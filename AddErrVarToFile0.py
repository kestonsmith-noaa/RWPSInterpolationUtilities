import numpy as np
import netCDF4 as nc
import sys
import InterpUtilities as  iutil
import os
#Add compute and add error variance field to existing file 

UseUnixTime=True
nargin = len(sys.argv) - 1

flin=sys.argv[1]
dist2bnd_file=sys.argv[2]

VarParam0=sys.argv[3]
VarParam=VarParam0.split(":")

data=nc.Dataset(dist2bnd_file,"r")
dist2bnd=np.array(data["dist2bnd"][:])
zi=np.array(data["depth"][:])
nn=len(dist2bnd)
data.close()


VariableType="WaterLevel"
if "wind" in flin:
    VariableType="Wind"
elif "uv" in flin:
    VariableType="Current"
elif "vel" in flin:
    VariableType="Current"


if VariableType=="Current":
    VarShallow=float(VarParam[0]) # variance (m/s)**2 for shallow regions
    VarDeep=float(VarParam[1])  # variance (m/s)**2 for deep regions
    BatShallow=float(VarParam[2]) # isobath (m) for shallow regions
    BatDeep=float(VarParam[3]) # isobath (m) for deep regions
    if "stofs" in flin:
#            Variance = iutil.VarianceLinearDepth(zi,1.,100.,50.,250.)
        Variance = iutil.VarianceLinearDepth (zi, VarShallow, VarDeep, BatShallow, BatDeep)
    if "rtofs" in flin: #variance high in shallows and near boundary of coverage
#            VarianceDepth = iutil.VarianceLinearDepth(zi,100.,1.,50.,250.)
        VarianceDepth = iutil.VarianceLinearDepth(zi,VarShallow,VarDeep,BatShallow,BatDeep)
        VarLambda= float(VarParam[4])  # lengthscale (km) for linear transition from bounadry variance(==VarShallow) to interior variance(==VarDeep)
        VarianceBnd = iutil.VarianceLinearDistanceToBndy( dist2bnd, VarDeep,VarShallow, VarLambda)
        Variance = np.maximum(VarianceDepth, VarianceBnd)

if VariableType=="WaterLevel":
    if "stofs" in flin:
#            Variance = 1.+0*zi
        VarInterior=float(VarParam[0]) # variance (m)**2 for stofs water level
        Variance = VarInterior+0.*zi

if VariableType=="Wind":
    ##LocalFS  = [ rwps_pr, rwps_hi, rwps_ak, rwps_conus, rwps_na] # file names
    ##VarFS    = [ 4.     , 4.    , 9.      , 16.       , 25.    ] # (m m /s /s)
    ##LambdaFS = [ 150.   , 200.  , 500.    , 1000.     , 1500.  ] # (km)
    VarInterior=float(VarParam[0]) # variance (m/s)**2 for interior of forecast
    if "nbm" in flin:
        Variance = VarInterior + np.zeros(nn)
    if "rrfs" in flin:
        VarBoundary = float(VarParam[1]) # variance (m/s)**2 for boundary of forecast
        VarLambda   = float(VarParam[2]) # lengthscale (km) for linear transition from bounadry variance to interior variance
        Variance = iutil.VarianceLinearDistanceToBndy( dist2bnd, VarInterior, VarBoundary,VarLambda )

fltmp="tmp."+flin
try:
    os.remove(fltmp)
except:
    print("creating "+fltmp+" temporarily")

data0 = nc.Dataset(flin,"r")

with  nc.Dataset(fltmp, "w", format="NETCDF4") as ncout:
    # 1. Copy Global Attributes
    ncout.setncatts({attr: data0.getncattr(attr) for attr in data0.ncattrs()})
    # 2. Copy Dimensions
    for name, dimension in data0.dimensions.items():
        # If the dimension is unlimited, pass None to createDimension
        dim_len = len(dimension) if not dimension.isunlimited() else None
        ncout.createDimension(name, dim_len)
    for name, src_var in data0.variables.items():
        dst_var = ncout.createVariable(name, src_var.datatype, src_var.dimensions)
        dst_var.setncatts({attr: src_var.getncattr(attr) for attr in src_var.ncattrs()})
        dst_var[:] = src_var[:]
        
    time=np.asarray(data0["time"][:])
    nt=len(time)
    ErrorVariance=np.zeros((nt,nn))
    for k in range(nt):
        ErrorVariance[k,:]=Variance[:]

    if not 'node' in ncout.dimensions:
        ncadd.createDimension('node' , nn)
    if not 'time' in ncout.dimensions:
        ncadd.createDimension('time' , nt)
    if not 'ErrorVariance' in ncout.variables:
        ErrorVariance_var=ncout.createVariable('ErrorVariance', 'f8', ('time','node'))
        ErrorVariance_var.long_name     = 'forecast error variance'
        ErrorVariance_var.units         = "(field units)**2"
        ErrorVariance_var.standard_name = 'errror variance'
        ErrorVariance_var[:]=ErrorVariance

    ncout.close
os.rename(fltmp, flin)
