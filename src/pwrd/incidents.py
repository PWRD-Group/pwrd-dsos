"""Helper functions for working with incident/fault data."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import xvec  # noqa: F401

from pwrd.common import xarray_to_xvec

if TYPE_CHECKING:
    import geopandas as gpd
    import xarray as xr


class Mixin:
    """Pandas DataFrame accessor for working with fault/incident data."""

    # To satisfy the type checker
    _df: gpd.GeoDataFrame

    def fault_counts(
        self,
        areas: gpd.GeoDataFrame,
        start: str,
        end: str,
        reference: str,
        freq: str = "h",
    ) -> xr.DataArray:
        """Aggregate faults by area and start time.

        Parameters
        ----------
        areas
            A GeoPandas GeoDataFrame covering regions that you want
            to count faults in.
        start
            The name of the column in the incident dataframe that
            contains the incident start time.
        end
            The name of the column in the incident dataframe that
            contains the incident end time.
        reference
            The name of the column containing the reference code
            of the incident.
        freq
            The time period over which to aggregate new faults,
            specified by a pandas frequency alias e.g. `h` for hourly
            counts and `D` for daily counts. See
            https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
            for a full list of valid frequency aliases.

        Returns
        -------
        xarray.DataArray
            An `xarray.DataArray` with coordinates `geometry` and
            `valid_time`.  The `geometry` coordinates will be the same
            length as the number of input geometries in the `areas`
            parameter, and the `valid_time` coordinate will be from
            the first earliest start time to the latest end time, with
            a frequency determined by the `freq` parameter.

        """
        name = areas.index.name

        # A daterange spanning all times from the start of the
        # earliest incident to the end of the latest incident
        all_times = pd.date_range(
            start=self._df[start].dt.floor(freq).min(),
            end=self._df[end].dt.ceil(freq).max(),
            freq=freq,
            inclusive="both",
        ).tz_localize(None)

        faults_xr = (
            self._df
            # Drop duplicate reference numbers so that we only have
            # the main incident (not "sub-incidents")
            .drop_duplicates(reference)
            # Perform a spatial join with areas so each fault is
            # associated to an area how="right" keeps the geometries
            # from the areas and includes any areas that don't contain
            # incidents
            .sjoin(areas, predicate="within", how="right")
            # Make a new column in the dataframe that is the hour the
            # fault occurred
            .assign(
                time=lambda df: df[start].dt.floor(freq).dt.tz_localize(None),
            )
            # Group by GSP and hour the incident occurred
            # Keep any NA values (areas without faults)
            .groupby([name, "time"], dropna=False)
            # Find the size of each group (the number of faults / hour)
            .size()
            # Rename the resulting data
            .rename("faults")
            # Convert to an xarray.DataArray
            .to_xarray()
            # Reindex so that we have an entry for every hour included
            # in the weather dataset
            .reindex(time=all_times)
            # Rename hour as valid time for consistency with weather data
            .rename(time="valid_time")
            # Fill any NA values with 0 (if they are NA then it means
            # no incidents occurred in that GSP in that hour)
            .fillna(0)
        )

        return xarray_to_xvec(faults_xr, areas)

    def resilience(self, start: str, end: str, customers: str) -> pd.DataFrame:
        """Create a resilience dataframe.

        The resilience dataframe contains the cumulative number of
        customers that have been affected by an outage (outage column)
        and the cumulative number of customers who have had their
        power restored (restoration column). The resilience column is
        the difference between the restoration and outage column
        i.e. the number of customers at that specific time that are
        affected by an outage.

        Parameters
        ----------
        start
            The name of the column that contains incident start times
        end
            The name of the column that contains incident end times
        customers
            The name of the columns that contains the number of customers
            affected by the incident

        Returns
        -------
        pd.DataFrame
            A `pd.DataFrame` with a datetime index and with columns
            outage, restoration, and resilience (which is restoration
            - outage)

        """
        # We group by the start and end times (which will do a sort by
        # default) and then we sum up (eventually cumulatively) how
        # many customers have been restored.  This is under the
        # assumption that customers are affected at the start of fault
        # and restored at the end of it.

        # sum then cumsum because a direct cumsum on a groupby does a
        # cumulative sum per group
        outage = self._df.groupby(start)[customers].sum().cumsum()
        restoration = self._df.groupby(end)[customers].sum().cumsum()

        # ffill is used to front fill NaN values that are present in
        # only one of start or end times, ensuring that there is a
        # value for every entry.  Once front filling is complete NaN
        # values are then set to 0 which sets the first entries of the
        # restoration column when no customers have been restored.
        return (
            pd.DataFrame(
                {"outage": outage, "restoration": restoration},
            )
            .ffill()
            .fillna(0)
            .assign(
                resilience=lambda df: df.restoration - df.outage,
            )
        )
