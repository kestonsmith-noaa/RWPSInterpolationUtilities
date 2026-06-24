#!/bin/bash

# This script takes ensemble rrfs grib2 forecast files, extracts 10m u and v wind
# components and outputs to netcdf. Comand line arguments are
# forecast time: YYYYMMDD
# forecast cycle: CC
# frecast region: hi,pr,na,ak or conus
#
# For example call as:
# sh MakeEnsRRFSWind.sh 20260428 00 pr
# to produce output file:
# rrfs.20260428.00.wind10m.pr.nc
#

module load intel-oneapi/2022.2.0.262
module load wgrib2/2.0.8

#INPUT_DIR="/lfs/h1/ops/para/com/rrfs/v1.0/rrfs.$1/$2"
OUTPUT_FILE="rrfs.ensemble.$1.$2.wind10m.$3.nc"
INPUT_DIR1="/lfs/h1/ops/para/com/rrfs/v1.0/rrfsens.$1/$2/m001/"

for i in {1..5}; do
    echo "Number: $i"
     rm varname$i.txt
     echo "# variable renaming for ensemble member $i">varname$i.txt
     echo "UGRD:10 m above ground:UGRDn$i" >>varname$i.txt
     echo "VGRD:10 m above ground:VGRDn$i" >>varname$i.txt
done


# Remove existing output file to avoid mixing old data
rm -f "$OUTPUT_FILE"

echo "writing ensemble 10m wind from $INPUT_DIR1 to $OUTPUT_FILE"

# Note: Ensure files are in the correct chronological order (e.g., sorted by name)
for file1 in $(ls "$INPUT_DIR1"/rrfs.t$2z.m001.2dfld.*km.f*.$3.grib2 | sort); do
    file2="${file1//m001/m002}"
    file3="${file1//m001/m003}"
    file4="${file1//m001/m004}"
    file5="${file1//m001/m005}"
    fileN="${file1//m001/m00N}"

    echo "Processing: ensemble $fileN"
    wgrib2 $file1  -match ":UGRD:10 m" -nc_table varname1.txt -append -netcdf "$OUTPUT_FILE"
    wgrib2 $file1  -match ":VGRD:10 m" -nc_table varname1.txt -append -netcdf "$OUTPUT_FILE"

    wgrib2 $file2  -match ":UGRD:10 m" -nc_table varname2.txt -append -netcdf "$OUTPUT_FILE"
    wgrib2 $file2  -match ":VGRD:10 m" -nc_table varname2.txt -append -netcdf "$OUTPUT_FILE"

    wgrib2 $file3  -match ":UGRD:10 m" -nc_table varname3.txt -append -netcdf "$OUTPUT_FILE"
    wgrib2 $file3  -match ":VGRD:10 m" -nc_table varname3.txt -append -netcdf "$OUTPUT_FILE"

    wgrib2 $file4  -match ":UGRD:10 m" -nc_table varname4.txt -append -netcdf "$OUTPUT_FILE"
    wgrib2 $file4  -match ":VGRD:10 m" -nc_table varname4.txt -append -netcdf "$OUTPUT_FILE"

    wgrib2 $file5  -match ":UGRD:10 m" -nc_table varname5.txt -append -netcdf "$OUTPUT_FILE"
    wgrib2 $file5  -match ":VGRD:10 m" -nc_table varname5.txt -append -netcdf "$OUTPUT_FILE"

#    wgrib2 $file2 -nc_table varname2.txt -append -netcdf "$OUTPUT_FILE"
#    wgrib2 $file3 -nc_table varname3.txt -append -netcdf "$OUTPUT_FILE"
#    wgrib2 $file4 -nc_table varname4.txt -append -netcdf "$OUTPUT_FILE"
#    wgrib2 $file5 -nc_table varname5.txt -append -netcdf "$OUTPUT_FILE"


#    cat $file1 $file2 $file3 $file4 $file5  | wgrib2 - -match ":(UGRD|VGRD):10 m" -append -netcdf "$OUTPUT_FILE"
# equivalent alternates
#    cat $file1 $file2 $file3 $file4 $file5 > ensemble.grib2
#    wgrib2 ensemble.grib2 -match ":UGRD:10 m" -append -netcdf "$OUTPUT_FILE"
#    wgrib2 ensemble.grib2 -match ":VGRD:10 m" -append -netcdf "$OUTPUT_FILE"
# or
#    cat $file1 $file2 $file3 $file4 $file5  | wgrib2 - -match ":UGRD:10 m" -append -netcdf "$OUTPUT_FILE"
#    cat $file1 $file2 $file3 $file4 $file5  | wgrib2 - -match ":VGRD:10 m" -append -netcdf "$OUTPUT_FILE"
done

echo "rrfs ensemble processing complete for forecast date $1, cycle $2, domain $3"
echo "output written to: $OUTPUT_FILE"
