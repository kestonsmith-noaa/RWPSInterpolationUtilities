#!/bin/bash

# This script retrieves rrfs and nbm winbds and exports as 
# netcdf files

echo "retrieving winds from rrfs and nbm for rwps wind"

echo "sh nbm/MakeNBMWind.sh $1 $2 oc > nbm.oc.out"
nbm/MakeNBMWind.sh $1 $2 oc > nbm.oc.out
echo "retrieved winds from nbm oc domain"
echo "Not retrieving other nbm domain winds"

echo "sh rrfs/MakeRRFSWind.sh $1 $2 na > rrfs.na.out"
rrfs/MakeRRFSWind.sh $1 $2 na > rrfs.na.out
echo "retrieved winds from rrfs na domain"

echo "sh rrfs/MakeRRFSWind.sh $1 $2 ak > rrfs.ak.out"
rrfs/MakeRRFSWind.sh $1 $2 ak > rrfs.ak.out
echo "retrieved winds from rrfs ak domain"

echo "sh rrfs/MakeRRFSWind.sh $1 $2 pr > rrfs.pr.out"
rrfs/MakeRRFSWind.sh $1 $2 pr > rrfs.pr.out
echo "retrieved winds from rrfs pr domain"

echo "sh rrfs/MakeRRFSWind.sh $1 $2 hi > rrfs.hi.out"
rrfs/MakeRRFSWind.sh $1 $2 hi > rrfs.hi.out
echo "retrieved winds from rrfs hi domain"

echo "sh rrfs/MakeRRFSWind.sh $1 $2 conus > rrfs.conus.out"
rrfs/MakeRRFSWind.sh $1 $2 conus > rrfs.conus.out
echo "retrieved winds from rrfs conus domain"

echo "finished retrieving winds from rrfs and nbm for rwps wind"

