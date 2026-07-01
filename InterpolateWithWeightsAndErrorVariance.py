import numpy as np
import netCDF4 as nc
import sys
import InterpUtilities as  iutil
import xarray as xr
import scipy.sparse as sp
from scipy.interpolate import NearestNDInterpolator
import datetime

# Engine for interpolating to WW3 unstructured mesh using precomputed interpolation weights from netcdf files with forecasts
#
# to call:
# python InterpolateSTOFS.py input_file meshpath outputfile variable1:variable2:variable3 ExtrapMethod
#
# example:
# python InterpolateSTOFS.py stofs.20260608.00/stofs.cwl.vel.nc meshes/RWPS.V0a.small.msh tesdtoZ.vel.nc u-vel:v-vel 2
# or:
# python InterpolateSTOFS.py stofs.20260608.00/stofs.cwl.nc meshes/RWPS.V0a.small.msh tesdtoZ.vel.nc zeta 1
#
# ExtrapMethod =-1 no extrapolation, NaN's potentially in output where source field is dry
# ExtrapMethod = 0 NaN values in interpolated field replaced with 0.0
# ExtrapMethod = 1 Nearest Neighbor extrapolation from valid source values
# ExtrapMethod = 2 Nearest Neighbor extrapolation from valid interpolated values
# ExtrapMethod = 3 Nearest Neighbor extrapolation from interpolated nodes which allways have valid values (faster than 2 for larger source mesh)

UseUnixTime=True
nargin = len(sys.argv) - 1

flin=sys.argv[1]
#mshfl=sys.argv[2]
#meshslash=mshfl.rfind('/')+1

#weights_file="STOFS.wght."+mshfl[meshslash:len(mshfl)-4]+".nc"
weights_file=sys.argv[2]

flout=sys.argv[3]
varname0=sys.argv[4]
varname=varname0.split(":")
if nargin>4:
    VarParam0=sys.argv[5]
    IncludeErrorVariance=True
else:
    print("no variance parameters provided- error variance will not be included in file "+flout)
    IncludeErrorVariance=False

VariableType='Wind'
if "vel" in varname[0]:
    VariableType='Current'
if "zeta" in varname[0]:
    VariableType='WaterLevel'
if "ice" in varname[0]:
    VariableType='Ice'

ExtrapMethod=-1 # no extrapolation
if nargin>4:
    ExtrapMethod=int(sys.argv[5])
    
if ExtrapMethod==-1:
    print("no extrapolation, nan left in place in output")
if ExtrapMethod==0:
    print("Fill missing values in interpolated field with value 0")
if ExtrapMethod==1:
    print("extrapolation from nearest valid point in source- can be slow if source mesh is much larger than destination mesh")
if ExtrapMethod==2:
    print("extrapolation from nearest valid point in destination (interpolated field)")

with xr.open_dataset(weights_file) as ds_s:
   # Standard sparse storage uses 'row', 'col', and 'data' variables
   row = ds_s['row'].values
   col = ds_s['col'].values
   weights = ds_s['S'].values
   Nrows=ds_s.attrs.get('Nrows')
   Ncols=ds_s.attrs.get('Ncols')
   SrcFieldType=ds_s.attrs.get('SrcFieldType')
   if ExtrapMethod>0: #these extrapolation methods need the source and destination nodes
       x=ds_s['x_src'].values
       y=ds_s['y_src'].values
       xi=ds_s['x_dst'].values
       yi=ds_s['y_dst'].values
       #shift to RWPS convention
       j=np.where(x>90)
       x[j]=x[j]-360.
       j=np.where(xi>90)
       xi[j]=xi[j]-360.

nni=Nrows
n1=Ncols
   
matrix = sp.coo_matrix((weights, (row-1, col-1)), shape=(Nrows,Ncols)).tocsr()
print("sparse interpolation matrix")
print(matrix)

data = nc.Dataset(flin,"r")
if "time" in data.variables:
    time=iutil.ConvertTimeToUnixTime(flin,"time")
elif "MT" in data.variables:
    time=iutil.ConvertTimeToUnixTime(flin,"MT")
else:
    print("No time variable found in "+flin+" EXITING")
    sys.exit(1)

nt=len(time)

#nt=4
#time=time[0:nt]

print(time)

nvar=len(varname)
vari=np.zeros((nvar,nt,nni))

if ExtrapMethod>=0:
    IsExtrap=np.zeros((nvar,nt,nni),dtype=int)
    
if ExtrapMethod==3:
    AnyExtrap=np.zeros((nvar,nni),dtype=int)

nan=float("nan")
for jv in range(nvar):
    fill_value0=data[varname[jv]]._FillValue
    print("fill value="+str(fill_value0))
    for k in range(nt):
        print("interpolating for time step = "+str(k)+" of "+str(nt))
        vshp = data.variables[varname[jv]].shape
