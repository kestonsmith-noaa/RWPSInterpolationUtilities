from scipy.interpolate import RegularGridInterpolator
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from datetime import datetime
import numpy as np
import netCDF4 as nc
import sys
import re

#Convert Time to "seconds since 1970-01-01 00:00:00.0"
#eg   'seconds since 2024-04-04 12:00:00        ! NCDASE - BASE_DAT'
def ConvertTimeToUnixTime(flin,TimeVarName = None):
    if TimeVarName == None:
        TimeVarName="time"
    data = nc.Dataset(flin,"r")
    #print("TimeVarName = "+TimeVarName)
    timevar=data[TimeVarName]
    time=np.asarray(data[TimeVarName][:])
    epoch_1970 = datetime(1970, 1, 1, 0, 0, 0)
    TimeUnitsString=timevar.units
    TimeUnitsStrings=TimeUnitsString.split(" ")
    tunits=TimeUnitsStrings[0]
    dstr=TimeUnitsStrings[2]
    dstr=dstr.split("-")
    tstr=TimeUnitsStrings[3]
    tstr=tstr.split(":")
    base_date = datetime(int(dstr[0]),int(dstr[1]),int(dstr[2]),int(tstr[0]),int(tstr[1]),int(tstr[2]))
    base_offset = int((base_date - epoch_1970).total_seconds())
    if tunits=="seconds":
        unix_time = time + base_offset
    if tunits=="days":
        unix_time = time*24*60*60 + base_offset
    if tunits=="hours":
        unix_time = time*60*60 + base_offset
    return unix_time

def loadWW3Mesh(fl):
    print("mesh file="+fl)
    f=open(fl, 'r')
    header = f.readline() 
    header = f.readline() 
    header = f.readline() 
    header = f.readline() 
    header = f.readline() # number of nodes
    nn=int(header)
    print("nn = "+str(nn))
    xi=np.zeros(nn)
    yi=np.zeros(nn)
    zi=np.zeros(nn)
    k=0
    for i in range(nn):
        A = f.readline()
        B=A.lstrip()
        values = B.split(" ")
#        print(values)
        if len(values)>5:
            xi[k]=values[2]
            yi[k]=values[4]
            zi[k]=values[6]
        else:
            xi[k]=values[1]
            yi[k]=values[2]
            zi[k]=values[3]
        k=k+1
    print("number of nodes read: "+str(k))
    header = f.readline() 
    header = f.readline() 
    header = f.readline() # number of elements
    ne=int(header)#includes boundary nodes and actual elements
    print("ne="+str(ne)+" -includes boundary nodes")
    nbnd=0
    bnd=[]
    eix=np.zeros((ne,3), dtype=int)
    k=0
    for i in range(ne):
        A = f.readline()
        #print(A)
        values = A.split(" ")
        #print(values)
        if len(values) == 6:
            if int(values[2])==2:
                bnd.append(int(values[5]))
                nbnd=nbnd+1
        if len(values)>15:
            eix[k,0]=int(values[12])
            eix[k,1]=int(values[14])
            eix[k,2]=int(values[16])
            k=k+1
        elif len(values)>7:
            eix[k,0]=int(values[6])
            eix[k,1]=int(values[7])
            eix[k,2]=int(values[8])
            k=k+1
    ei=eix[range(k),:]
    print("number of open boundary nodes read: "+str(nbnd))
    print("number of elements read: "+str(k))
    return xi, yi, ei, zi


import numpy as np
from scipy.interpolate import griddata
#import matplotlib.pyplot as plt

def interpolate_curvilinear_to_points(lon_in, lat_in, data_in, lon_out, lat_out):
    """
    Performs bilinear-equivalent interpolation from a curvilinear grid to new points.

    Args:
        lon_in (np.ndarray): 2D array of input longitudes.
        lat_in (np.ndarray): 2D array of input latitudes.
        data_in (np.ndarray): 2D array of data values corresponding to (lon_in, lat_in).
        lon_out (np.ndarray or list): Longitudes of the target points.
        lat_out (np.ndarray or list): Latitudes of the target points.

    Returns:
        np.ndarray: Interpolated data values at the target points.
    """
    # Flatten the input coordinates and data into 1D arrays
    # griddata expects points as a list of (x, y) tuples or a 2D array
    points_in = np.vstack((lon_in.flatten(), lat_in.flatten())).T
    values_in = data_in.flatten()

    # Define the target points
    points_out = np.vstack((lon_out, lat_out)).T

    # Perform the interpolation using scipy.interpolate.griddata with 'linear' method
    # The 'linear' method in griddata is the appropriate choice for curvilinear data
    # as it uses triangulation.
    interpolated_data = griddata(points_in, values_in, points_out, method='linear')

    return interpolated_data


