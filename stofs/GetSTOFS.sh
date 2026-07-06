#!/bin/bash

##script for retrieving stofs current and/or water level

date=$1
cycl=$2

if [ "$#" -lt 3 ]; then
    echo "No arguments field argument."
    echo "Retrieving both stofs currents and stofs water level."
    fields="currents,waterlevel"
else
    fields=$3
fi

mkdir stofs.$date.$cycl

if [[ "$fields" == *"current"* ]]; then
    echo retrieving stofs current for $date cycle $cycl
    cp /lfs/h1/ops/prod/com/stofs/v2.1/stofs_2d_glo.$date/stofs_2d_glo.t"$cycl"z.fields.cwl.vel.nc  stofs.$date.$cycl/
fi

if [[ "$fields" == *"level"* ]]; then
    echo retrieving stofs water level for $date cycle $cycl
    cp /lfs/h1/ops/prod/com/stofs/v2.1/stofs_2d_glo.$date/stofs_2d_glo.t"$cycl"z.fields.cwl.nc  stofs.$date.$cycl/
fi

