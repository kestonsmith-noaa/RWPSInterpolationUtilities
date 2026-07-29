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

nni=Nrows
n1=Ncols
   
matrix = sp.coo_matrix((weights, (row-1, col-1)), shape=(Nrows,Ncols)).tocsr()
print("sparse interpolation matrix")
print(matrix)
row_sum = matrix.sum(axis=1)
j0=np.where( row_sum==0 ) # destination nodes with no coverage from interpolation matrix

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
        elif len(vshp)==2: 
            var=np.asarray(data[varname[jv]][k,:])
        elif len(vshp)==3: # Wind field with dimensions time, x, y
            if "wind" in flin:
                var0=np.asarray(data[varname[jv]][k,:,:])
                var=np.transpose(var0).reshape(n1)
            elif "ice" in flin:
                var0=np.asarray(data[varname[jv]][k,:,:])
                if "rtofs" in flin: #remove bad geometry edges
                    var0=var0[1:-1,1:-1]
                var=np.transpose(var0).reshape(n1)

        elif len(vshp)==4: # RTOFS field with 2nd dimensional "Level" and garbage boundries
            var0=np.asarray(data[varname[jv]][k,0,:,:])
            if "rtofs" in flin: #remove bad geometry edges
                var0=var0[1:-1,1:-1]
            var=np.transpose(var0).reshape(n1)
            
        else:
            print(vshp)
            print(len(vshp))
            print("unkown data shape for "+varname[jv]+" terminating")
            sys.exit()
        
        #replace fill with nan to avoid interpolating fill
        j=np.where(var==fill_value0)
        var[j]=nan
        if ExtrapMethod==0:
            j=np.where(np.isnan(var))
            var[j]=0.
        
        vari[jv,k,:] = matrix @ var # actual spatial interpolation step
        vari[jv,k,j0]=nan # empty rows
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

#ne=ei.shape[0]

with nc.Dataset(flout, 'w', format='NETCDF4') as ncout:

    ncout.createDimension('level' , 1)  
    ncout.createDimension('node' , nni)
    ncout.createDimension('time', nt)

    time_var=ncout.createVariable('time', 'f8', ('time',))
    varin = data["time"]
    iutil.CopyAttributes(varin, time_var)
    if UseUnixTime:
        time_var.units         = 'seconds since 1970-01-01 00:00:00.0 0:00'
        time_var.standard_name = 'time'
    time_var[:]=time[:]

    for jv in range(nvar):
        print("writing output for :"+varname[jv])
        varin = data[varname[jv]]
        F_var=ncout.createVariable(varname[jv], 'f4', ('time','node'),fill_value = fill_value0)
        iutil.CopyAttributes(varin, F_var)
        F_var.location      = 'node'
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

    ncout.close
            
    
#mesh geometry should be added later
"""

    ncout.createDimension('element' , ne)
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
    
    tri_var=ncout.createVariable('tri', 'i4', ('noel','element'))
    tri_var.long_name     = 'element list'
    tri_var.standard_name = 'element list'
    tri_var[:]=np.transpose(ei)
"""

