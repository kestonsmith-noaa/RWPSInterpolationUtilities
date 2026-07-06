#!/bin/bash

# This script retrieves and processes forcing for a forecast period
date=$1
cycl=$2
mesh=$3
(
    echo "retrieving nbm and rrfs winds for $date z$cycl"
    sh GetWinds.sh $date $cycl
    echo "processing winds for $date z$cycl for $mesh"
    sh ProcessWinds.sh $date $cycl $mesh
)&

(
    echo "retrieving rtofs and stofs currents for $date z$cycl"
    sh GetCurrents.sh $date $cycl
    echo "processing currents for $date z$cycl for $mesh"
    sh ProcessCurrentsFcasts.sh $date $cycl $mesh
)&

(
    echo "retrieving stofs water level for $date z$cycl"
    sh GetWaterLevel.sh $date $cycl
    echo "processing water level for $date z$cycl for $mesh"
    sh ProcessWaterLevelFcasts.sh $date $cycl $mesh
)&

