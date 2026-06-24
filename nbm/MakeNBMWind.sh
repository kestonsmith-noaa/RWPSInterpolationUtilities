#!/bin/bash

# This script takes rrfs grib2 forecast files, extracts 10m u and v wind
# components and outputs to netcdf. Comand line arguments are

module load intel-oneapi/2022.2.0.262
module load wgrib2/2.0.8

INPUT_DIR="/lfs/h3/mdl/ptmp/mdl.nbm/blend/v5.0/blend.$1/$2/grib2"
WSPD_FILE="$INPUT_DIR/blend.t$2z.wspd.$3.grib2"
WDIR_FILE="$INPUT_DIR/blend.t$2z.wdir.$3.grib2"

OUTPUT_DIR="wind.$1.$2"
OUTPUT_FILE="$OUTPUT_DIR/nbm.$1.$2.wind10m.$3.nc"

mkdir "$OUTPUT_DIR"
# Remove existing output file to avoid mixing old data
rm -f "$OUTPUT_FILE"

echo "writing 10m wind from $INPUT_DIR to $OUTPUT_FILE"

wgrib2 "$WSPD_FILE"  -match ":WIND:10 m" -netcdf "$OUTPUT_FILE"
wgrib2 "$WDIR_FILE"  -match ":WDIR:10 m" -append -netcdf "$OUTPUT_FILE"

echo "nbm processing complete for forecast date $1, cycle $2, domain $3"
echo "output written to: $OUTPUT_FILE"
