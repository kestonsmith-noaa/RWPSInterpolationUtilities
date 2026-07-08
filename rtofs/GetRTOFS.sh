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

#date=20260602
date=$1

tmpdir="tmp.rtofs.$date"
filesin="/lfs/h1/ops/prod/com/rtofs/v2.5/rtofs.$date/*prog.nc"
flout="rtofs.$date.nc"

mkdir $tmpdir
cp $filesin $tmpdir/
python rtofs/GetRTOFSfcst.py $tmpdir $flout
rm -rf $tmpdir
