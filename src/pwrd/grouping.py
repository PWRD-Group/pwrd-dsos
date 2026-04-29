from __future__ import annotations
import geopandas as gpd
import pandas as pd

from pwrd.common import xarray_to_xvec


def line_length_in_areas(
    lines: gpd.GeoDataFrame,
    areas: gpd.GeoDataFrame,
    crs: str | int,
) -> pd.Series:
    """Calculate the total line length in each area.

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
        """Calculate line lengths in areas.

        Given lines and areas, calculate the total line length in each
        area.

        Parameters
        ----------
        areas:
            A geopandas GeoDataFrame of areas to perform the aggregation
            with
        crs:
            The CRS to perform the aggregation. Important in order to
            get the right units.
        groupby:
            A column name in areas to groupby after calculating line lengths.
            It is generally faster to calculate line lengths with small areas
            and then sum them to get the line lengths in large areas. For
            example it may be faster to pass primary areas as the `areas`
            argument and then `groupby="dno"` to get the line lengths per dno
            rather than passing the DNOs as the `areas` argument.

        Returns
        -------
        An `xarray.DataArray` in the format that `xvec` uses i.e. has a
        `geometry` dimension.
        """
        out = line_length_in_areas(self._df, areas, crs)

        if groupby:
            # Perform a groupby operation on the computed lengths
            out = areas.join(out).groupby(groupby)["length"].sum()
            # Dissolve the areas by the groupby argument
            areas = areas.dissolve(groupby)

        return xarray_to_xvec(out.to_xarray(), areas)

    def points_in_areas(self, areas):
        out = points_in_areas(self._df, areas)
        return xarray_to_xvec(out.to_xarray(), areas)
