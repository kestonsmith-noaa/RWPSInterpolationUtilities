

import datetime
import numpy as np
import netCDF4 as nc
import sys
import re
import InterpUtilities as iutil
flin0=sys.argv[1]
flin1=sys.argv[2]
flout=sys.argv[3]

varname0=sys.argv[4]
varname=varname0.split(":")
nvar=len(varname)

data0 = nc.Dataset(flin0,"r")
t=np.asarray(data0["time"][:])
var=np.asarray(data0["ErrorVariance"][:,:])

x=np.asarray(data0["longitude"][:])
y=np.asarray(data0["latitude"][:])
e=np.asarray(data0["tri"][:,:])

nt=len(t)
nn=len(x)
ne=e.shape[1]
noel=e.shape[0]

nvar=len(varname)
field=np.zeros((nvar,nt,nn))

nan=float("nan")
for jv in range(nvar):
    tmp=np.asarray(data0[varname[jv]][:,:])
    if "_FillValue" in data0[varname[jv]].ncattrs():
        fill_value0=data0[varname[jv]]._FillValue
        tmp[np.where(tmp==fill_value0)]=nan
    field[jv,:,:]=tmp

data1 = nc.Dataset(flin1,"r")
t1=np.asarray(data1["time"][:])
var1=np.asarray(data1["ErrorVariance"][:,:])
nt1,nn1=var1.shape
field1=np.zeros((nvar,nt1,nn1))
for jv in range(nvar):
    tmp=np.asarray(data1[varname[jv]][:,:])
    if "_FillValue" in data1[varname[jv]].ncattrs():
        fill_value1=data1[varname[jv]]._FillValue
        tmp[np.where(tmp==fill_value1)]=nan
    field1[jv,:,:]=tmp

Inf=float('inf')
um1=field1[0,0,:]
ng1=np.where( um1**2>=0  ) # find points that are valid floats for field1

for k in range(nt):
    #j=np.where(t[k]==t1) # find common merge point in data
    j=np.where(np.abs(t[k]-t1)<120.) # find common merge point in data
    j=j[0].tolist()
    if len(j)==1:
        print("j="+str(j)+" : k="+str(k))
        for jv in range(nvar):
             field[jv,k,ng1] =  ( field[jv,k,ng1] 
                                    +  ( var[k,ng1] / ( var[k,ng1] + var1[j,ng1] ) ) 
                                    * (field1[jv,j,ng1]-field[jv,k,ng1])
                                )
        #update error variance to posterior
        var[k,ng1]=var[k,ng1] * ( var1[j,ng1] / ( var[k,ng1]+var1[j,ng1] ) )

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

    time_var=ncout.createVariable('time', 'f4', ('time',))
    iutil.CopyAttributes(data0["time"], time_var)
    time_var[:]=t[:]

    tri_var=ncout.createVariable('tri', 'i4', ('noel','element'))
    tri_var.long_name     = 'element list'
    tri_var.standard_name = 'element list'
    tri_var[:,:]=e

    #Copy attributes from old file to new
    for jv in range(nvar):
        f_var=ncout.createVariable(varname[jv], 'f4', ('time','node'))
        iutil.CopyAttributes(data0[varname[jv]], f_var)
        f_var[:,:]=field[jv,:,:]

    ErrVar0=data0["ErrorVariance"]
    ErrVar_var=ncout.createVariable("ErrorVariance", 'f4', ('time','node'))
    iutil.CopyAttributes(ErrVar0, ErrVar_var)
    ErrVar_var[:,:]=var[:,:]
    ncout.close
