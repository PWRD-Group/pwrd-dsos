"""Helper functions for working with incident/fault data."""
import numpy as np
import pandas as pd

@pd.api.extensions.register_dataframe_accessor("pwrd")
class PwrdFaultsAccessor:
    def __init__(self, df):
        self._df = df

    def fault_counts(self, areas, start, end, reference, freq="h"):
        """Count the number of faults in areas starting at a given frequency.

        TODO: Do we want to know the number of ongoing faults at a given time.
        """
        name = areas.index.name

        # A daterange spanning all times from the start of the
        # earliest incident to the end of the latest incident
        all_times = pd.date_range(
            start=self._df[start].dt.floor(freq).min(),
            end=self._df[end].dt.ceil(freq).max(),
            freq=freq, inclusive="both",
        ).tz_localize(None)

        faults_xr = (
            self._df
            # Drop duplicate reference numbers so that we only have the main incident (not "sub-incidents")
            .drop_duplicates(reference)
            # Perform a spatial join with areas so each fault is associated to an area
            # how="right" keeps the geometries from the areas 
            # and includes any areas that don't contain incidents
            .sjoin(areas, predicate="within", how="right")
            # Make a new column in the dataframe that is the hour the fault occured
            .assign(
                time=lambda df: df[start].dt.floor(freq).dt.tz_localize(None)
            )
            # Group by GSP and hour the incident occured
            # Keep any NA values (areas without faults)
            .groupby([name, "time"], dropna=False)
            # Find the size of each group (the number of faults / hour)
            .size()
            # Rename the resulting data
            .rename("faults")
            # Convert to an xarray.DataArray
            .to_xarray()
            # Reindex so that we have an entry for every hour included in the weather dataset 
            .reindex(time=all_times)
            # Rename hour as valid time for consistency with weather data
            .rename(time="valid_time")
            # Fill any NA values with 0 
            # (if they are NA then it means no incidents occured in that GSP in that hour)
            .fillna(0)            
        )

        return (
            faults_xr
            # Assign a new coordinate. Note need to convert Geometry array to a numpy object array
            # The .loc call hopefully ensures that the xarray is aligned properly with the geometry
            .assign_coords(geometry=(name, np.array(areas.loc[faults_xr[name]].geometry)))
            # Swap dimensions so that geometry is the dimension
            .swap_dims({name: "geometry"})
            .xvec.set_geom_indexes("geometry", crs=areas.crs)
        )

                  