#        if SrcFieldType=="unstructured":
        if len(vshp)==1: 
            var=np.asarray(data[varname[jv]][:]) # No time dimension?, just spatial data to interpolate
        if len(vshp)==2: 
            var=np.asarray(data[varname[jv]][k,:])
        if len(vshp)==3: # Wind field with dimensions time, x, y
            var0=np.asarray(data[varname[jv]][k,:,:])
            var=np.transpose(var0).reshape(n1)                
        if len(vshp)==4: # RTOFS field with 2nd dimensional "Level" and garbage boundries
            var0=np.asarray(data[varname[jv]][k,0,:,:])
            if "rtofs" in flin: #remove bad geometry edges
                var0=var0[1:-1,1:-1]
            var=np.transpose(var0).reshape(n1)                
        else:
            print("unkown data shape for "+varname[jv]+" terminating")
            sys.exit()
        
        #replace fill with nan to avoid interpolating fill
        j=np.where(var==fill_value0)
        var[j]=nan
        
        if ExtrapMethod==0:
            j=np.where(np.isnan(var))
            var[j]=0.
        
        vari[jv,k,:] = matrix @ var # actual spatial interpolation step
        
        if ExtrapMethod==3: # Fast posthoc nearest neighbor extrapolator
            jd=np.where(np.isnan(vari[jv,k,:]))
            AnyExtrap[jv,jd]=1.
        elif ExtrapMethod>0:# and ExtrapMethod<3:
            jd=np.where(np.isnan(vari[jv,k,:]))
            dstp=np.array((xi[jd],yi[jd]))
            if ExtrapMethod==1:
            #extrapolate using nearest neighbor of source with valid value
                js=np.where(~np.isnan(var))
                srcp=np.array((x[js],y[js]))
                srcv=var[js]
            if ExtrapMethod==2:
            #extrapolate using nearest neighbor of interpolated field with valid value
                js=np.where(~np.isnan(vari[jv,k,:]))
                srcp=np.array((xi[js],yi[js]))
                tmp=vari[jv,k,js]
                srcv=tmp.flatten()
            interp = NearestNDInterpolator(srcp.T,srcv)
            ExtrapVals = interp( dstp.T )
            vari[jv,k,jd]=ExtrapVals
            IsExtrap[jv,k,jd]=1

if ExtrapMethod==0:
    jd=np.where(np.isnan(vari))
    vari[jd]==0.
    IsExtrap[jd]=1
    
if ExtrapMethod==3: #posthoc extrapolation from points which are valid at all times
    for jv in range(nvar):
        jd=np.where(AnyExtrap[jv,:]==1) # nodes that have some "nan" intrepolated values
        js=np.where(AnyExtrap[jv,:]==0) # nodes that have no "nan" intrepolated values
        srcp = np.array((xi[js],yi[js])).T
        srcv = vari[jv,0,js] #dummy input field
        dstp = np.array((xi[jd],yi[jd])).T
        srcv=srcv[0,:]
        interpolator = NearestNDInterpolator(srcp, srcv)
        distances, jsrc = interpolator.tree.query(dstp)
        jd=jd[0]
        for k in range(nt):
            jdk=np.where(np.isnan(vari[jv,k,jd]))
            jdk=jdk[0]
            vari[jv,k,jd[jdk]]=vari[jv,k,jsrc[jdk]] # value of nearest "always valid" destination point
            IsExtrap[jv,k,jd[jdk]]=1
            
print("nn(target mesh) = "+str(nni)+": Nrows = "+str(Nrows))
print("nn(source mesh) = "+str(n1)+": Ncols = "+str(Ncols))
if not ((nni==Nrows) and (n1==Ncols)):
    print("WARNING: Wrong matrix weights: number of rows from "+ mshfl +" = "+str(nni)+
    " but number of rows in "+ weights_file +" = "+str(Nrows)+ 
    ", number of spatial points in "+ flin +" = "+str(n1)+ 
    " but number of columns in "+ weights_file +" = "+str(Ncols)  )
    print("  You may need to regnerate file "+ weights_file +" with appropriate weights")

##########################################################################################
# CONSTRUCT PRESCRIBED ERROR COVARIANCE FOR UPDATING ESTIMATE
##########################################################################################
#grab variables for prescribing error variance
if IcludeErrorVariance:
    dist2bnd_file=weights_file.replace("InterpolationWeights", "DistToBnd")
    with xr.open_dataset(dist2bnd_file) as ds_s:
        dist2bnd = ds_s['dist2bnd'].values
        zi = ds_s['depth'].values

    if VariableType=="Current":
        VarShallow=float(VarParam[0]) # variance (m/s)**2 for shallow regions
        VarDeep=float(VarParam[1])  # variance (m/s)**2 for deep regions
        BatShallow=float(VarParam[2]) # isobath (m) for shallow regions
        BatDeep=float(VarParam[3]) # isobath (m) for deep regions
        if "stofs" in flin:
