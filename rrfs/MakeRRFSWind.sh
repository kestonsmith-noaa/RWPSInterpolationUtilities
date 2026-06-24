#!/bin/bash

# This script takes rrfs grib2 forecast files, extracts 10m u and v wind
# components and outputs to netcdf. Comand line arguments are
# forecast time: YYYYMMDD
# forecast cycle: CC
# frecast region: hi,pr,na,ak or conus
#
# For example call as:
# sh MakeRRFSWind.sh 20260428 00 pr
# to produce output file:
# rrfs.20260428.00.wind10m.pr.nc
#
echo "MakeRRFSWind.sh fetching rrfs : time = $1, cycle = $2, domain = $3"

module load intel-oneapi/2022.2.0.262
module load wgrib2/2.0.8

INPUT_DIR="/lfs/h1/ops/para/com/rrfs/v1.0/rrfs.$1/$2"
OUTPUT_DIR="wind.$1.$2"
OUTPUT_FILE="$OUTPUT_DIR/rrfs.$1.$2.wind10m.$3.nc"

mkdir "$OUTPUT_DIR"
# Remove existing output file to avoid mixing old data
rm -f "$OUTPUT_FILE"

echo "writing 10m wind from $INPUT_DIR to $OUTPUT_FILE"

# Note: Ensure files are in the correct chronological order (e.g., sorted by name)
for file in $(ls "$INPUT_DIR"/rrfs.t$2z.2dfld.*km.f*.$3.grib2 | sort); do
    echo "Processing: $file"
    # Convert and append to the NetCDF file
    # -netcdf: specifies the output format and filename
    # -append: adds data to the existing netcdf file instead of overwriting
    wgrib2 "$file"  -match ":UGRD:10 m" -append -netcdf "$OUTPUT_FILE"
    wgrib2 "$file"  -match ":VGRD:10 m" -append -netcdf "$OUTPUT_FILE"
done

echo "rrfs processing complete for forecast date $1, cycle $2, domain $3"
echo "output written to: $OUTPUT_FILE"