def interpolate_curvilinear_to_pointsMD(lon_in, lat_in, data_in, lon_out, lat_out):
    """
    Performs bilinear-equivalent interpolation from a curvilinear grid to new points.

    Args:
        lon_in (np.ndarray): 2D array of input longitudes.
        lat_in (np.ndarray): 2D array of input latitudes.
        data_in (np.ndarray): 3D array of data values corresponding to (lon_in, lat_in, ntimes).
        lon_out (np.ndarray or list): Longitudes of the target points.
        lat_out (np.ndarray or list): Latitudes of the target points.

    Returns:
        np.ndarray: Interpolated data values at the target points (length(lon_out/lat_out x ntimes)).
    """
    # Flatten the input coordinates and data into 1D arrays
    # griddata expects points as a list of (x, y) tuples or a 2D array
    points_in = np.vstack((lon_in.flatten(), lat_in.flatten())).T

    shp=data_in.shape
    print(shp)
    nx=shp[0]
    ny=shp[1]
    nt=shp[2]

    ns=nx*ny
    S=np.zeros((ns,nt))
    s0=np.zeros((nx,ny))
    for k in range(nt):
        s0[:,:]=np.transpose(data_in[:,:,k])
        S[:,k] = s0.flatten()

    # Define the target points
    points_out = np.vstack((lon_out, lat_out)).T

    # Perform the interpolation using scipy.interpolate.griddata with 'linear' method
    # The 'linear' method in griddata is the appropriate choice for curvilinear data
    # as it uses triangulation.
    interpolated_data = griddata(points_in, S, points_out, method='linear')

    return interpolated_data


def interpolate_curvilinear_to_pointsRRFS(lon_in, lat_in, data_in, lon_out, lat_out):
    """
    Performs bilinear-equivalent interpolation from a curvilinear grid to new points.

    Args:
        lon_in (np.ndarray): 2D array of input longitudes.
        lat_in (np.ndarray): 2D array of input latitudes.
        data_in (np.ndarray): 3D array of data values corresponding to (lon_in, lat_in, ntimes).
        lon_out (np.ndarray or list): Longitudes of the target points.
        lat_out (np.ndarray or list): Latitudes of the target points.

    Returns:
        np.ndarray: Interpolated data values at the target points (length(lon_out/lat_out x ntimes)).
    """
    # Flatten the input coordinates and data into 1D arrays
    # griddata expects points as a list of (x, y) tuples or a 2D array
   
    points_in = np.vstack((lon_in.flatten(), lat_in.flatten())).T
   # points_in = np.hstack((lon_in.flatten(), lat_in.flatten()))

    shp=data_in.shape
    print(shp)
    nx=shp[0]
    ny=shp[1]
    nt=shp[2]

    ns=nx*ny
    S=np.zeros((ns,nt))
    #s0=np.zeros((nx,ny))
    s0=np.zeros((ny,nx))
    for k in range(nt):
        s0[:,:]=np.transpose(data_in[:,:,k])
        #s0[:,:]=data_in[:,:,k]
        S[:,k] = s0.flatten()

    # Define the target points
    points_out = np.vstack((lon_out, lat_out)).T

    # Perform the interpolation using scipy.interpolate.griddata with 'linear' method
    # The 'linear' method in griddata is the appropriate choice for curvilinear data
    # as it uses triangulation.
    print(S.shape)
    print(points_in)
    print(points_out)
    
    interpolated_data = griddata(points_in, S, points_out, method='linear')

    return interpolated_data

