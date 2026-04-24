import pytest

import geopandas as gpd
import pandas as pd

import shapely
from shapely.geometry import Polygon


import pwrd  # noqa: F401


WGS_CRS = "EPSG:4326"
# British national grid CRS
BNG_CRS = "EPSG:27700"


@pytest.fixture
def gb_extents():
    # Rough extents of GB
    boxes = [Polygon([(-7, 50), (2, 50), (2, 59), (-7, 59)])]
    index = pd.Index(["GB"], name="area")
    areas = gpd.GeoDataFrame(geometry=boxes, index=index, crs=WGS_CRS)
    return areas.to_crs(BNG_CRS)


@pytest.fixture
def unnamed_areas(gb_extents):
    return gb_extents.reset_index(drop=True)


def test_line_length_in_areas(gb_extents, unnamed_areas):
    # One line in the area, one outside. Only the length of the line
    # inside the area will actually be calculated.
    line_data = shapely.linestrings([[(0, 51), (1, 51)], [(0, 0), (1, 0)]])
    lines = gpd.GeoDataFrame(geometry=line_data, crs=WGS_CRS)
    lines = lines.to_crs(BNG_CRS)

    lengths = lines.pwrd.line_length_in_areas(gb_extents, crs=BNG_CRS)

    # We should have one line that is approx 70km in length
    assert lengths.sel(area="GB").item() > 0

    # Areas must have a named index to work, test that is the case
    with pytest.raises(ValueError):
        lines.pwrd.line_length_in_areas(unnamed_areas, crs=BNG_CRS)


def test_points_in_areas(gb_extents, unnamed_areas):
    # Some points in the area, some outside
    point_data = shapely.points([(-6, 55), (0, 56), (-8, 52), (0, 62)])
    points = gpd.GeoDataFrame(geometry=point_data, crs=WGS_CRS).to_crs(BNG_CRS)

    points_in_areas = points.pwrd.points_in_areas(gb_extents)

    assert points_in_areas.item() == 2

    # Areas must have a named index to work, test that is the case
    with pytest.raises(ValueError):
        points.pwrd.points_in_areas(unnamed_areas)
