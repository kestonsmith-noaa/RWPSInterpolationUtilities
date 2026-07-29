#aws s3 ls --no-sign-request s3://noaa-nbm-pds/blendv5.0/alaska/2026/05/07/0000/ | g ice
#aws s3 cp --no-sign-request s3://noaa-nbm-pds/blendv5.0/alaska/2026/05/07/0000/iceconcentration/blendv5.0_alaska_iceconcentration_2026-05-07T00:00_2026-05-08T12:00.tif ./
#aws s3 cp --no-sign-request s3://noaa-nbm-pds/blendv5.0/alaska/2026/05/07/0000/icethickness/blendv5.0_alaska_icethickness_2026-05-07T00:00_2026-05-08T12:00.tif ./
#pip install rioxarray xarray pyproj numpy NetCDF4
#python ConvertNBMIcetif2NetCDF.py iceconcentration/blendv5.0_alaska_iceconcentration_2026-05-07T00:00_2026-05-08T12:00.tif
import numpy as np
import pyproj
import rioxarray as rio
import xarray as xr
import sys

flin = sys.argv[1]
flout=flin[0:-4]+".nc"
# 1. Load the original GeoTIFF file
# Replace 'input.tif' with your actual file path
da = rio.open_rasterio(flin)

# 2. Extract the 1D projected X and Y coordinates (in meters)
x_coords = da.x.values
y_coords = da.y.values

# 3. Create a 2D meshgrid of the projected coordinates
X, Y = np.meshgrid(x_coords, y_coords)

# 4. Set up the coordinate transformer
# From EPSG:5936 (Polar Stereographic) to EPSG:4326 (Lat/Lon)
transformer = pyproj.Transformer.from_crs(
    "EPSG:5936", "EPSG:4326", always_xy=True
)

# 5. Compute the 2D curvilinear latitude and longitude grids
lon_2d, lat_2d = transformer.transform(X, Y)

# 6. Restructure the DataArray, dropping old 1D spatial coordinates
# We assume band 0 is your primary data array
data_var = da.isel(band=0).drop_vars(["x", "y", "spatial_ref"])

# 7. Build the NetCDF dataset with 2D curvilinear coordinates
ds = xr.Dataset(
    data_vars={"variable_name": (["y", "x"], data_var.values)},
#    data_vars={"Band1": (["y", "x"], data_var.values)},
    coords={
        "lon": (["y", "x"], lon_2d),
        "lat": (["y", "x"], lat_2d),
    },
)

# Add standard CF-compliant metadata for curvilinear grids
ds["variable_name"].attrs["coordinates"] = "lon lat"
ds["lon"].attrs["units"] = "degrees_east"
ds["lat"].attrs["units"] = "degrees_north"

# 8. Export to NetCDF with compression enabled
ds.to_netcdf(flout, encoding={"variable_name": {"zlib": True}})

print("Conversion complete: "+flout+" saved.")
