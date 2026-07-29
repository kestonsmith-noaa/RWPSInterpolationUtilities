#!/bin/bash
#PBS -N ESMPy
#PBS -j oe
#PBS -S /bin/bash
#PBS -q dev
#PBS -A NWPS-DEV
#PBS -l walltime=00:05:00
#PBS -l select=1:ncpus=1:mem=8G
#PBS -l place=excl
#PBS -l debug=true

module reset
module load PrgEnv-intel/8.5.0
module load intel/19.1.3.304
module load craype/2.7.17
module load cray-mpich/8.1.19
module load hdf5-C/1.14.0
module load netcdf-C/4.9.2
module load esmf-C/8.6.0
module load ve/hafs/2.1

pip list -v

##date="20260527"
#date=20260602
#cycl="00"
#mesh=meshes/RWPS.V0a.small.msh

date=$1
cycl=$2
mesh=$3
#winddir="forecasts/wind.$date.$cycl"
winddir="wind.$date.$cycl"
windvars="UGRD_10maboveground:VGRD_10maboveground"

# extract mesh name from file path
meshname="${mesh##*/}"
# remove .msh suffix from mesh name
meshname="${meshname: 0: -4}"

# incorporate meshname date and cycle into output directory name to avoid
# applying winds to wrong mesh
outdir="rwps_winds.$meshname.$date.$cycl"

echo "outputing files to: $outdir"

nbm_oc="$winddir/nbm.$date.$cycl.wind10m.oc.nc"
nbm_oc_uv="$winddir/nbm.$date.$cycl.wind10m.oc.uv.nc"

rrfs_pr="$winddir/rrfs.$date.$cycl.wind10m.pr.nc"
rrfs_hi="$winddir/rrfs.$date.$cycl.wind10m.hi.nc"
rrfs_na="$winddir/rrfs.$date.$cycl.wind10m.na.nc"
rrfs_ak="$winddir/rrfs.$date.$cycl.wind10m.ak.nc"
rrfs_conus="$winddir/rrfs.$date.$cycl.wind10m.conus.nc"

rwps_oc="$outdir/nbm.$meshname.$date.$cycl.wind10m.oc.nc"
rwps_oc_ti="$outdir/nbm.$meshname.$date.$cycl.wind10m.oc.ti.nc"
rwps_pr="$outdir/rrfs.$meshname.$date.$cycl.wind10m.pr.nc"
rwps_hi="$outdir/rrfs.$meshname.$date.$cycl.wind10m.hi.nc"
rwps_na="$outdir/rrfs.$meshname.$date.$cycl.wind10m.na.nc"
rwps_ak="$outdir/rrfs.$meshname.$date.$cycl.wind10m.ak.nc"
rwps_conus="$outdir/rrfs.$meshname.$date.$cycl.wind10m.conus.nc"
rwps_est="$outdir/rwps.est.$meshname.$date.$cycl.wind10m.nc"

mkdir $outdir


##weights_file = "InterpolationWeights."+mshfl[meshslash:len(mshfl)-3]+dom+".nc"

##LocalFS  = [ rwps_pr, rwps_hi, rwps_ak, rwps_conus, rwps_na] # file names
##VarFS    = [ 4.     , 4.    , 9.      , 16.       , 25.    ] # (m m /s /s)
##LambdaFS = [ 150.   , 200.  , 500.    , 1000.     , 1500.  ] # (km)
nbm_oc_wghts="InterpolationWeights.$meshname.oc.nc"
rrfs_hi_wghts="InterpolationWeights.$meshname.hi.nc"
rrfs_pr_wghts="InterpolationWeights.$meshname.pr.nc"
rrfs_ak_wghts="InterpolationWeights.$meshname.ak.nc"
rrfs_na_wghts="InterpolationWeights.$meshname.na.nc"
rrfs_conus_wghts="InterpolationWeights.$meshname.conus.nc"

nbm_oc_dist="DistToBndy.$meshname.oc.nc"
rrfs_hi_dist="DistToBndy.$meshname.hi.nc"
rrfs_pr_dist="DistToBndy.$meshname.pr.nc"
rrfs_ak_dist="DistToBndy.$meshname.ak.nc"
rrfs_na_dist="DistToBndy.$meshname.na.nc"
rrfs_conus_dist="DistToBndy.$meshname.conus.nc"