def CopyAttributes(VarOld, VarNew):
    #Copy attributes from old NetCDF file variable to new NetCDF file variable
    att_names = VarOld.ncattrs()
    for jatt in range(len(att_names)):
        att_name=att_names[jatt]
        if (not (att_name=="_FillValue")):
            att_value = VarOld.getncattr(att_name)
            VarNew.setncattr(att_name, att_value)
    return


############################################################################################
# BEGIN WIND TO RWPS INTERP ROUTINES 
import esmpy
import scipy.sparse as sp

def CurvilinearGridCreateInterpWeights(xi,yi,x1,y1, weights_file):
# Compute interpolation weights to interpolate from curvilinear grid (x1,y1) to points (xi,yi)
# and store in netcdf file using ESMPY
    nx,ny=x1.shape
    nn=len(xi)
    n1=nx*ny
    src_lon = x1
    src_lat = y1
    dst_lon=np.zeros((1,nn))
    dst_lat=np.zeros((1,nn))
    print("nn="+str(nn))
    dst_lon[0,:] = xi[:]
    dst_lat[0,:] = yi[:]

    esmpy.Manager()

    src_grid = esmpy.Grid(
      max_index=np.array([src_lon.shape[0], src_lon.shape[1]]),
      staggerloc=esmpy.StaggerLoc.CENTER,
      coord_sys=esmpy.CoordSys.SPH_DEG
    )

    dst_grid = esmpy.Grid(
      max_index=np.array([nn, 1]),
      staggerloc=esmpy.StaggerLoc.CENTER,
      coord_sys=esmpy.CoordSys.SPH_DEG
    )

    # 4. Populate the coordinate data
    src_lon_ptr = src_grid.get_coords(0)
    src_lat_ptr = src_grid.get_coords(1)
    src_lon_ptr[...] = src_lon
    src_lat_ptr[...] = src_lat

    dst_lon_ptr = dst_grid.get_coords(0)
    dst_lat_ptr = dst_grid.get_coords(1)
    dst_lon_ptr[...] = dst_lon.T
    dst_lat_ptr[...] = dst_lat.T

    # 5. Create esmpy Fields
    src_field = esmpy.Field(src_grid, name="src_field")
    dst_field = esmpy.Field(dst_grid, name="dst_field")
    src_field.data[...]=np.sqrt(x1/180)/(90+y1) # arbitrary function of x,y

    np.savetxt('F.txt', src_field.data[...])
    np.savetxt('X.txt', x1)
    np.savetxt('Y.txt', y1)
    print(f"Creating weights: {weights_file}")
    regrid = esmpy.Regrid(
      src_field,
      dst_field,
      filename=weights_file,
      regrid_method=esmpy.RegridMethod.BILINEAR,
      unmapped_action=esmpy.UnmappedAction.IGNORE # Optional: Ignores missing/masked points
    )
#Add number of rows and columns to weights file for clarity when constructing sparse matrix for interpolation
    with nc.Dataset(weights_file, mode="a") as ds:
        ds.Nrows = nn
        ds.Ncols = n1
    
    np.savetxt('Fi.txt', dst_field.data[...])
    np.savetxt('xi.txt', xi)
    np.savetxt('yi.txt', yi)
    
    return

def CalculateDistanceToBoundary(xi,yi,x1,y1):
# Distance to boundary calculation for use when interpolation envelope corresponds with 
# interior of curvilinear grid boundary.
#
# Inputs:
#   xi (nn): longitude of unstructured mesh nodes 
#   yi (nn): latitude of unstructured mesh nodes 
#   x1 (nx x ny): longitude for interpoltated field
#   y1 (nx x ny): latitude for interpoltated field
#
# Outputs:
#   dist2bnd (nn) : distance to edge of interpolation envelope.  
    nx=x1.shape[0]
    ny=x1.shape[1]
    xb=np.hstack((x1[1,:],x1[:,ny-1].T,x1[nx-1,:],x1[:,1].T))
    yb=np.hstack((y1[1,:],y1[:,ny-1].T,y1[nx-1,:],y1[:,1].T))
    np.savetxt('xbyb.txt', np.vstack((xb,yb)))
    dist2bnd=np.zeros(nn)
    for k in range(nn):
        dist2bnd[k]=QuickDistance(yi[k],xi[k],yb,xb)
        if k%10000==0:
            print("calculating distance to boundary, "+str(k)+":"+ str(nn)+":"+str(k/nn) )
    return dist2bnd

