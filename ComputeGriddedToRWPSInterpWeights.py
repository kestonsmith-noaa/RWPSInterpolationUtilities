# This is a a set of routines that interpolate wind forecasts to an unstructured 
# mesh from regular or curvilinear grids (using ESMPY). In addition to interpolation 
# field the out file contains a spatially variable error variance estimate based on the 
# distance to the forecast boundary. This error variance is used later to update 
# dispirate forecasts in a bayesian manner to yield a spatially smooth estimate 
# incorporating all forecasts. The understanding is that the more local forecast 
# products are of higher accuracy than the coarser broader scale forecasts

import numpy as np
import os

import datetime
import netCDF4 as nc
import sys
import re
import InterpUtilities as iutil

import xarray as xr
import esmpy
import scipy.sparse as sp

import InterpUtilities as iutil


#mshfl="../meshes/RWPS.V0a.small.msh"
#flin="../RWPSWrkFlw/WindBlend/wind.20260507.00X/rrfs.20260507.00.wind10m.ak.nc"


# Main program
#AddExtrapolationSupport=False
AddExtrapolationSupport=True

nargin = len(sys.argv) - 1

flin=sys.argv[1]
mshfl=sys.argv[2]

# Don't use nearest neighbor interpolation unless 6th positive integer argument present.
# This may be needed on boundary of RWPS mesh if node alignment is outside NBM OC domain
Extrapolate=False
if nargin > 2:
    if int(sys.argv[3])>0:
        print("using nearest neighbor to extrapolate wind field beyond geometric coverage")
        Extrapolate=True

xi, yi, ei, zi = iutil.loadWW3Mesh(mshfl)
nn=len(xi)

if np.mean(xi)<0:
	xi=xi+360.

data = nc.Dataset(flin,"r")
#read spaital dimensions and determine if input mesh is curvilinear or regular
x1=np.asarray(data["longitude"][:])
y1=np.asarray(data["latitude"][:])
if (len(x1.shape)==2 and len(y1.shape)==2):
    IsCrvLn=True
elif (len(x1.shape)==1 and len(y1.shape)==1):
    IsCrvLn=False
else:
    print("input file spatial dimension is not right. ending program")
    sys.exit()
# shift to common longitude
if np.mean(np.mean(x1))<0:
    x1=x1+360.

#######################################
# === Create weights  ===#
#######################################

meshslash=mshfl.rfind('/')+1
dom=flin.split(".")
dom=dom[len(dom)-2]
weights_file = "InterpolationWeights."+mshfl[meshslash:len(mshfl)-3]+dom+".nc"
print("interpolation weights will be written to file = "+ weights_file)

if IsCrvLn:
    nx=x1.shape[0]
    ny=x1.shape[1]
else:
    nx=len(x1)
    ny=len(y1)
n1=nx*ny

print("Computing weights and saving to file: "+ weights_file)

if not IsCrvLn:
    x1 = np.tile(x1,(ny,1))
    y1 = np.tile(y1,(nx,1)).T
#Use esmpy to construct bilinear interpolation weights
iutil.CurvilinearGridCreateInterpWeights(xi, yi, x1, y1, weights_file)

#######################################
# === read weights and  ===#
#######################################
with xr.open_dataset(weights_file) as ds_s:
   # Standard sparse storage uses 'row', 'col', and 'S'==weights variables
   row = ds_s['row'].values
   col = ds_s['col'].values
   weights = ds_s['S'].values
   Nrows=ds_s.attrs.get('Nrows')
   Ncols=ds_s.attrs.get('Ncols')
print("nn = "+str(nn)+": Nrows = "+str(Nrows))
print("n1 = "+str(n1)+": Ncols = "+str(Ncols))
if not ((nn==Nrows) and (n1==Ncols)):
    print("Wrong matrix weights: number of rows from "+ mshfl +" = "+str(nn)+
    " but number of rows in "+ weights_file +" = "+str(Nrows)+ 
    ", number of spatial points in "+ flin +" = "+str(n1)+ 
    " but number of columns in "+ weights_file +" = "+str(Ncols)  )
    print("  You probably need to remove file "+ weights_file +" and rerun to generate appropriate weights")
