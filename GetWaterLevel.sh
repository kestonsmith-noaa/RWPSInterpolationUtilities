#!/bin/bash

## This script retrieves stofs water level as netcdf file

date=$1
cycl=$2
stofs/GetSTOFS.sh $date $cycl waterlevel 
