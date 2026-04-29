from __future__ import annotations
import geopandas as gpd
import pandas as pd

from pwrd.common import xarray_to_xvec


def line_length_in_areas(
    lines: gpd.GeoDataFrame,
    areas: gpd.GeoDataFrame,
    crs: str | int,
) -> pd.Series:
    """Given line data and polygon data, compute aggregated statistic.

    Notes
    -----
    It may be a bit surprising that this method is using a loop over
    geometries. In testing it has been found that this is as
    performant (if not more) for the sorts of problems we are
    typically dealing with. However, this might not be the best
    method if the number of polygons becomes very large.

    Returns
    -------
    A pandas.Series with the same index as areas and the length as
    values
    """
    index_name = areas.index.name
    if index_name is None:
        msg = "areas must be supplied with a named index"
        raise ValueError(msg)

    # Ensure both in crs
    lines = lines.to_crs(crs)
    areas = areas.to_crs(crs)

    return (
        pd.Series(
            {
                key: lines.clip(poly).length.sum() / 1000.0
                for key, poly in areas.geometry.items()
            }
        )
        .rename_axis(index_name)
        .rename("length")
    )


def points_in_areas(points: gpd.GeoDataFrame, areas: gpd.GeoDataFrame) -> pd.Series:
    """Count the number of points in given areas.

    Returns
    -------
    A pandas.Series with the same index as areas and the number of
    points in each area as values
    """

    # Group by the index
    index_name = areas.index.name
    if index_name is None:
        msg = "areas must be supplied with a named index"
        raise ValueError(msg)

    return (
        areas.sjoin(points, predicate="contains", how="left")["index_right"]
        .groupby(index_name)
        .count()
        .rename("count")
    )


class Mixin:
    # To satisfy the type checker
    _df: gpd.GeoDataFrame

    def line_length_in_areas(self, areas, crs, *, groupby=None):
        out = line_length_in_areas(self._df, areas, crs)

        # TODO: Document and test groupby!
        if groupby:
            # Perform a groupby operation on the computed lengths
            out = areas.join(out).groupby(groupby)["length"].sum()
            # Dissolve the areas by the groupby argument
            areas = areas.dissolve(groupby)

        return xarray_to_xvec(out.to_xarray(), areas)

    def points_in_areas(self, areas):
        out = points_in_areas(self._df, areas)
        return xarray_to_xvec(out.to_xarray(), areas)
