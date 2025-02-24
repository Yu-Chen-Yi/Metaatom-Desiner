import torch
import numpy as np  
import torcwa
from Materials import Material

GRID_XPIXELS = 300
GRID_YPIXELS = 300
SIMULATION_DTYPE = torch.complex64
GEOMETRIC_DTYPE = torch.float32
EDGE_SHARPNESS = 1000

class RCWA:
    def __init__(self, args):
        self.device = args["device"]
        self.shape_type = args["shape type"]
        self.harmonic_order = args["harmonic order"]
        self.input_material = args["Input material"]
        self.output_material = args["Output material"]
        self.layer1_materialA = args["Layer 1 material A"]
        self.layer1_materialB = args["Layer 1 material B"]

    def get_Sparameter(self, 
                       wvln_list=None, 
                       period_list=None,
                       thickness_list=None, 
                       inc_ang_list=None, 
                       azi_ang_list=None, 
                       var1_list=None, 
                       var2_list=None, 
                       var3_list=None, 
                       var4_list=None,
                       orders_list=None
                       ):
        tensor_txx = torch.zeros(len(orders_list), 
                                 len(wvln_list), 
                                 len(period_list), 
                                 len(thickness_list), 
                                 len(inc_ang_list), 
                                 len(azi_ang_list), 
                                 len(var1_list), 
                                 len(var2_list), 
                                 len(var3_list), 
                                 len(var4_list), 
                                 len(orders_list), 
                                 dtype=SIMULATION_DTYPE, device=self.device
                                 )
        tensor_txy, tensor_tyx, tensor_tyy, tensor_rxx, tensor_rxy, tensor_ryx, tensor_ryy = [torch.zeros_like(tensor_txx) for _ in range(7)]
        # Simulation environment
        for wvln_idx, wvln in enumerate(wvln_list):
            for pd_idx, pd in enumerate(period_list):
                for thk_idx, thk in enumerate(thickness_list):
                    for idc_idx, inc_deg in enumerate(inc_ang_list):
                        for azi_idx, azi_deg in enumerate(azi_ang_list):
                            for var1_idx, var1 in enumerate(var1_list):
                                for var2_idx, var2 in enumerate(var2_list):
                                    for var3_idx, var3 in enumerate(var3_list):
                                        for var4_idx, var4 in enumerate(var4_list):
                                            txx, txy, tyx, tyy, rxx, rxy, ryx, ryy = self.forward(wvln, pd, thk, inc_deg, azi_deg, var1, var2, var3, var4, orders_list)
                                            # [orders, wvln, pd, thk, inc, azi, var1, var2, var3, var4]
                                            tensor_txx[:, wvln_idx, pd_idx, thk_idx, idc_idx, azi_idx, var1_idx, var2_idx, var3_idx, var4_idx] = txx #txx shape is torch.size[len(orders)]
                                            tensor_txy[:, wvln_idx, pd_idx, thk_idx, idc_idx, azi_idx, var1_idx, var2_idx, var3_idx, var4_idx] = txy
                                            tensor_tyx[:, wvln_idx, pd_idx, thk_idx, idc_idx, azi_idx, var1_idx, var2_idx, var3_idx, var4_idx] = tyx
                                            tensor_tyy[:, wvln_idx, pd_idx, thk_idx, idc_idx, azi_idx, var1_idx, var2_idx, var3_idx, var4_idx] = tyy
                                            tensor_rxx[:, wvln_idx, pd_idx, thk_idx, idc_idx, azi_idx, var1_idx, var2_idx, var3_idx, var4_idx] = rxx
                                            tensor_rxy[:, wvln_idx, pd_idx, thk_idx, idc_idx, azi_idx, var1_idx, var2_idx, var3_idx, var4_idx] = rxy
                                            tensor_ryx[:, wvln_idx, pd_idx, thk_idx, idc_idx, azi_idx, var1_idx, var2_idx, var3_idx, var4_idx] = ryx
                                            tensor_ryy[:, wvln_idx, pd_idx, thk_idx, idc_idx, azi_idx, var1_idx, var2_idx, var3_idx, var4_idx] = ryy
        tensor_tRL, tensor_tRR, tensor_tLR, tensor_tLL = self.XY2RL(tensor_txx, tensor_txy, tensor_tyx, tensor_tyy)
        tensor_rRL, tensor_rRR, tensor_rLR, tensor_rLL = self.XY2RL(tensor_rxx, tensor_rxy, tensor_ryx, tensor_ryy)
        T = {'xx': tensor_txx, 'xy': tensor_txy, 'yx': tensor_tyx, 'yy': tensor_tyy, 'RL': tensor_tRL, 'RR': tensor_tRR, 'LR': tensor_tLR, 'LL': tensor_tLL}
        R = {'xx': tensor_rxx, 'xy': tensor_rxy, 'yx': tensor_ryx, 'yy': tensor_ryy, 'RL': tensor_rRL, 'RR': tensor_rRR, 'LR': tensor_rLR, 'LL': tensor_rLL}
        result = {'T': T, 'R': R}
        return result
    
    def forward(self, wvln, pd, thickness, inc_deg, azi_deg, var1, var2, var3, var4, order_list):
        # light
        lamb0 = torch.tensor(wvln,dtype=GEOMETRIC_DTYPE,device=self.device)    # nm
        inc_ang = inc_deg*(np.pi/180)                    # radian
        azi_ang = azi_deg*(np.pi/180)                    # radian

        # material
        input_eps = Material.forward(wavelength=lamb0, name=self.input_material)**2
        output_eps = Material.forward(wavelength=lamb0, name=self.output_material)**2
        layer1_epsA = Material.forward(wavelength=lamb0, name=self.layer1_materialA)**2
        layer1_epsB = Material.forward(wavelength=lamb0, name=self.layer1_materialB)**2
        # geometry
        L = [pd, pd]            # nm / nm
        torcwa.rcwa_geo.dtype = GEOMETRIC_DTYPE
        torcwa.rcwa_geo.device = self.device
        torcwa.rcwa_geo.Lx = L[0]
        torcwa.rcwa_geo.Ly = L[1]
        torcwa.rcwa_geo.nx = GRID_XPIXELS
        torcwa.rcwa_geo.ny = GRID_YPIXELS
        torcwa.rcwa_geo.grid()
        torcwa.rcwa_geo.edge_sharpness = EDGE_SHARPNESS

        layer1_geometry = torcwa.rcwa_geo.circle(R=var1/2,Cx=L[0]/2.,Cy=L[1]/2.)
        # layers
        # Generate and perform simulation
        sim = torcwa.rcwa(freq=1/lamb0,order=[self.harmonic_order,self.harmonic_order],L=L,dtype=SIMULATION_DTYPE,device=self.device)
        sim.add_input_layer(eps=input_eps)
        sim.add_output_layer(eps=output_eps)
        sim.set_incident_angle(inc_ang=inc_ang, azi_ang=azi_ang)
        layer0_eps = layer1_geometry*layer1_epsA + layer1_epsB*(1.-layer1_geometry)
        sim.add_layer(thickness=thickness,eps=layer0_eps)
        sim.solve_global_smatrix()

        txx = sim.S_parameters(orders=order_list, direction='forward',port='transmission',polarization='xx',ref_order=[0,0])
        txy = sim.S_parameters(orders=order_list, direction='forward',port='transmission',polarization='xy',ref_order=[0,0])
        tyx = sim.S_parameters(orders=order_list, direction='forward',port='transmission',polarization='yx',ref_order=[0,0])
        tyy = sim.S_parameters(orders=order_list, direction='forward',port='transmission',polarization='yy',ref_order=[0,0])

        rxx = sim.S_parameters(orders=order_list, direction='forward',port='r',polarization='xx',ref_order=[0,0])
        rxy = sim.S_parameters(orders=order_list, direction='forward',port='r',polarization='xy',ref_order=[0,0])
        ryx = sim.S_parameters(orders=order_list, direction='forward',port='r',polarization='yx',ref_order=[0,0])
        ryy = sim.S_parameters(orders=order_list, direction='forward',port='r',polarization='yy',ref_order=[0,0])

        return txx, txy, tyx, tyy, rxx, rxy, ryx, ryy

    @staticmethod
    def XY2RL(txx, txy, tyx, tyy):
        tRL = (txx - tyy) - 1j * (txy + tyx)
        tRR = (txx + tyy) + 1j * (txy - tyx)
        tLR = (txx - tyy) + 1j * (txy + tyx)
        tLL = (txx + tyy) - 1j * (txy - tyx)
        return tRL, tRR, tLR, tLL