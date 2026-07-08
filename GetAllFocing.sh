#!/bin/bash 

# Setup and load modules 
module load PrgEnv-intel/8.1.0
module load craype/2.7.8
module load intel/19.1.3.304
module load cfp/2.0.4
module load prod_util/2.0.8
module load prod_envir/2.0.5

# 0.a Set necessary variables

# This script retrieves and processes forcing for a forecast period
date=$1
cycl=$2
mesh=$3


##date=20260707 
##cycl=00
##mesh="../meshes/RWPS.V0a.small.msh"

meshname="${mesh##*/}"
meshname="${meshname: 0: -4}"

echo "retrieving and processing RWPS forcing for $date z$cycl for WW3 mesh $mesh"

rm FetchWinds.out ProcWinds.out FetchCurrents.out ProcCurrents.out FetchWaterLevel.out ProcWaterLevel.out

(
    echo "retrieving nbm and rrfs winds for $date z$cycl"
    sh GetWinds.sh $date $cycl  > FetchWinds.out
    echo "processing winds for $date z$cycl for $mesh"
    sh ProcessWinds.sh $date $cycl $mesh > ProcWinds.out
)&

(
    echo "retrieving rtofs and stofs currents for $date z$cycl"
    sh GetCurrents.sh $date $cycl > FetchCurrents.out
    echo "processing currents for $date z$cycl for $mesh"
    sh ProcessCurrentsFcasts.sh $date $cycl $mesh  > ProcCurrents.out
)&

(
    echo "retrieving stofs water level for $date z$cycl"
    sh GetWaterLevel.sh $date $cycl > FetchWaterLevel.out
    echo "processing water level for $date z$cycl for $mesh"
    sh ProcessWaterLevelFcasts.sh $date $cycl $mesh  > ProcWaterLevel.out
)&

wait
echo "Finished preprocessing for $date z$cycl for $mesh"

cp $meshname.$date.$cycl.vel.stofsxrtofs.nc $meshname.$date.$cycl.current.nc
echo "current forcing file:  $meshname.$date.$cycl.current.nc"

cp $meshname.$date.$cycl.cwl.stofs.nc $meshname.$date.$cycl.waterlevel.nc
echo "water level forcing file:  $meshname.$date.$cycl.watterlevel.nc"

cp rwps_winds.$meshname.$date.$cycl/rwps.est.$meshname.$date.$cycl.wind10m.nc $meshname.$date.$cycl.wind.nc
echo "wind forcing file:  $meshname.$date.$cycl.wind.nc"

