#!/bin/bash

# This script retrieves rtofs and stofs as netcdf files


date=$1
cycl=$2
rtofs/GetRTOFSIce.sh $date $cycl &
nbm/GetNBMIce.sh $date $cycl &
wait;
