import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from shapely.geometry import Polygon
from zarr.storage import FsspecStore

# No testing other than import testing is done on the era5 module
from pwrd.earthdatahub import (
    LocalCache,
    era5,  # noqa: F401
)


def test_local_cache(tmp_path):

    cache = LocalCache(path=tmp_path)
    # A dummy fsspec store
    store = FsspecStore.from_url("file://")
    cache.create_cache_store(store)
    # Should probably actually test something here?


@pytest.fixture
def test_data():

    longitude = np.linspace(0, 359, 360)
    latitude = np.linspace(90, -90, 181)

    # Shape must be (longitude, latitude)
    data = np.arange(360 * 181).reshape(360, 181)

    ds = xr.Dataset(
        {"data": (("longitude", "latitude"), data)},
        coords={"longitude": longitude, "latitude": latitude},
    )

    ds.longitude.attrs["units"] = "degrees_east"
    return ds


def test_convert_longitude(test_data):

    # Assert that we don't have anything < 0
    assert not (test_data.longitude < 0).any()

    # Convert the dataset
    converted_data = test_data.pwrd.convert_longitude()

    # Test that we have some values < 0, the maximum value is <= 180,
    # and the unit is now degrees
    assert (converted_data.longitude < 0).any()
    assert abs(converted_data.longitude).max() <= 180
    assert converted_data.longitude.units == "degrees"


test_from_area_params = dict(
    argnames=("geo", "expected_shape"),
    argvalues=[
        # Rough GB (crosses Greenwich meridian)
        (
            Polygon([(-7, 50), (2, 50), (2, 59), (-7, 59)]),
            (10, 10),
        ),
        # Rough Switzerland (doesn't cross Greenwich, all +ve)
        (
            Polygon([(6, 45), (11, 45), (11, 48), (6, 48)]),
            (6, 4),
        ),
        # Rough California (doesn't cross Greenwich, all -ve)
        (
            Polygon([(-124, 33), (-115, 33), (-115, 42), (-124, 42)]),
            (10, 10),
        ),
    ],
    ids=("GB", "Switzerland", "California"),
)


@pytest.mark.parametrize(**test_from_area_params)
def test_from_area(test_data, geo, expected_shape):

    areas = gpd.GeoDataFrame(
        geometry=[geo],
        index=pd.Index(["area"], name="area"),
        crs=4326,
    )
    selected_ds = test_data.pwrd.era5_from_area_bounds(areas)

    # Check that we have just selected the right bounds
    assert selected_ds.data.shape == expected_shape


def test_from_area_wrong_units(test_data):

    # Use a single geometry from test_from_area_params
    geo = test_from_area_params["argvalues"][0][0]

    areas = gpd.GeoDataFrame(
        geometry=[geo],
        index=pd.Index(["area"], name="area"),
        crs=4326,
    )

    test_data.longitude.attrs["units"] = "degrees"
    # Test whether calling `era5_from_area_bounds` correctly raises a
    # ValueError if the input data has the wrong units
    with pytest.raises(ValueError):
        test_data.pwrd.era5_from_area_bounds(areas)