#            Variance = iutil.VarianceLinearDepth(zi,1.,100.,50.,250.)
            Variance = iutil.VarianceLinearDepth(zi,VarShallow,VarDeep,BatShallow,BatDeep)
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
            Variance = VarInterior + 0.*dist2bnd[:] 
        if "rrfs" in flin:
            VarBoundary = float(VarParam[1]) # variance (m/s)**2 for boundary of forecast
            VarLambda   = float(VarParam[2]) # lengthscale (km) for linear transition from bounadry variance to interior variance
            Variance = iutil.VarianceLinearDistanceToBndy( dist2bnd, VarInterior, VarBoundary,VarLambda )

    ErrorVariance=np.zeros((nt,nni))
    for k in range(nt):
        ErrorVariance[k,:]=Variance[:]
##########################################################################################
# CONSTRUCT PRESCRIBED ERROR COVARIANCE FOR UPDATING ESTIMATE
##########################################################################################

ne=ei.shape[0]
with nc.Dataset(flout, 'w', format='NETCDF4') as ncout:

    ncout.createDimension('level' , 1)  
    ncout.createDimension('node' , nni)
    ncout.createDimension('element' , ne)
    ncout.createDimension('time', nt)
    ncout.createDimension('noel', 3)

    lon_var=ncout.createVariable('longitude', 'f8', ('node',))
    lon_var.units         = 'degree_east'
    lon_var.long_name     = 'longitude'
    lon_var.standard_name = 'longitude'
    lon_var.axis          = 'X'
    lon_var[:]=xi[:]

    lat_var=ncout.createVariable('latitude', 'f8', ('node',))
    lat_var.units         = 'degree_north'
    lat_var.long_name     = 'latitude'
    lat_var.standard_name = 'latitude'
    lat_var.axis          = 'Y'
    lat_var[:]=yi[:]
    
    if UseUnixTime:
        units = 'seconds since 1970-01-01 00:00:00.0 0:00'
        long_name = 'verification time generated by wgrib2 function verftime()'
        standard_name = 'time'
    else:
        varin = data["time"]
        units = varin.units 
        standard_name = varin.standard_name
        long_name = varin.long_name
    
    time_var=ncout.createVariable('time', 'f8', ('time',))
    time_var.units         = units
    time_var.long_name     = long_name 
    time_var.standard_name = standard_name
    time_var[:]=time[:]

    tri_var=ncout.createVariable('tri', 'i4', ('noel','element'))
    tri_var.long_name     = 'element list'
    tri_var.standard_name = 'element list'
    tri_var[:]=np.transpose(ei)

    for jv in range(nvar):
        if varname[jv]==''
        print("writing output for :"+varname[jv])
        varin = data[varname[jv]]
        units = varin.units 
        standard_name = varin.standard_name
        long_name = varin.long_name
        location = 'node' 

        F_var=ncout.createVariable(varname[jv], 'f4', ('time','node'),fill_value = fill_value0)
        F_var.long_name     = long_name
        F_var.units         = units
        F_var.standard_name = standard_name
        F_var.location      = location
        F_var[:,:]          = vari[jv,:,:]
        
        if ExtrapMethod >= 0 :
            xtrp_var=ncout.createVariable(varname[jv]+'IsExtrap', 'i1', ('time','node'))
            xtrp_var.long_name     = '==1 if the interpolated value extrapolated. 0 if interpolated'
            xtrp_var.standard_name = 'is extrapolated'
            xtrp_var.location      = 'node'
            if ExtrapMethod == 0:
                xtrp_var.method        = 'Interpolated nan values replaced with 0'
            if ExtrapMethod == 1:
                xtrp_var.method        = 'nearest valid neighbor in source field'
            if ExtrapMethod == 2:
                xtrp_var.method        = 'nearest valid neighbor in interpolated field'
            xtrp_var[:,:]          = IsExtrap[jv,:,:]

    if IcludeErrorVariance:
        ErrorVariance_var=ncout.createVariable('ErrorVariance', 'f4', ('time','node'),fill_value    = fill_value0)
        ErrorVariance_var.long_name     = 'forecast error variance'
        ErrorVariance_var.units         = "("+units+")**2"
        ErrorVariance_var.standard_name = 'variance'
        ErrorVariance_var[:,:]=ErrorVariance

    ncout.close