def CalculateDistanceToInterpEnvelope(xi,yi,fi,SearchWidth):
# Alternative distance to boundary calculation for use when interpolation envelope is 
# distinctly interior to curvilinear grid boundary as happens for RRFS NA grid 
#
# Inputs:
#   xi (nn): longitude of unstructured mesh nodes 
#   yi (nn): latitude of unstructured mesh nodes 
#   fi (nn): interpolated field on mesh nodes with 'nan' values outside of interpolation envelope
#   SearchWidth: Computational speed up to remove extra search points in distance to boundary
#
# Outputs:
#   dist2bnd (nn) : distance to edge of interpolation envelope.  dist2bnd[k]=0 if (xi[k],yi[k]) is outside
#                   of the interpolation envelope
    nn=len(xi)
    #dist2bnd=np.zeros(nn)
    dist2bnd=np.full(nn,np.nan)
    jin = np.where(~np.isnan(fi))[0].tolist()#points inside interpolation envelope
    jout = np.where(np.isnan(fi))[0].tolist() #points outside interpolation envelope
    xin=xi[jin]
    yin=yi[jin]
    xout=xi[jout]
    yout=yi[jout]
    jxU=np.where( xout < np.max(xin)+SearchWidth )[0].tolist()
    jxD=np.where( xout > np.min(xin)-SearchWidth )[0].tolist()
    jyU=np.where( yout < np.max(yin)+SearchWidth )[0].tolist()
    jyD=np.where( yout > np.min(yin)-SearchWidth )[0].tolist()
    j=list( set(jxU) & set(jxD)  & set(jyU)   & set(jyD)  )
    xout=xout[j]
    yout=yout[j]
    din=np.zeros(len(jin))
    print(len(xin))
    print(len(xout))
    for k in range(len(xin)):
        din[k]=QuickDistance(yin[k],xin[k],yout,xout) # distance from node to closest point not interpolated to
        if k%10000==0:
            print("calculating distance to boundary, "+str(k)+":"+ str(nn)+":"+str(k/nn) )
    dist2bnd[jin]=din
    return dist2bnd

#END WIND TO RWPS Utils

def QuickDistance(lat1, lon1, lats2, lons2):
    deg2kmY=111.
    deg2kmX=np.cos( np.pi * lat1 / 180.)*deg2kmY
    d= np.min(  np.sqrt( (  (lat1-lats2)*deg2kmY)**2 + ((lon1-lons2)*deg2kmX)**2 )  )
    return d

def VarianceLinearDistanceToBndy(InteriorNodeList, DistanceToBoundary, InteriorVariance, VarianceOnBoundary, LengthScale):
    Variance=np.zeros(len(DistanceToBoundary))+np.inf
    SpatialFunction=DistanceToBoundary/LengthScale
    j=np.where(SpatialFunction>1.)
    SpatialFunction[j]=1.
    Variance[InteriorNodeList] = VarianceOnBoundary + ( InteriorVariance - VarianceOnBoundary ) * SpatialFunction[InteriorNodeList]
    return Variance

def VarianceInverseDistanceToBndy(InteriorNodeList, DistanceToBoundary, InteriorVariance, LengthScale):
    Variance=np.zeros(len(DistanceToBoundary))+np.inf
    SpatialFunction=LengthScale / DistanceToBoundary
    j=np.where(SpatialFunction>1.)
    SpatialFunction[j]=1.
    Variance[InteriorNodeList] = InteriorVariance  * SpatialFunction[InteriorNodeList]
    return Variance

