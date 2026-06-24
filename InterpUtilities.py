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
    print("TimeVarName = "+TimeVarName)
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

def CopyAttributes(VarOld, VarNew)
    #Copy attributes from old file to new
    for jv in range(nvar):
        att_names = VarOld.ncattrs()
        for jatt in range(len(att_names)):
            att_name=att_names[jatt]
            if (not (att_name=="_FillValue")):
                att_value = var.getncattr(att_name)
                VarNew.setncattr(att_name, att_value)
    return

from datetime import datetime, date, timedelta
def UnixTimeToDaysSince1990(UnixTime):
    """
    Converts a time value in seconds since 1970-01-01 UTC to 
    days since 1990-01-01 UTC.
    """
    # 1. Define the two epoch start dates (using UTC to avoid timezone issues)
    epoch_1970 = datetime(1970, 1, 1, tzinfo=None) # naive datetime is fine if assuming UTC
    epoch_1990 = datetime(1990, 1, 1, tzinfo=None)
    # 2. Convert the input seconds to a datetime object (relative to 1970)
    # Note: Use datetime.utcfromtimestamp() for Python 3.5+, or datetime.fromtimestamp(ts, timezone.utc) for newer Python
    # For simplicity assuming the input is a standard Unix timestamp (UTC)
    time_datetime_1970 = epoch_1970 + timedelta(seconds=UnixTime)
    # 3. Calculate the time difference between the target date and the 1990 epoch
    delta = time_datetime_1970 - epoch_1990
    # 4. Extract the total number of days from the timedelta object
    days_since_1990 = delta.days + delta.seconds / (24 * 3600) # Account for fractional days
    return days_since_1990
