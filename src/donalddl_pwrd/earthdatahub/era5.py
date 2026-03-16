from zarr.storage import FsspecStore

BASE_URL = "https://data.earthdatahub.destine.eu/era5"
ERA5_STORAGE_OPS = {"client_kwargs": {"trust_env": True}}

land_hourly_store = FsspecStore.from_url(
    f"{BASE_URL}/reanalysis-era5-land-no-antartica-v0.zarr",
    storage_options=ERA5_STORAGE_OPS,
)

hourly_single_levels_store = FsspecStore.from_url(
    f"{BASE_URL}/reanalysis-era5-single-levels-v0.zarr",
    storage_options=ERA5_STORAGE_OPS,
)