import numpy as np
import netCDF4 as nc
def WriteInterpolationWeightsToNetCDF(weights_file,row,col,weights,Nrows,Ncols):
    #create a esmpy style sparse matrix netcdf file
    print(Nrows)
    print(Ncols)
    print(row)
    print(col)
    print(weights)
    n_s=len(weights)

    if isinstance(row , list):
        row      = np.array( row  )
    if isinstance( col, list):
        col      = np.array( col )
    if isinstance( weights, list):
        weights = np.array( weights )

    with nc.Dataset(weights_file, 'w', format='NETCDF4') as ncout:
            
        ncout.createDimension('n_s' , n_s)
        ncout.setncattr("Nrows", Nrows)
        ncout.setncattr("Ncols", Ncols)
            
        r_var=ncout.createVariable('row', 'i4', ('n_s',))
        r_var.long_name     = 'row index'
        r_var[:]=row[:]
            
        c_var=ncout.createVariable('col', 'i4', ('n_s',))
        c_var.long_name     = 'column index'
        c_var[:]=col[:]
            
        s_var=ncout.createVariable('S', 'f4', ('n_s',))
        s_var.long_name     = 'matrix value'
        s_var[:]=weights[:]
        


def IsInElement(x,y,xp,yp):
    IsIn=False
    c1 = (x[1] - x[0]) * (yp - y[0]) - (y[1] - y[0]) * (xp - x[0])
    c2 = (x[2] - x[1]) * (yp - y[1]) - (y[2] - y[1]) * (xp - x[1])
    c3 = (x[0] - x[2]) * (yp - y[2]) - (y[0] - y[2]) * (xp - x[2])
    if ( ( c1 > 0 and c2 > 0 and c3 > 0) or ( c1 < 0 and c2 < 0 and c3 < 0) ):
        IsIn=True
    if (c1*c2*c3 == 0): # include points on triangle
        IsIn=True
    return IsIn

def FindElement(x,y,e,xi,yi):
    nd=len(e.shape)
    e=np.squeeze(e)
    j=-9999
    ne=e.shape[0]
    #print(nd)
    #print(ne)
    #print(e)
    if nd > 1: 
        xc = np.squeeze(np.mean(x[e], axis=1))
        yc = np.squeeze(np.mean(y[e], axis=1))
        DistanceToElements = np.abs((xi + 1j*yi) - (xc + 1j*yc))
        n=0
        while (j < 0 and n < ne)  :
            n=n+1
            j = np.argmin( DistanceToElements )
            xl = np.squeeze(x[e[j,:]])
            yl = np.squeeze(y[e[j,:]])
            IsIn=IsInElement(xl,yl,xi,yi)
            if IsIn :
                return j
            else:
                DistanceToElements[j]=float('inf')
                j=-9999
    else:
        xl = np.squeeze(x[e])
        yl = np.squeeze(y[e])
        IsIn=IsInElement(xl,yl,xi,yi)
        if IsIn:
            j=0
            return j
        else:
            j=-9999
            return j
        
    return j
"""
import matplotlib.tri as mtri
def compute_mesh_to_mesh_interp_weights(x, y, e, xi, yi, flout):

# Assume x, y are vertex coords (N,), triangles is (M, 3) connectivity array
    e0=e-1
    triang = mtri.Triangulation(x, y, e0)

    # z are the known values at each vertex (N,)
    linear_interp = mtri.LinearTriInterpolator(triang, z)

    # Evaluate at new points (callable directly)
    z_new = linear_interp(x_new, y_new)
    
"""    

def universal_len(obj):
    try:
        return len(obj)
    except TypeError:
        return 1


def compute_mesh_to_mesh_interp_weights(x, y, e, xi, yi):
    """
    Compute mesh-to-mesh interpolation weights using barycentric coordinates.
    
    Parameters:
    -----------
    x : array-like
        X coordinates of source mesh nodes
    y : array-like
        Y coordinates of source mesh nodes
    e : array-like
        Element connectivity matrix (n_elements x 3 for triangular elements)
        (nodes indexed from 1 to nn)
    xi : array-like
        X coordinates of target points
    yi : array-like
        Y coordinates of target points
        
    Returns:
    --------
    weights : ndarray
        Interpolation weights (n_points x 3)
    nodes : ndarray
        Node indices for each point (n_points x 3)
    elenum : ndarray
        Element number for each point (n_points,)
    Dist2EleCenter : ndarray
        Distance to element center for each element
    """
    
    # Convert to numpy arrays
    
    deg2kmY=111.
    UseNearestEle = False #if True just use closest element center
    N = 12 # search N nearest elements (nearest by element center to target node distance)
            
    print(xi)
    x = np.asarray(x)
    y = np.asarray(y)
    e = np.asarray(e)
    xi = np.asarray(xi)
    yi = np.asarray(yi)
    print("e.shape")
    print(e.shape)
    # convert node indexs to 0 .. nn-1
    e0=e-1
    

