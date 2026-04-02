from __future__ import annotations
from typing import TYPE_CHECKING
import geopandas as gpd

if TYPE_CHECKING:
    import pandas as pd


def line_lengths_by_area(
        lines: gpd.GeoDataFrame,
        areas: gpd.GeoDataFrame,
        crs: str | int
) -> pd.Series:
    """Given line data and polygon data, compute aggregated statistic.


    Returns
    -------
    A pandas.Series with the same index as areas and the length as
    values
    """
    # how="intersection" is the default

    lines_in_areas = lines.overlay(
        areas.reset_index()
        # ty gets confused about what happens after reset_index so
        # explicitly set geometry
        .set_geometry(areas.geometry.name)
    )
    # By default we'll convert lengths to km, but this might be CRS
    # dependent. There will be a warning issued if we are calling
    # length on a CRS with units of degrees
    lines_in_areas["length"] = lines_in_areas.to_crs(crs).length / 1000.

    # Group by the index
    index_name = areas.index.name
    if index_name is None:
        msg = "areas must be supplied with a named index"
        raise ValueError(msg)
    total_line_length = lines_in_areas.groupby(index_name)["length"].sum()
    # Return total lengths, ensuring that all areas have an entry,
    # setting areas without lines to 0
    return total_line_length.reindex_like(areas).fillna(0)
