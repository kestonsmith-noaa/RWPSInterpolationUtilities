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

#date=$1
#cycl=$2
#mesh=$3

cdir=$(pwd)

echo "directory : $cdir"

source ./PDY_rwps

meshname="${mesh##*/}"
meshname="${meshname: 0: -4}"

stofslev="stofs.$date.$cycl/stofs_2d_glo.t00z.fields.cwl.nc"

varnames="zeta"

## STOFS interpolation
stofs_wghts="InterpolationWeights.$meshname.stofs.nc"
stofs_dists="DistToBndy.$meshname.stofs.nc"
stofs_rwps="$meshname.$date.$cycl.cwl.stofs.nc"


echo "$meshname"
echo "$stofs_wghts"
echo "$stofs_rwps"

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

python InterpolateWithWeights.py $stofslev $stofs_wghts $stofs_rwps $varnames 0 
python AddMeshGeomToFile.py $stofs_rwps $mesh
##python AddErrVarToFile.py $stofs_rwps $stofs_dists 1.

