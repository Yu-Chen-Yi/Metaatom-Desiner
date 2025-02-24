from RCWA import RCWA
from objprint import objprint
import torch
args = {}
args["Random Seed"] = 777
args["Device"] = "GPU"
args["Data Type"] = "float32"
args["Shape type"] = "circle"
args["Harmonic order"] = 7
args["Input material"] = "air.txt"
args["Output material"] = "air.txt"
args["Layer 1 material A"] = "aSiH.txt"
args["Layer 1 material B"] = "air.txt"
A = RCWA(args)
wvln_list = [wvln for wvln in range(401, 702, 100)]
period_list = [period for period in range(800, 1201, 100)]
thickness_list = [thickness for thickness in range(100, 301, 100)]
inc_ang_list = [0.]
azi_ang_list = [0.]
var1_list = [var1 for var1 in range(100, 301, 100)]
var2_list = [0.]
var3_list = [0.]
var4_list = [0.]
orders_list = [[i, j] for i in range(-1, 2) for j in range(-1, 2)]
result = A.get_Sparameter(wvln_list,
                        period_list, 
                        thickness_list,
                        inc_ang_list, 
                        azi_ang_list, 
                        var1_list, 
                        var2_list, 
                        var3_list, 
                        var4_list, 
                        orders_list)
print(result["R"]["xx"].shape)
objprint(A)