import geopandas as gpd
from pandas.api.extensions import register_dataframe_accessor

from pwrd import grouping, incidents


@register_dataframe_accessor("pwrd")
class PwrdDataFrameAccessor(
    grouping.Mixin,
    incidents.Mixin,
):
    """The main point of access for operations on dataframes.

    This class is constructed of 'Mixin' classes that are defined in
    various submodules.
    """

    def __init__(self, df: gpd.GeoDataFrame) -> None:
        self._df = df