#    triangle_indices, weights, valid_mask=compute_and_save_weights(x, y, e0, xi, yi)
#    np.savetxt("triangle_indices.txt",triangle_indices)
#    np.savetxt("weights.txt",weights)
#    np.savetxt("mask.txt",valid_mask)

    xc = np.mean(x[e0], axis=1)
    yc = np.mean(y[e0], axis=1)
    
    # Initialize output arrays
    n_points = len(xi)
    n_elements = len(e)
    weights = np.zeros((n_points, 3))
    nodes = np.zeros((n_points, 3), dtype=int)
    elenum = np.zeros(n_points, dtype=int)
    Dist2EleCenter = np.zeros(n_points)
    
    t0 = time.time()

    for k in range(n_points):
        x0=xi[k]
        y0=yi[k]
        deg2kmX=np.cos( np.pi * y0 / 180.)*deg2kmY
        #distances = np.abs((x0 + 1j*y0) - (xc + 1j*yc))
        distances = np.abs( deg2kmX*(x0 - xc) + 1j*deg2kmY*(y0 - yc))
        if UseNearestEle:
            jg=np.argmin(distances)
        else:
            raw_indices = np.argpartition(distances, N)[:N]
            sorted_sub_indices = np.argsort(distances[raw_indices])
            jg = raw_indices[sorted_sub_indices]
        if UseNearestEle :
            j=jg
        else:
            j=FindElement(x,y,e0[jg,:],x0,y0)
            if j < 0:
                print("couldn't find element for point : "+ str(k))
                print(str(x0)+" : "+str(y0))
                j = jg[0]
                print("using closest element at distance : "+ str(distances[j]))
            else:
                j=jg[j]

        elenum[k] = j
        Dist2EleCenter[k] = distances[j]
        xl = x[e0[j, :]]
        yl = y[e0[j, :]]
            
        # Compute barycentric coordinates using shoelace formula for areas
        # Area of triangle formed by vertices 1, 2, and point (a3)
        xt = np.array([xl[0], xl[1], x0, xl[0]])
        yt = np.array([yl[0], yl[1], y0, yl[0]])
        a3 = -np.dot(xt[1:4] - xt[0:3], yt[0:3] + yt[1:4]) / 2
        # Area of triangle formed by vertices 3, 1, and point (a2)
        xt = np.array([xl[2], xl[0], x0, xl[2]])
        yt = np.array([yl[2], yl[0], y0, yl[2]])
        a2 = -np.dot(xt[1:4] - xt[0:3], yt[0:3] + yt[1:4]) / 2
        # Area of triangle formed by point, vertices 2, 3 (a1)
        xt = np.array([x0, xl[1], xl[2], x0])
        yt = np.array([y0, yl[1], yl[2], y0])
        a1 = -np.dot(xt[1:4] - xt[0:3], yt[0:3] + yt[1:4]) / 2

        # Normalize to get barycentric weights
        total_area = a1 + a2 + a3
        weights[k, :] = [a1, a2, a3] / total_area

        nodes[k, :] = e[j, :] #<- indexed 1 .. nn
        # Progress reporting every 100 iterations
        if (k + 1) % 10 == 0:
            t1 = time.time()
            time_per_iter = (t1 - t0) / (k + 1)
            time_remaining = (n_points - k - 1) * time_per_iter / 60
            print(f"Progress: {k+1}/{n_points}")
            print(f"Time remaining: {time_remaining:.2f} minutes")
    return weights, nodes, elenum, Dist2EleCenter


def InterpolateField2Nodes(nodes,weights, f):
    fi=np.zeros(weights.shape[0])
    for k in range(weights.shape[0]):
        fl=f[nodes[k,:]]
        wl=weights[k,:]
        fi[k]=np.dot(wl,fl)
        if (not np.abs(fi[k]) > 0.):
           fi[k]=0.
        if ( fi[k]>np.max(fl)  ):
           fi[k]=np.max(fl)
        if ( fi[k]<np.min(fl)  ):
           fi[k]=np.min(fl)
    return fi


