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
    """xarray-like accessor for pwrd methods.

    Methods can be accessed through the `pwrd` accessor e.g.
    `da.pwrd.convert_longitude()` where `da` is an `xarray.Dataset` or
    `xarray.DataArray`.
    """

    def __init__(self, da):
        self._da = da

    def era5_from_area_bounds(self, area: gpd.GeoDataFrame):
        """Select elements of an xarray Dataset or DataArray from the total bounds of an area.

        Parameters
        ----------
        area:
            A geopandas.GeoDataFrame of areas. The bounding box of all
            areas is used in the data selection.

        Returns
        -------
        xarray.Dataset | xarray.DataArray
            An xarray-like object selecting only data covered by the
            bounding box of `area`

        Notes
        -----
        This method is designed to operate on data
        directly from the EarthDataHub. This means that the
        `.convert_longitude()` method should not be called after applying
        this method.

        """
        return from_area(self._da, area)

    def convert_longitude(self):
        """Convert longitude from 0->360 to -180->180.

        ERA5 data from the EarthDataHub has longitudes from 0 to 360
        degrees. This method converts data to use -180 to 180, for
        consistency with other data sources.

        Returns
        -------
        xarray.Dataset | xarray.DataArray
            An xarray-like object with latitude converted to be in
            the range -180 to 180

        Warnings
        --------
        Beware that the conversion doesn't check the
        format the longitude coordinate is in, so calling this on data
        already in the -180 to 180 format may result in bad data
        """
        return self._da.assign_coords(longitude=convert_longitude)


class LocalCache:
    """A local cache for storing zarr data from earthdatahub."""

    def __init__(self, path=None):
        path = path or Path.cwd()
        self.path = Path(path)

    def create_cache_store(self, fsspec_store):
        """Create a cache store from an existing FSSpecStore."""
        fname = Path(fsspec_store.path).name
        local_store = LocalStore(self.path / fname)
        return CacheStore(store=fsspec_store, cache_store=local_store)
