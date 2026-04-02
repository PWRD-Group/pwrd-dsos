from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np
import xvec  # noqa: F401

if TYPE_CHECKING:
    import geopandas as gpd
    import xarray as xr


def _xarray_to_xvec(xarr: xr.DataArray, areas: gpd.GeoDataFrame) -> xr.DataArray:
    """Convert an xarray to a xvec compatible format using a GeoDataFrame.

    Returns
    -------
    An xarray.DataArray with a geometry dimension that matches a
    coordinate which is the index of the input `areas` GeoDataFrame.
    """

    name = areas.index.name
    # Need to convert Geometry array to a numpy object array. The .loc
    # call hopefully ensures that the xarray is aligned properly with
    # the geometry. This should mean the geometries are in the same
    # order as the index of xarr.
    geometries = np.array(areas.loc[xarr[name]].geometry)

    return (
        xarr
        # Assign a new coordinate.
        .assign_coords(geometry=(name, geometries))
        .swap_dims({name: "geometry"})
        .xvec.set_geom_indexes("geometry", crs=areas.crs)
    )
