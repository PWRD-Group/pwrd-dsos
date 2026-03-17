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
    new_lon = ((ds.longitude + 180) % 360) - 180
    return new_lon.assign_attrs(units="degrees")


def from_area(xdata: XrLike, area: gpd.GeoDataFrame) -> XrLike:
    """Select data from an xarray in a bounding box defined by area."""
    # Ensure that bounds are in EPSG:4326 (WGS 84) coordinates
    west, south, east, north = area.to_crs(4326).total_bounds

    # This function requires `xdata` to have longitudes from 0 -> 360
    if xdata.longitude.units != "degrees_east":
        msg = "The longitude units of the xarray should be 'degrees_east'"
        raise ValueError(msg)

    # Convert from -180->180 to 0->360
    west = west % 360
    east = east % 360

    # If west has ended up greater than east then we have crossed the
    # Greenwich meridian, need to concat two slices together
    lats = [(west, 360), (0, east)] if west > east else [(west, east)]

    out = xr.concat([xdata.sel(longitude=slice(*i)) for i in lats], dim="longitude")
    # Latitude selection presumes ordering from north to south
    return out.sel(latitude=slice(north, south))


@xr.register_dataset_accessor("pwrd")
@xr.register_dataarray_accessor("pwrd")
class PwrdAccessor:
    def __init__(self, da):
        self._da = da

    def era5_from_area_bounds(self, area):
        """Select elements of an xarray Dataset or DataArray from the total bounds of an area"""
        return from_area(self._da, area)

    def convert_longitude(self):
        """Convert longitude from 0->360 to -180->180."""
        return self._da.assign_coords(longitude=convert_longitude)


class LocalCache:

    def __init__(self, path=None):
        path = path or Path.cwd()
        self.path = Path(path)

    def create_cache_store(self, fsspec_store):
        fname = Path(fsspec_store.path).name
        local_store = LocalStore(self.path / fname)
        return CacheStore(store=fsspec_store, cache_store=local_store)