#!/bin/bash
#PBS -N my_array_job
#PBS -l select=1:ncpus=1:mem=2gb
#PBS -l walltime=01:00:00
#PBS -J 1-10%5
#PBS -o my_job_array_out.txt
#PBS -e my_job_array_err.txt

# Move to the directory where the job was submitted
#-->cd $PBS_O_WORKDIR
#-->echo "Running on node: $(hostname)"
#--> python my_script.py --task $PBS_ARRAY_INDEX

def WriteInterpJobscriptPBS(fl,flin,mshfl,Njobs, ComputeNodes):
    
    meshslash=mshfl.rfind('/')+1
    TmpOutDir="STOFSInterpWeights."+mshfl[meshslash:len(mshfl)-4]
    WghtFl="STOFS.wght."+mshfl[meshslash:len(mshfl)-4]+".txt"
    WghtFlNetCDF="STOFS.wght."+mshfl[meshslash:len(mshfl)-4]+".nc"
    with open(fl, 'w') as f:
        f.write("#PBS -N ESMPy\n")
        f.write("#PBS -j oe\n")
        f.write("#PBS -S /bin/bash\n")
        f.write("#PBS -q dev\n")
        f.write("#PBS -A NWPS-DEV\n")
        f.write("#PBS -l walltime=01:00:00\n")

        f.write("#PBS -J 1-"+str(Njobs)+"\n")
        
        f.write("#PBS -l select=1:ncpus=1:mem=8G\n")
        f.write("#PBS -l place=excl\n")
        f.write("#PBS -l debug=true\n")

        f.write("module reset\n")
        f.write("module load PrgEnv-intel/8.5.0\n")
        f.write("module load intel/19.1.3.304\n")
        f.write("module load craype/2.7.17\n")
        f.write("module load cray-mpich/8.1.19\n")
        f.write("module load hdf5-C/1.14.0\n")
        f.write("module load netcdf-C/4.9.2\n")
        f.write("module load esmf-C/8.6.0\n")
        f.write("module load ve/hafs/2.1\n")

        f.write("pip list -v\n")



        #yi[k]=float(values[4])
        f.write("#!/bin/bash \n")
        f.write("#SBATCH --job-name=STOFS_interp_masterscript \n")
#        f.write("#SBATCH --ntasks="+str(N)+" \n")
        f.write("#SBATCH --ntasks=1 \n") # ntasks per interpolation
        f.write("#SBATCH --time=08:00:00 \n") 
        f.write("#SBATCH --output=mpi_test_%j.log \n")
        f.write("#SBATCH --error=%j.err \n")
        f.write("#SBATCH --account=marine-cpu \n")
        f.write("#SBATCH --nodes="+str(ComputeNodes)+" \n")
        f.write("#SBATCH --ntasks-per-core=1"+" \n")
        f.write("#SBATCH --array=0-"+str(Njobs-1)+" \n")

        f.write(" \n")

        f.write("module purge \n")
        f.write("module use /scratch4/NCEPDEV/marine/Ali.Salimi/Hera_Data/HR4-OPT/FromJessica/Keston/ICunstructuredRuns15km-implicit-450s/global-workflow/sorc/ufs_model.fd/modulefiles \n")
        f.write("module load ufs_ursa.intel \n")
        f.write("module load py-scipy/1.14.1 \n")
        f.write("module load py-netcdf4/1.7.1.post2 \n")
        f.write("pip list \n")
        f.write("# calculate interpolation weights in parallel geographically \n")
        f.write("srun python GeoSubsetInterpolateSTOFS.py "+flin+" "+mshfl+" $SLURM_ARRAY_TASK_ID " + str(Njobs)+" > InterpJob.$SLURM_ARRAY_TASK_ID.out \n")
        f.write("wait\n")
        f.write("# concatonate different parts of the mesh to common text file \n")
        f.write("cat "+TmpOutDir+"/Part.IntrpWghts.*.txt > "+WghtFl+" \n")
        f.write("# convert output weights to netcdf file \n")
        f.write("python ConvertWeights2Netcdf.py "+flin+" "+mshfl+" \n")


