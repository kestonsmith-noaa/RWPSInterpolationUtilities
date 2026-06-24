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
winddir="forecasts/wind.$date.$cycl"

# extract mesh name from path
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

##LocalFS  = [ rwps_pr, rwps_hi, rwps_ak, rwps_conus, rwps_na] # file names
##VarFS    = [ 4.     , 4.    , 9.      , 16.       , 25.    ] # (m m /s /s)
##LambdaFS = [ 150.   , 200.  , 500.    , 1000.     , 1500.  ] # (km)

#Convert NBM deom speed and direction to u,v
python SpdDir2UVnbm.py $nbm_oc $nbm_oc_uv

python InterpWindToMesh.py $nbm_oc_uv $mesh $rwps_oc 100. 0. 1
python InterpWindToMesh.py $rrfs_pr $mesh $rwps_pr 4. 150.
python InterpWindToMesh.py $rrfs_hi $mesh $rwps_hi 4. 200.
python InterpWindToMesh.py $rrfs_ak $mesh $rwps_ak 9. 500.
python InterpWindToMesh.py $rrfs_conus $mesh $rwps_conus 16. 1000.
python InterpWindToMesh.py $rrfs_na $mesh $rwps_na 50. 1500.

#Interpolate NBM in time to times within the NBM forecast covered by the RRFS forecast 
python InterpTimeNBM.py $rwps_oc $rwps_pr $rwps_oc_ti 

python BlendWindForecasts.py $rwps_oc_ti $rwps_pr blend1.nc
python BlendWindForecasts.py blend1.nc $rwps_hi blend2.nc
python BlendWindForecasts.py blend2.nc $rwps_ak blend3.nc
python BlendWindForecasts.py blend3.nc $rwps_conus blend4.nc
python BlendWindForecasts.py blend4.nc $rwps_na $rwps_est

