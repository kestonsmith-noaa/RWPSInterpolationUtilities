import numpy as np
import netCDF4 as nc
import sys
import InterpUtilities as  iutil
import os

UseUnixTime=True
nargin = len(sys.argv) - 1

flin=sys.argv[1]
mshfl=sys.argv[2]

meshslash=mshfl.rfind('/')+1
meshname=mshfl[meshslash:len(mshfl)-3]

xi, yi, ei, zi = iutil.loadWW3Mesh(mshfl)
nn=len(xi)
ne=ei.shape[0]

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
        
    if not 'node' in data0.dimensions:
        ncout.createDimension('node' , nn)
    if not 'element' in data0.dimensions:
        ncout.createDimension('element' , ne)
    if not 'noel' in data0.dimensions:
        ncout.createDimension('noel', 3)
    ncout.meshname=meshname
    ncout.mesh=mshfl
    
    if not 'longitude' in ncout.variables:
        lon_var=ncout.createVariable('longitude', 'f8', ('node',))
        lon_var.units         = 'degree_east'
        lon_var.long_name     = 'longitude'
        lon_var.standard_name = 'longitude'
        lon_var.axis          = 'X'
        lon_var[:]=xi[:]

    if not 'latitude' in ncout.variables:
        lat_var=ncout.createVariable('latitude', 'f8', ('node',))
        lat_var.units         = 'degree_north'
        lat_var.long_name     = 'latitude'
        lat_var.standard_name = 'latitude'
        lat_var.axis          = 'Y'
        lat_var[:]=yi[:]

    if not 'tri' in ncout.variables:
        tri_var=ncout.createVariable('tri', 'i4', ('noel','element'))
        tri_var.long_name     = 'element list'
        tri_var.standard_name = 'element list'
        tri_var[:]=np.transpose(ei)

    ncout.close
os.rename(fltmp, flin)