matrix = sp.coo_matrix((weights, (row-1, col-1)), shape=(nn,n1)).tocsr()
print("sparse interpolation matrix")
print(matrix)

##################################################################################
# START: Extrapolate for nodes not covered by interpolator
##################################################################################
x1v=np.transpose(x1).reshape(n1) # vectorize src nodes, consistant with data to interpolate
y1v=np.transpose(y1).reshape(n1)

if Extrapolate:
    from scipy.interpolate import NearestNDInterpolator
    srcp = np.array((x1v,y1v)).T
    srcv = 1.+x1v**2 + y1v**2 #dummy input field
    #dstv = matrix @ srcv.T
    row_sum = matrix.sum(axis=1)
    j0=np.where( row_sum==0 ) # destination nodes with no coverage from interpolation matrix
    j0=np.array(j0[0]).tolist()
    dstp = np.array((xi[j0],yi[j0])).T
    interpolator = NearestNDInterpolator(srcp, srcv)
    distances, j0src = interpolator.tree.query(dstp)
    weightsExtrp=weights.tolist().append([1.0] * len(j0) )
    rowExtrp=np.concatenate( (row, np.array(j0)) )
    colExtrp=np.concatenate( (col, np.array(j0src)) )
    weightsExtrp=np.concatenate( (weights, np.array([1.0] * len(j0))) )
    os.replace(weights_file, "NoExtrap."+weights_file)
    iutil.WriteInterpolationWeightsToNetCDF(weights_file,rowExtrp,colExtrp,weightsExtrp,len(xi),len(x1v))
##################################################################################
# FINISHED: Extrapolate for nodes not covered by interpolator
##################################################################################

##################################################################################
# START: Extrapolation support for NaN occurances in source field
##################################################################################
if AddExtrapolationSupport:
    with nc.Dataset(weights_file, 'r+', format='NETCDF4') as ncadd:
        x=np.asarray(data["x"][:])
        y=np.asarray(data["y"][:])
        ncadd.createDimension('nn_src' , nn_src)
        ncadd.createDimension('nn_dst' , nn_dst)
        
        xsrc_var=ncadd.createVariable('x_src', 'f8', ('nn_src',))
        xsrc_var.long_name     = 'interpolation source node longitude'
        xsrc_var[:]=x1v[:]
        
        ysrc_var=ncadd.createVariable('y_src', 'f8', ('nn_src',))
        ysrc_var.long_name     = 'interpolation source node latitude'
        ysrc_var[:]=y1v[:]
        
        xdst_var=ncadd.createVariable('x_dst', 'f8', ('nn_dst',))
        xdst_var.long_name     = 'interpolation destination node longitude'
        xdst_var[:]=xi[:]
    
        ydst_var=ncadd.createVariable('y_dst', 'f8', ('nn_dst',))
        ydst_var.long_name     = 'interpolation destination node latitude'
        ydst_var[:]=yi[:]
        
##################################################################################
# FINISHED: Extrapolation support for NaN occurances in source field
##################################################################################

##################################################################################
# START: Compute distance to boundary for each node in mesh:
##################################################################################
#dist2bnd_file = "DistToBndy."+mshfl[meshslash:len(mshfl)-3]+dom+".txt"
dist2bnd_file = "DistToBndy."+mshfl[meshslash:len(mshfl)-3]+dom+".nc"

if Extrapolate:
    dist2bnd=np.full(len(xi), np.inf) #all points are inside boundary- No boundary with this type of extrapolation
else:
    row_sum = matrix.sum(axis=1)
    j0=np.where( row_sum==0 ) # destination nodes with no coverage from interpolation matrix
    j0=np.array(j0[0]).tolist()
    u0=np.ones(xi.shape)
    nan=float("nan")
    u0[j0]=nan
    dist2bnd=iutil.CalculateDistanceToInterpEnvelope(xi,yi,u0, 1.)

with nc.Dataset(dist2bnd_file, 'w', format='NETCDF4') as ncout:
    ncout.createDimension('node' , nn)
    d_var=ncout.createVariable('dist2bnd', 'f4', ('node',))
    d_var.long_name     = 'distance to boundary'
    d_var.units         = 'km'
    d_var.standard_name = 'distance to boundary'
    d_var[:]=dist2bnd[:]

