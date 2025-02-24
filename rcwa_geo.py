import torch
import torch.fft

class geometry:
    def __init__(self,
            Lx:float=1.,
            Ly:float=1.,
            nx:int=100,
            ny:int=100,
            edge_sharpness:float=1000.,*,
            dtype=torch.float32,
            device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'),
        ):

        '''
            Geometry

            Parameters
            - Lx: x-direction Lattice constant (float)
            - Ly: y-direction Lattice constant (float)
            - x: x-axis sampling number (int)
            - y: y-axis sampling number (int)
            - edge_sharpness: sharpness of edge (float)

            Keyword Parameters
            - dtype: geometry data type (only torch.complex64 and torch.complex128 are allowed.)
            - device: geometry device (only torch.device('cpu') and torch.device('cuda') are allowed.)

        '''
        self.Lx = Lx
        self.Ly = Ly
        self.nx = nx
        self.ny = ny
        self.edge_sharpness = edge_sharpness

        self.dtype = dtype
        self.device = device

    def grid(self):
        '''
            Update grid
        '''

        self.x = (self.Lx/self.nx)*(torch.arange(self.nx,dtype=self.dtype,device=self.device)+0.5)
        self.y = (self.Ly/self.ny)*(torch.arange(self.ny,dtype=self.dtype,device=self.device)+0.5)
        self.x_grid, self.y_grid = torch.meshgrid(self.x,self.y,indexing='ij')

    def circle(self,R,var2,Cx,Cy,theta):
        ''' 
            R: radius
            Cx: x center
            Cy: y center
        '''

        self.grid()
        level = 1. - torch.sqrt(((self.x_grid-Cx)/R)**2 + ((self.y_grid-Cy)/R)**2)
        return torch.sigmoid(self.edge_sharpness*level)

    def ellipse(self,Rx,Ry,Cx,Cy,theta=0.):
        '''
            Rx: x direction radius
            Ry: y direction radius
            Cx: x center
            Cy: y center
        '''

        theta = torch.as_tensor(theta,dtype=self.dtype,device=self.device)

        self.grid()
        level = 1. - torch.sqrt((((self.x_grid-Cx)*torch.cos(theta)+(self.y_grid-Cy)*torch.sin(theta))/Rx)**2 + ((-(self.x_grid-Cx)*torch.sin(theta)+(self.y_grid-Cy)*torch.cos(theta))/Ry)**2)
        return torch.sigmoid(self.edge_sharpness*level)

    def square(self,W,var2,Cx,Cy,theta=0.):
        '''
            W: width
            Cx: x center
            Cy: y center
            theta: rotation angle / center: [Cx, Cy] / axis: z-axis
        '''

        theta = torch.as_tensor(theta,dtype=self.dtype,device=self.device)

        self.grid()
        level = 1. - (torch.maximum(torch.abs(((self.x_grid-Cx)*torch.cos(theta)+(self.y_grid-Cy)*torch.sin(theta))/(W/2.)),torch.abs((-(self.x_grid-Cx)*torch.sin(theta)+(self.y_grid-Cy)*torch.cos(theta))/(W/2.))))
        return torch.sigmoid(self.edge_sharpness*level)

    def rectangle(self,Wx,Wy,Cx,Cy,theta=0.):
        '''
            Wx: x width
            Wy: y width
            Cx: x center
            Cy: y center
            theta: rotation angle / center: [Cx, Cy] / axis: z-axis
        '''

        theta = torch.as_tensor(theta,dtype=self.dtype,device=self.device)

        self.grid()
        level = 1. - (torch.maximum(torch.abs(((self.x_grid-Cx)*torch.cos(theta)+(self.y_grid-Cy)*torch.sin(theta))/(Wx/2.)),torch.abs((-(self.x_grid-Cx)*torch.sin(theta)+(self.y_grid-Cy)*torch.cos(theta))/(Wy/2.))))
        return torch.sigmoid(self.edge_sharpness*level)

    def rhombus(self,Wx,Wy,Cx,Cy,theta=0.):
        '''
            Wx: x diagonal
            Wy: y diagonal
            Cx: x center
            Cy: y center
            theta: rotation angle / center: [Cx, Cy] / axis: z-axis
        '''

        theta = torch.as_tensor(theta,dtype=self.dtype,device=self.device)

        self.grid()
        level = 1. - (torch.abs(((self.x_grid-Cx)*torch.cos(theta)+(self.y_grid-Cy)*torch.sin(theta))/(Wx/2.)) + torch.abs((-(self.x_grid-Cx)*torch.sin(theta)+(self.y_grid-Cy)*torch.cos(theta))/(Wy/2.)))
        return torch.sigmoid(self.edge_sharpness*level)

    def super_ellipse(self,Wx,Wy,Cx,Cy,theta=0.,power=2.):
        '''
            Wx: x width
            Wy: y width
            Cx: x center
            Cy: y center
            theta: rotation angle / center: [Cx, Cy] / axis: z-axis
            power: elliptic power
        '''

        theta = torch.as_tensor(theta,dtype=self.dtype,device=self.device)

        self.grid()
        level = 1. - (torch.abs(((self.x_grid-Cx)*torch.cos(theta)+(self.y_grid-Cy)*torch.sin(theta))/(Wx/2.))**power + torch.abs((-(self.x_grid-Cx)*torch.sin(theta)+(self.y_grid-Cy)*torch.cos(theta))/(Wy/2.))**power)**(1/power)
        return torch.sigmoid(self.edge_sharpness*level)

    def hollow_square(self, W1, W2, Cx, Cy, theta=0.):
        layerA = self.square(W1, W1, Cx, Cy, theta)
        layerB = self.square(W2, W1, Cx, Cy, theta)
        
        return torch.minimum(layerA,1.-layerB)
    
    def hollow_circle(self, R1, R2, Cx, Cy, theta=0.):
        layerA = self.circle(R1, R2, Cx, Cy, theta)
        layerB = self.circle(R1, R2, Cx, Cy, theta)
        
        return torch.minimum(layerA,1.-layerB)
    
    def cross(self, Wx, Wy, Cx, Cy, theta):
        layerA = self.rectangle(Wx=Wx, Wy=Wy, Cx=L[0]/2., Cy=L[1]/2., theta=theta)
        layerB = self.rectangle(Wx=Wx, Wy=Wy, Cx=L[0]/2., Cy=L[1]/2., theta=theta+3.14159265359/2)
        
        return torch.maximum(layerA,layerB)
        
    def union(self,A,B):
        '''
            A U B
        '''

        return torch.maximum(A,B)

    def intersection(self,A,B):
        '''
            A n B
        '''

        return torch.minimum(A,B)

    def difference(self,A,B):
        '''
            A - B = A n Bc
        '''

        return torch.minimum(A,1.-B)