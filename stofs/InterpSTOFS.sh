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
stofs.20260630.00/stofs_2d_glo.t00z.fields.cwl.nc
stofs.20260630.00/stofs_2d_glo.t00z.fields.cwl.vel.nc

pip list -v
#stofs.20260630.00/stofs_2d_glo.t00z.fields.cwl.nc
#stofs.20260630.00/stofs_2d_glo.t00z.fields.cwl.vel.nc

#date=20260602
#cycl=00

date=$1
cycl=$2
mesh=$3

meshname="${mesh##*/}"
meshname="${meshname: 0: -4}"
velvarnames="u-vel:v-vel"
waterlevelvarnames="zeta"

flwhgts="../InterpolationWeights.$meshname.stofs.nc"

## [ ! -f "$interpwghts" ] && sh ../ComputeUnstrToRWPSInterpWeights.sh $stofsele $mesh $Nprocs

flin="stofs.$date.$cycl/stofs_2d_glo.t00z.fields.cwl.nc"
flout_rwps="$meshname.$date.cwl.stofs.nc"
python ../InterpolateWithWeights.py $flin $flwhgts $flout_rwps $waterlevelvarnames 0

flin="stofs.$date.$cycl/stofs_2d_glo.t00z.fields.cwl.vel.nc"
flout_rwps="$meshname.$date.vel.cwl.stofs.nc"
python ../InterpolateWithWeights.py $flin $flwhgts $flout_rwps $velvarnames 0



