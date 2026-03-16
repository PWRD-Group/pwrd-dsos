from pathlib import Path

import geopandas as gpd
import xarray as xr
from zarr.storage import LocalStore
from zarr.experimental.cache_store import CacheStore

# Type alias for an xarray Dataset or DataArray
XrLike = xr.Dataset | xr.DataArray


def convert_longitude(ds: XrLike):
    """Given an xarray dataset, converts longitude from 0->360 to -180->180.

    Usage:

    Given a dataset `ds` use as
    `ds = ds.assign_coords(longitude=convert_longitude)`
    """
    return ((ds.longitude + 180) % 360) - 180


def from_area(xdata: XrLike, area: gpd.GeoDataFrame) -> XrLike:
    """Select data from an xarray in a bounding box defined by area."""
    # Ensure that bounds are in EPSG:4326 (WGS 84) coordinates
    west, south, east, north = area.to_crs(4326).total_bounds

    # Convert from -180->180 to 0->360
    west = west % 360
    east = east % 360

    # If west has ended up greater than east then we have crossed the
    # Greenwich meridian, need to concat two slices together
    lats = [(west, 360), (0, east)] if west > east else [(west, east)]

    out = xr.concat([xdata.sel(longitude=slice(*i)) for i in lats], dim="longitude")
    # Latitude selection presumes ordering from north to south
    return out.sel(latitude=slice(north, south)).assign_coords(longitude=convert_longitude)


class LocalCache:

    def __init__(self, path=None):
        path = path or Path.cwd()
        self.path = Path(path)

    def create_cache_store(self, fsspec_store):
        fname = Path(fsspec_store.path).name
        local_store = LocalStore(self.path / fname)
        return CacheStore(store=fsspec_store, cache_store=local_store)
