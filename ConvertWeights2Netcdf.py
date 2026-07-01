import numpy as np
import netCDF4 as nc
import sys
#import GeoComputeMeshToMeshInterpWeights as mshint
import InterpUtilities as  iutil
import scipy.sparse as sp

nargin = len(sys.argv) - 1

flin=sys.argv[1]
mshfl=sys.argv[2]
meshslash=mshfl.rfind('/')+1

#AddExtrapolationSupport=False
AddExtrapolationSupport=True

#TextWeightFl="STOFS.wght."+mshfl[meshslash:len(mshfl)-4]+".txt"
TextWeightFl="InterpWeights."+mshfl[meshslash:len(mshfl)-4]+".stofs.txt"
flout = "InterpolationWeights."+mshfl[meshslash:len(mshfl)-3]+".stofs.nc"

xi, yi, ei, zi = iutil.loadWW3Mesh(mshfl)
nn_dst=len(xi)
data = nc.Dataset(flin,"r")
#read spaital dimensions and determine if input mesh is curvilinear or regular
x=np.asarray(data["x"][:])
#convert to RWPS coordinates
jEast=np.where(x>90)
x[jEast]=x[jEast]=360.

nn_src=len(x)

#Read in weights from cat of text output(rows are not in order)
F=np.loadtxt(TextWeightFl)

node_dst=F[:,0] # row number (destination node)
ele_num_src=F[:,1] # Source element number (not used)
node_src=F[:,2:5] # Source node
DistToCenterKM=F[:,5] # distance of destination node from source element center (not used) 
weights=F[:,6:9] # interpolation weights from source nodes to destination node

node_dst=node_dst.astype(int)
node_src=node_src.astype(int)
ele_num_src=ele_num_src.astype(int)

nnz=F.shape[0]
n_s=3*nnz
row=np.zeros(n_s,dtype=int)
col=np.zeros(n_s,dtype=int)
val=np.zeros(n_s)

n=0
for k in range(nnz):
    for j in range(3):
        row[n]=node_dst[k]
        col[n]=node_src[k,j]
        val[n]=weights[k,j]
        n=n+1
print("n="+str(n))
print("n_s="+str(n_s))
n_s=n

with nc.Dataset(flout, 'w', format='NETCDF4') as ncout:
    ncout.createDimension('n_s' , n_s)
    ncout.setncattr("Nrows", nn_dst)
    ncout.setncattr("Ncols", nn_src)
    ncout.setncattr("SrcFieldType", "unstructured") 
    
    r_var=ncout.createVariable('row', 'i4', ('n_s',))
    r_var.long_name     = 'row index'
    r_var[:]=row[:]
    
    c_var=ncout.createVariable('col', 'i4', ('n_s',))
    c_var.long_name     = 'column index'
    c_var[:]=col[:]
    
    s_var=ncout.createVariable('S', 'f8', ('n_s',))
    s_var.long_name     = 'matrix value'
    s_var[:]=val[:]

#Consider adding (x,y) destination and (x,y) for source. This is usefull for extrapolation
    if AddExtrapolationSupport:
        x=np.asarray(data["x"][:])
        y=np.asarray(data["y"][:])
        ncout.createDimension('nn_src' , nn_src)
        ncout.createDimension('nn_dst' , nn_dst)
        
        xsrc_var=ncout.createVariable('x_src', 'f8', ('nn_src',))
        xsrc_var.long_name     = 'interpolation source node longitude'
        xsrc_var[:]=x[:]
        
        ysrc_var=ncout.createVariable('y_src', 'f8', ('nn_src',))
        ysrc_var.long_name     = 'interpolation source node latitude'
        ysrc_var[:]=y[:]
        
        xdst_var=ncout.createVariable('x_dst', 'f8', ('nn_dst',))
        xdst_var.long_name     = 'interpolation destination node longitude'
        xdst_var[:]=xi[:]
    
        ydst_var=ncout.createVariable('y_dst', 'f8', ('nn_dst',))
        ydst_var.long_name     = 'interpolation destination node latitude'
        ydst_var[:]=yi[:]

        zdst_var=ncout.createVariable('depth_dst', 'f8', ('nn_dst',))
        zdst_var.long_name     = 'interpolation destination node latitude'
        zdst_var[:]=zi[:]

#Extrapolate=False
Extrapolate=sys.argv[3]

if Extrapolate:
    dist2bnd=np.full(len(xi), np.inf) #all points are inside boundary- No boundary with this type of extrapolation
else:
    matrix = sp.coo_matrix((weights, (row-1, col-1)), shape=(nn_src,nn_dst)).tocsr()
    row_sum = matrix.sum(axis=1)
    j0=np.where( row_sum==0 ) # destination nodes with no coverage from interpolation matrix
    j0=np.array(j0[0]).tolist()
    u0=np.ones(xi.shape)
    nan=float("nan")
    u0[j0]=nan
    dist2bnd=iutil.CalculateDistanceToInterpEnvelope(xi,yi,u0, 1.)

dist2bnd_file = "DistToBndy."+mshfl[meshslash:len(mshfl)-3]+".stofs.nc"
with nc.Dataset(dist2bnd_file, 'w', format='NETCDF4') as ncout:
    ncout.createDimension('node' , nn_dst)
    d_var=ncout.createVariable('dist2bnd', 'f4', ('node',))
    d_var.long_name     = 'distance to boundary'
    d_var.units         = 'km'
    d_var.standard_name = 'distance to boundary'
    d_var[:]=dist2bnd[:]
    
    z_var=ncout.createVariable('depth', 'f4', ('node',))
    z_var.long_name     = 'mesh depth'
    z_var.units         = 'm'
    z_var.standard_name = 'depth'
    z_var[:]=zi[:]