(
    #Convert NBM speed and direction to u,v
    python SpdDir2UVnbm.py $nbm_oc $nbm_oc_uv
    # If the interpolation weights do not already exist for the domains create them
    # also creates distance to boundary used in prescribed error covariance specification
    [ ! -f "$nbm_oc_wghts" ] && python ComputeGriddedToRWPSInterpWeights.py $nbm_oc_uv $mesh 1
    python InterpolateWithWeights.py $nbm_oc_uv $nbm_oc_wghts $rwps_oc $windvars 3
    python AddMeshGeomToFile0.py $rwps_oc $mesh
)&

(
    [ ! -f "$rrfs_hi_wghts" ] && python ComputeGriddedToRWPSInterpWeights.py $rrfs_hi $mesh
    python InterpolateWithWeights.py $rrfs_hi $rrfs_hi_wghts $rwps_hi $windvars -1
    #add mesh geometry into interpolated file
    python AddMeshGeomToFile0.py $rrfs_hi $mesh
    # Add error covariance field to files with interpolated fields for bayesian update
    # Based on distance to boundary of input field and commant line parameters InternalVariance:BoundaryVariance:LengthScale(km) 
    python AddErrVarToFile0.py $rwps_hi $rrfs_hi_dist 4.:40.:200.
)&

(
    [ ! -f "$rrfs_pr_wghts" ] && python ComputeGriddedToRWPSInterpWeights.py $rrfs_pr $mesh
    python InterpolateWithWeights.py $rrfs_pr $rrfs_pr_wghts $rwps_pr $windvars -1
    python AddMeshGeomToFile0.py $rrfs_pr $mesh
    python AddErrVarToFile0.py $rwps_pr $rrfs_pr_dist 4.:40.:150.
)&

(
    [ ! -f "$rrfs_ak_wghts" ] && python ComputeGriddedToRWPSInterpWeights.py $rrfs_ak $mesh
    python InterpolateWithWeights.py $rrfs_ak $rrfs_ak_wghts $rwps_ak $windvars -1
    python AddMeshGeomToFile0.py $rrfs_ak $mesh
    python AddErrVarToFile0.py $rwps_ak $rrfs_ak_dist 9.:90.:500.
)&

(
    [ ! -f "$rrfs_conus_wghts" ] && python ComputeGriddedToRWPSInterpWeights.py $rrfs_conus $mesh
    python InterpolateWithWeights.py $rrfs_conus $rrfs_conus_wghts $rwps_conus $windvars -1
    python AddMeshGeomToFile0.py $rrfs_conus $mesh
    python AddErrVarToFile0.py $rwps_conus $rrfs_conus_dist 16.:160.:1000.
)&

(
    [ ! -f "$rrfs_na_wghts" ] && python ComputeGriddedToRWPSInterpWeights.py $rrfs_na $mesh
    python InterpolateWithWeights.py $rrfs_na $rrfs_na_wghts $rwps_na $windvars -1
    python AddMeshGeomToFile0.py $rrfs_na $mesh
    python AddErrVarToFile0.py $rwps_na $rrfs_na_dist 50.:500.:1500.
)&

wait;
#Interpolate NBM in time to times within the NBM forecast covered by the RRFS forecast
python InterpTime.py $rwps_oc $rwps_pr $rwps_oc_ti $windvars
#add mesh geometry into file
python AddMeshGeomToFile0.py $rwps_oc_ti $mesh
#add prescribed error covariance for nbm oc domain (assumed constant 100. (m/s)^2 )
python AddErrVarToFile0.py $rwps_oc_ti $nbm_oc_dist 100.

cp $rwps_oc_ti $rwps_est
[ ! -f "$rwps_hi" ] && python BayesForecastUpdate.py $rwps_est $rwps_hi $rwps_est $windvars
[ ! -f "$rwps_pr" ] && python BayesForecastUpdate.py $rwps_est $rwps_pr $rwps_est $windvars
[ ! -f "$rwps_ak" ] && python BayesForecastUpdate.py $rwps_est $rwps_ak $rwps_est $windvars
[ ! -f "$rwps_conus" ] && python BayesForecastUpdate.py $rwps_est $rwps_conus $rwps_est $windvars
[ ! -f "$rwps_na" ] && python BayesForecastUpdate.py $rwps_est $rwps_na $rwps_est $windvars
