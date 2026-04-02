import pandas as pd
from pandas.api.extensions import register_dataframe_accessor

from pwrd import grouping, incidents


@register_dataframe_accessor("pwrd")
class PwrdDataFrameAccessor(
    grouping.Mixin,
    incidents.Mixin,
):
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df
