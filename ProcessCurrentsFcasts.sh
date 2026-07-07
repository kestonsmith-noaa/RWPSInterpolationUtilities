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

#date="20260602"
#cycl="00"
#mesh="meshes/RWPS.V0a.small.msh"

date=$1
cycl=$2
mesh=$3


meshname="${mesh##*/}"
meshname="${meshname: 0: -4}"

stofscur="stofs.$date.$cycl/stofs_2d_glo.t00z.fields.cwl.vel.nc"
rtofscur="rtofs/rtofs.20260630.nc"

varnames="u-vel:v-vel"

combinedcur=$meshname.$date.$cycl.vel.stofsxrtofs.nc

## STOFS interpolation
stofs_wghts="InterpolationWeights.$meshname.stofs.nc"
stofs_dists="DistToBndy.$meshname.stofs.nc"
stofs_rwps="$meshname.$date.$cycl.vel.cwl.stofs.nc"

if [ ! -f "$stofs_wghts" ]; then
    echo "missing stofs interpolation weights file: $stofs_wghts"
    echo "compute with script ComputeUnstrToRWPSInterpWeights.sh"
    exit 1
fi
if [ ! -f "$stofs_dists" ]; then
    echo "missing stofs distance to boundary file: $stofs_dists"
    echo "compute with script ComputeUnstrToRWPSInterpWeights.sh"
    exit 1
fi

python InterpolateWithWeights.py $stofscur $stofs_wghts $stofs_rwps $varnames 0 &


## RTOFS interpolation
rtofs_rwps="$meshname.$date.vel.rtofs.nc"
rtofs_wghts="InterpolationWeights.$meshname.rtofs.nc"
rtofs_dists="DistToBndy.$meshname.rtofs.nc"

if [ ! -f "$rtofs_wghts" ]; then
    echo "missing rtofs interpolation weights file: $stofs_wghts"
    echo "compute with script ComputeGridToRWPSInterpWeights.py"
    exit 2
fi
if [ ! -f "$rtofs_dists" ]; then
    echo "missing stofs distance to boundary file: $rtofs_dists"
    echo "compute with script ComputeUnstrToRWPSInterpWeights.py"
    exit 2
fi

python InterpolateWithWeights.py $rtofscur $rtofs_wghts $rtofs_rwps $varnames -1 &

wait;

python AddMeshGeomToFile.py $rtofs_rwps $mesh
python AddErrVarToFile.py $rtofs_rwps $rtofs_dists 100.:1.:50.:250.:50.

python AddMeshGeomToFile.py $stofs_rwps $mesh
python AddErrVarToFile.py $stofs_rwps $stofs_dists 1.:100.:50.:250.


python BayesForecastUpdate.py $stofs_rwps $rtofs_rwps $combinedcur $varnames

