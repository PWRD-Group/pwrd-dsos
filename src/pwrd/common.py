from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np
import xvec  # noqa: F401

if TYPE_CHECKING:
    import geopandas as gpd
    import xarray as xr
    # Type alias for an xarray Dataset or DataArray
    XrLike = xr.Dataset | xr.DataArray
    

def _xarray_to_xvec(xarr: XrLike, areas: gpd.GeoDataFrame) -> XrLike:
    """Convert an xarray to a xvec compatible format using a GeoDataFrame."""

    name = areas.index.name
    # This should be the geometries in the same order as the index of
    # xarr
    geometries = np.array(areas.loc[xarr[name]].geometry)
    
    return (
        xarr
        # Assign a new coordinate. Note need to convert Geometry
        # array to a numpy object array The .loc call hopefully
        # ensures that the xarray is aligned properly with the
        # geometry
        .assign_coords(geometry=(name, geometries))
        .swap_dims({name: "geometry"})
        .xvec
        .set_geom_indexes("geometry", crs=areas.crs)
    )
    