def WriteInterpJobscriptSlurm(fl,flin,mshfl,Njobs, ComputeNodes):
    
    meshslash=mshfl.rfind('/')+1
    TmpOutDir="STOFSInterpWeights."+mshfl[meshslash:len(mshfl)-4]
    WghtFl="STOFS.wght."+mshfl[meshslash:len(mshfl)-4]+".txt"
    WghtFlNetCDF="STOFS.wght."+mshfl[meshslash:len(mshfl)-4]+".nc"
    with open(fl, 'w') as f:
        #yi[k]=float(values[4])
        f.write("#!/bin/bash \n")
        f.write("#SBATCH --job-name=STOFS_interp_masterscript \n")
#        f.write("#SBATCH --ntasks="+str(N)+" \n")
        f.write("#SBATCH --ntasks=1 \n") # ntasks per interpolation
        f.write("#SBATCH --time=08:00:00 \n") 
        f.write("#SBATCH --output=mpi_test_%j.log \n")
        f.write("#SBATCH --error=%j.err \n")
        f.write("#SBATCH --account=marine-cpu \n")
        f.write("#SBATCH --nodes="+str(ComputeNodes)+" \n")
        f.write("#SBATCH --ntasks-per-core=1"+" \n")
        f.write("#SBATCH --array=0-"+str(Njobs-1)+" \n")

        f.write(" \n")

        f.write("module purge \n")
        f.write("module use /scratch4/NCEPDEV/marine/Ali.Salimi/Hera_Data/HR4-OPT/FromJessica/Keston/ICunstructuredRuns15km-implicit-450s/global-workflow/sorc/ufs_model.fd/modulefiles \n")
        f.write("module load ufs_ursa.intel \n")
        f.write("module load py-scipy/1.14.1 \n")
        f.write("module load py-netcdf4/1.7.1.post2 \n")
        f.write("pip list \n")
        f.write("# calculate interpolation weights in parallel geographically \n")
        f.write("srun python GeoSubsetInterpolateSTOFS.py "+flin+" "+mshfl+" $SLURM_ARRAY_TASK_ID " + str(Njobs)+" > InterpJob.$SLURM_ARRAY_TASK_ID.out \n")
        f.write("wait\n")
        f.write("# concatonate different parts of the mesh to common text file \n")
        f.write("cat "+TmpOutDir+"/Part.IntrpWghts.*.txt > "+WghtFl+" \n")
        f.write("# convert output weights to netcdf file \n")
        f.write("python ConvertWeights2Netcdf.py "+flin+" "+mshfl+" \n")

            
    flintrp="STOFS.to."+mshfl[meshslash:len(mshfl)-4]+".sh"
    flout=flin[0:-2]+mshfl[meshslash:len(mshfl)-4]+".nc"
    flinuv=flin[0:-3]+".vel.nc"
    floutuv=flinuv[0:-2]+mshfl[meshslash:len(mshfl)-4]+".nc"
    with open(flintrp, 'w') as f:
        f.write("#!/bin/bash \n")
        f.write("#SBATCH --job-name=STOFS_interp_masterscript \n")
        f.write(" \n")
        f.write("module purge \n")
        f.write("module use /scratch4/NCEPDEV/marine/Ali.Salimi/Hera_Data/HR4-OPT/FromJessica/Keston/ICunstructuredRuns15km-implicit-450s/global-workflow/sorc/ufs_model.fd/modulefiles \n")
        f.write("module load ufs_ursa.intel \n")
        f.write("module load py-scipy/1.14.1 \n")
        f.write("module load py-netcdf4/1.7.1.post2 \n")
        f.write("pip list \n")
        f.write("# calculate interpolation weights in parallel geographically \n")
        f.write("python InterpolateSTOFS.py "+flin+" "+mshfl+" "+flout+" zeta 2\n")
        f.write("python InterpolateSTOFS.py "+flinuv+" "+mshfl+" "+floutuv+" u-vel:v-vel 2\n")

