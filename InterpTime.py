import os
import argparse
import numpy as np
import netCDF4 as nc
import sys
import math

from scipy.interpolate import interp1d

nargin = len(sys.argv) - 1

flin=sys.argv[1] 
flinNewTimes=sys.argv[2] 
flout=sys.argv[3] 

varname0=sys.argv[4]
varname=varname0.split(":")
nvar=len(varname)

# If InterpSecondFile is True interpolate  the values from the second file are interpolated to the common time points
# and extrapolate (via persistance) for all times beyond the range of  time from the second file

InterpSecondFile=False
if nargin>4:
    InterpSecondFile=eval(sys.argv[5])
    print("Interpolating fields from second file: "+str(InterpSecondFile)+" and extrapolating via persistance in time")

#might want to rewrite with an input file to derive full set of times
print("running InterpTime.py: takes a forecast (arg1="+flin+") and interpolates to times ")
print("in another file (arg2="+flinNewTimes+"). The origonal and interpoated values are output to ")
print("a new file(arg3="+flout+") .")
print("interpolating for variables:")
for jv in range(nvar):
    print(varname[jv])

data0 = nc.Dataset(flin,"r")
t=np.asarray(data0["time"][:])

data1 = nc.Dataset(flinNewTimes,"r")
t1=np.asarray(data1["time"][:])

#make sorted union of times in both forecasts
tf = np.union1d(t, t1)

#eliminate times occuring outside the range of arg1 to avoid extrapolation
j=np.where( np.logical_and( tf>=np.min(t) , tf<=np.max(t)  )  )
print(j)
j=j[0].tolist()
tf=tf[j]

print("Initial times:")
print(t)
print("New times:")
print(tf)

nt=len(tf)

x=np.asarray(data0["longitude"][:])
y=np.asarray(data0["latitude"][:])
e=np.asarray(data0["tri"][:,:])
print("e")
print(e)
print(e.shape)
nn=len(x)
ne=e.shape[1]
noel=e.shape[0]

InterpolatedVariables=np.zeros((nvar,nt,nn))

IsExtrap=False
if InterpSecondFile:
    t=t1
    data=data1
    IsExtrap=True
else:
    data=data0

ntt=len(t)
#unique_vals, indices = np.unique(arr, return_index=True)
tu,indx=np.unique(t,return_index=True)
for jv in range(nvar):
    u=np.asarray(data[varname[jv]][:,:])
    fill_value0 = data[varname[jv]]._FillValue
    nan=float('nan')
    jb=np.where(u==fill_value0)
    u[jb]=nan

#set up interpolator for u
#    fi = interp1d(t, u, axis=0, kind='linear')
#    fi = interp1d(t, u, axis=0, kind='linear',fill_value=np.nan)
#    fi = interp1d(tu, u[indx,:], axis=0, kind='linear',fill_value=np.nan)
    if IsExtrap:
        fi = interp1d(tu, u[indx,:], axis=0, kind='linear',fill_value="extrapolate") #extrapolated values will be overwritten
    else:
        fi = interp1d(tu, u[indx,:], axis=0, kind='linear')
    uf=fi(tf)

    #re-insert initial values at times that match initial time points
    print("Interpolation compleate: now re-insert initial values at times that match initial time points")
    print("to remove small interpolation artifacts")
    for k in range(nt):
        j=np.where(tf[k]==t)
        j=j[0].tolist()
        print("new time index: "+str(k)+" is same as old time index:"+str(j))
        if len(j)>0:
            print("mapping exactly back to origonal values at time: "+str(tf[k]))
            j=j[0]
            uf[k,:]=u[j,:]

    if IsExtrap:
        jExtrapEarly=np.where(tf<t[0])
        for jxtrp in range(len(jExtrapEarly)):
            uf[jExtrapEarly[jxtrp],:]=u[0,:]
        jExtrapLate=np.where(tf>t[ntt-1])
        for jxtrp in range(len(jExtrapLate)):
            uf[jExtrapLate[jxtrp],:]=u[ntt-1,:]

    InterpolatedVariables[jv,:,:]=uf[:,:]

import InterpUtilities as iutil
with nc.Dataset(flout, 'w', format='NETCDF4') as ncout:

    ncout.createDimension('level' , 1)  
    ncout.createDimension('node' , nn)
    ncout.createDimension('element' , ne)
    ncout.createDimension('time', nt)
    ncout.createDimension('noel', 3)

    lon_var=ncout.createVariable('longitude', 'f8', ('node',))
    lon_var.units         = 'degree_east'
    lon_var.long_name     = 'longitude'
    lon_var.standard_name = 'longitude'
    lon_var.axis          = 'X'
    lon_var[:]=x[:]

    lat_var=ncout.createVariable('latitude', 'f8', ('node',))
    lat_var.units         = 'degree_north'
    lat_var.long_name     = 'latitude'
    lat_var.standard_name = 'latitude'
    lat_var.axis          = 'Y'
    lat_var[:]=y[:]

    time_var0=data0["time"]
    time_var=ncout.createVariable('time', 'f8', ('time',))
    iutil.CopyAttributes(time_var0, time_var)
    time_var[:]=tf[:]

    tri_var=ncout.createVariable('tri', 'i4', ('noel','element',))
    tri_var.long_name     = 'element list'
    tri_var.standard_name = 'element list'
    tri_var[:,:]=e
    
    #Copy attributes from old file to new
    for jv in range(nvar):
        var=data0[varname[jv]]
        f_var=ncout.createVariable(varname[jv], 'f4', ('time','node'))
        iutil.CopyAttributes(var, f_var)
        f_var[:,:]=InterpolatedVariables[jv,:,:]
    ncout.close
