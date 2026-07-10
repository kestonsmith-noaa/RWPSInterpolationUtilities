import numpy as np
import netCDF4 as nc
import sys
import InterpUtilities as  iutil
import xarray as xr
#Add compute and add error variance field to existing file 

UseUnixTime=True
nargin = len(sys.argv) - 1

flinout=sys.argv[1]
dist2bnd_file=sys.argv[2]

VarParam0=sys.argv[3]
VarParam=VarParam0.split(":")

data=nc.Dataset(dist2bnd_file,"r")
dist2bnd=np.array(data["dist2bnd"][:])
zi=np.array(data["depth"][:])
nn=len(dist2bnd)
data.close()


VariableType="WaterLevel"
if "wind" in flinout:
    VariableType="Wind"
elif "uv" in flinout:
    VariableType="Current"
elif "vel" in flinout:
    VariableType="Current"


if VariableType=="Current":
    VarShallow=float(VarParam[0]) # variance (m/s)**2 for shallow regions
    VarDeep=float(VarParam[1])  # variance (m/s)**2 for deep regions
    BatShallow=float(VarParam[2]) # isobath (m) for shallow regions
    BatDeep=float(VarParam[3]) # isobath (m) for deep regions
    if "stofs" in flinout:
#            Variance = iutil.VarianceLinearDepth(zi,1.,100.,50.,250.)
        Variance = iutil.VarianceLinearDepth (zi, VarShallow, VarDeep, BatShallow, BatDeep)
    if "rtofs" in flinout: #variance high in shallows and near boundary of coverage
#            VarianceDepth = iutil.VarianceLinearDepth(zi,100.,1.,50.,250.)
        VarianceDepth = iutil.VarianceLinearDepth(zi,VarShallow,VarDeep,BatShallow,BatDeep)
        VarLambda= float(VarParam[4])  # lengthscale (km) for linear transition from bounadry variance(==VarShallow) to interior variance(==VarDeep)
        VarianceBnd = iutil.VarianceLinearDistanceToBndy( dist2bnd, VarDeep,VarShallow, VarLambda)
        Variance = np.maximum(VarianceDepth, VarianceBnd)

if VariableType=="WaterLevel":
    if "stofs" in flinout:
#            Variance = 1.+0*zi
        VarInterior=float(VarParam[0]) # variance (m)**2 for stofs water level
        Variance = VarInterior+0.*zi

if VariableType=="Wind":
    ##LocalFS  = [ rwps_pr, rwps_hi, rwps_ak, rwps_conus, rwps_na] # file names
    ##VarFS    = [ 4.     , 4.    , 9.      , 16.       , 25.    ] # (m m /s /s)
    ##LambdaFS = [ 150.   , 200.  , 500.    , 1000.     , 1500.  ] # (km)
    VarInterior=float(VarParam[0]) # variance (m/s)**2 for interior of forecast
    if "nbm" in flinout:
        Variance = VarInterior + np.zeros(nn)
    if "rrfs" in flinout:
        VarBoundary = float(VarParam[1]) # variance (m/s)**2 for boundary of forecast
        VarLambda   = float(VarParam[2]) # lengthscale (km) for linear transition from bounadry variance to interior variance
        Variance = iutil.VarianceLinearDistanceToBndy( dist2bnd, VarInterior, VarBoundary,VarLambda )

#with nc.Dataset(flinout, 'r+', format='NETCDF4') as ncadd:
with nc.Dataset(flinout, 'a', format='NETCDF4') as ncadd:
    time=np.asarray(ncadd["time"][:])
    nt=len(time)
    ErrorVariance=np.zeros((nt,nn))
    for k in range(nt):
        ErrorVariance[k,:]=Variance[:]

    if not 'node' in ncadd.dimensions:
        ncadd.createDimension('node' , nn)
    if not 'time' in ncadd.dimensions:
        ncadd.createDimension('time' , nt)
    if not 'ErrorVariance' in ncadd.variables:
        ErrorVariance_var=ncadd.createVariable('ErrorVariance', 'f8', ('time','node'))
        ErrorVariance_var.long_name     = 'forecast error variance'
        ErrorVariance_var.units         = "(field units)**2"
        ErrorVariance_var.standard_name = 'errror variance'
        ErrorVariance_var[:]=ErrorVariance
