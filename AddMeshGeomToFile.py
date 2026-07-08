import numpy as np
import netCDF4 as nc
import sys
import InterpUtilities as  iutil
import xarray as xr

# Engine for interpolating to WW3 unstructured mesh using precomputed interpolation weights from netcdf files with forecasts
#
# to call:
# python InterpolateSTOFS.py input_file meshpath outputfile variable1:variable2:variable3 ExtrapMethod
#
# example:
# python InterpolateSTOFS.py stofs.20260608.00/stofs.cwl.vel.nc meshes/RWPS.V0a.small.msh tesdtoZ.vel.nc u-vel:v-vel 2
# or:
# python InterpolateSTOFS.py stofs.20260608.00/stofs.cwl.nc meshes/RWPS.V0a.small.msh tesdtoZ.vel.nc zeta 1

UseUnixTime=True
nargin = len(sys.argv) - 1

flinout=sys.argv[1]
mshfl=sys.argv[2]

meshslash=mshfl.rfind('/')+1
meshname=mshfl[meshslash:len(mshfl)-3]

xi, yi, ei, zi = iutil.loadWW3Mesh(mshfl)

nn=len(xi)
ne=ei.shape[0]

#with nc.Dataset(flinout, 'r+', format='NETCDF4') as ncadd:
with nc.Dataset(flinout, 'a', format='NETCDF4') as ncadd:
    if not 'node' in ncadd.dimensions:
        ncadd.createDimension('node' , nn)
    if not 'element' in ncadd.dimensions:
        ncadd.createDimension('element' , ne)
    if not 'noel' in ncadd.dimensions:
        ncadd.createDimension('noel', 3)
    ncadd.meshname=meshname
    ncadd.mesh=mshfl
    
    if not 'longitude' in ncadd.variables:
#        lon_var=ncadd.createVariable('longitude', 'f8', ('node',))
        lon_var=ncadd.createVariable('longitude', 'f8', ('node',),zlib=False)
        lon_var.units         = 'degree_east'
        lon_var.long_name     = 'longitude'
        lon_var.standard_name = 'longitude'
        lon_var.axis          = 'X'
        lon_var[:]=xi[:]

    if not 'latitude' in ncadd.variables:
        lat_var=ncadd.createVariable('latitude', 'f8', ('node',),zlib=False)
        lat_var.units         = 'degree_north'
        lat_var.long_name     = 'latitude'
        lat_var.standard_name = 'latitude'
        lat_var.axis          = 'Y'
        lat_var[:]=yi[:]

    if not 'tri' in ncadd.variables:
        tri_var=ncadd.createVariable('tri', 'i4', ('noel','element'),zlib=False)
        tri_var.long_name     = 'element list'
        tri_var.standard_name = 'element list'
        tri_var[:]=np.transpose(ei)

    ncadd.close
    
"""    
    if not 'depth' in ncadd.variables:
        depth_var=ncadd.createVariable('depth', 'f8', ('node',))
        depth_var.units         = 'm'
        depth_var.long_name     = 'ocean depth below geoid, Hdown'
        depth_var.standard_name = 'depth'
        depth_var.axis          = 'X'
        depth_var[:]=zi[:]
"""
