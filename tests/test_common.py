import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
import xarray as xr
import xvec  # noqa: F401

from pwrd.common import xarray_to_xvec


def test_xarray_to_xvec():

    # Make an xarray that has dimensions of area and day with some
    # dummy data
    data = [[1, 2], [3, 4]]
    # Use C and A so that we have a different ordering than areas
    area_coord = ["C", "A"]
    day_coord = [1, 2]
    xarr = xr.DataArray(data, dims=["area", "day"], coords=(area_coord, day_coord))

    # Make an areas GeoDataframe
    boxes = [
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
        Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
        Polygon([(0, 1), (1, 1), (1, 2), (0, 2)]),
    ]

    areas = gpd.GeoDataFrame(
        geometry=boxes,
        index=pd.Index(["A", "B", "C", "D"], name="area"),
    )

    out = xarray_to_xvec(xarr, areas)
    # Geometry should now be a dimension...
    assert "geometry" in out.dims
    # but area should now not be
    assert "area" not in out.dims
    # The underlying data should not have changed
    assert (xarr.data == out.data).all()
    # ... and the area ordering should not have changed
    assert (out.coords["area"].data == xarr.coords["area"].data).all()
