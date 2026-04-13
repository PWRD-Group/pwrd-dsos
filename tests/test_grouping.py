import pytest

import geopandas as gpd
import pandas as pd

from shapely.geometry import LineString, Polygon

import pwrd  # noqa: F401

def test_line_length_in_areas():

    wgs = "EPSG:4326"
    # British national grid CRS
    bng_crs = "EPSG:27700"
    
    # Rough extents of GB
    boxes = [Polygon([(-7, 50), (2, 50), (2, 59), (-7, 59)])]
    index = pd.Index(["GB"], name="area")
    areas = gpd.GeoDataFrame(geometry=boxes, index=index, crs=wgs)
    areas = areas.to_crs(bng_crs)

    # One line in the area, one outside. Only the length of the line
    # inside the area will actually be calculated.
    line_data = [
        LineString([(0, 51), (1, 51)]),
        LineString([(0, 0), (1, 0)]),
    ]
    lines = gpd.GeoDataFrame(geometry=line_data, crs=wgs)
    lines = lines.to_crs(bng_crs)
    
    lengths = lines.pwrd.line_length_in_areas(areas, crs=bng_crs)

    # We should have one line that is approx 70km in length
    assert lengths.sel(area="GB").item() > 0

    # Areas must have a named index to work, test that is the case
    unnamed_areas = gpd.GeoDataFrame(geometry=boxes, crs=wgs).to_crs(bng_crs)

    with pytest.raises(ValueError):
        lines.pwrd.line_length_in_areas(unnamed_areas, crs=bng_crs)

    

