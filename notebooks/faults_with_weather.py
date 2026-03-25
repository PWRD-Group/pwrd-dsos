import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import geopandas as gpd
    import pandas as pd
    import xarray as xr
    import xvec  # noqa
    import numpy as np
    import matplotlib.pyplot as plt


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Combining weather data with fault data

    The aim of this notebook is to investigate the combination of weather and fault data. This will likely require a bit of everything `geopandas`, `xarray`, `xvec`, etc...

    Along the way I'll try and identify where the pain points are and what we can spin out into a shared module.

    Loading the dataset certainly is a candidate for a shared module, especially the part that is adding the cached storage.
    """)
    return


@app.cell
def _():
    from donalddl_pwrd.earthdatahub import LocalCache, era5

    # We are going to cache files in the current directory
    local_cache = LocalCache()
    cached_store = local_cache.create_cache_store(era5.land_hourly_store)

    # Open with xarray
    earth_ds = xr.open_dataset(cached_store, engine="zarr", chunks={}, mode="a")
    return (earth_ds,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    When we load the dataset it would also be good to have a way to filter it by an area, given by some other data. So in this example it would be good to select the weather data directly from the incident data.
    """)
    return


@app.cell
def _(earth_ds):
    from donalddl_pwrd.huwise import UKPNClient
    client = UKPNClient()
    iis = client["ukpn-iis"]
    incidents = gpd.read_parquet(iis.file("parquet"))
    # We check that the number of rows in the the incident dataframe
    # is what we expect from the API
    assert len(iis) == len(incidents)

    # The GSP dataset has some duplicates and overlaps which make it a bit tricky to work with.
    # It seems that using the primarys and disolving them down seems to work well
    ukpn_primary = gpd.read_parquet(client["ukpn_primary_postcode_area"].file("parquet")).set_geometry("geo_shape")
    ukpn_gsps = ukpn_primary.dissolve("grid_supply_point")

    # We select the uk_ds (badly named, as it is just the UKPN area) from the ERA5 data
    uk_ds = (
        earth_ds
            .pwrd.era5_from_area_bounds(ukpn_gsps)
            # ERA5 has longitudes from 0 -> 360, convert to -180 -> 180
            .pwrd.convert_longitude()
            # Select just the years from 2021 to 2024
            .sel(valid_time=slice("2021", "2024"))
    )
    uk_ds
    return incidents, uk_ds, ukpn_gsps


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    To start with let's look at wind (unfortunatly the `earthdatahub` version of ERA5 doesn't have gusts). It is always worth checking how many bytes our selected data is before calling compute. We'll call the variable `wind_ds_cloud` to signify it isn't local yet (although it may be stored on disk in a local cache).
    """)
    return


@app.cell
def _(uk_ds):
    wind_ds_cloud = uk_ds[["v10", "u10"]]
    print(f"Wind data is {wind_ds_cloud.nbytes / 10**6} MB")
    return (wind_ds_cloud,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    So the wind data we've selected is a little under 180 MB, so it should be fine to read that into memory. We'll also compute the magnitude of the wind using `np.hypot`.
    """)
    return


@app.cell
def _(wind_ds_cloud):
    wind_ds = wind_ds_cloud.compute()
    # Other attrs should potentially be defined,
    # but these are the ones used for plotting
    wind_ds["wind_mag"] = np.hypot(wind_ds.u10, wind_ds.v10).assign_attrs(
        standard_name="Wind magnitude", long_name="10 metre wind magnitude", units=r"ms$^{-1}$")
    return (wind_ds,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Computing zonal statistics

    From conversations with Daniel, I think that the main goal will be to do things on an "area" basis i.e. looks at max wind gust per hours per GSP or similar. Exactly how data is grouped together is something to be decided, but we are using `xvec` to compute the statistics on a zonal level. This returns an `xarray.DataArray` with a geometry as one dimension. By setting the index of the gsp `GeoDataFrame` we will get the GSP name in the resulting output.
    """)
    return


@app.cell
def _(ukpn_gsps, wind_ds):
    mean_wind = wind_ds.xvec.zonal_stats(
        ukpn_gsps.geometry,
        x_coords="longitude",
        y_coords="latitude",
        method="iterate",  # polygons are small compared to pixels
        all_touched=True,
        stats="mean",
        n_jobs=-1,
    )
    mean_wind
    return (mean_wind,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Since the wind data is hourly we get an `xarray.Dataset` with dimensions `number of GSPs x number of hours in weather dataset`. To make some plots we'll want to reduce this further, e.g. by selecting a date range and a single component of the wind, then taking the maximum wind value on each of those days in each GSP. Use `xvec` for plotting. Note the windiest day was the 18th of Feburary 2022, which was when Storm Eunice hit.
    """)
    return


@app.cell
def _(mean_wind):
    (
        mean_wind
            # Select the data of the storm
            .sel(valid_time=slice("2022-02-15", "2022-02-22"))
            # Group by the date and take the maximum (so we'll get a plot per day)
            .groupby("valid_time.date").max()
            # Select the wind magnitude and plot using `xvec`
            ["wind_mag"].xvec.plot(col="date", col_wrap=4)
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Counts days with some condition

    Another thing we might want to do is count how many days are certain thing happened. For example, we might want to count the number of days in our dataset when then maximum wind was > 10 m/s. We can do this by resampling the data and taking the maximum per day, then summing across the time dimension.
    """)
    return


@app.cell
def _(mean_wind):
    # Want to get the count of days where the wind was greater than a certain value.
    # Let's get the number of days where the wind magnitude is
    # greater than 10m/s
    # 1. Resample to days (taking the maximum value)
    (
        mean_wind
            .resample(valid_time="1D")
            .max()
    # 2. Find values > 10
            > 10
    ).sum(dim="valid_time")["wind_mag"].xvec.plot()
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    So the Margate area experiences the most days where the maximum wind is greater than 10 m/s.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Creating an `xarray.DataArray` for the incident data

    In order to combine the incident data with out newly created wind dataset, we want to convert our `incidents` `GeoDataFrame` into an `xarray`. At the same time we'll perform an `sjoin` to convert from a 2D point where the incident occured, to a polygon representing the GSP where the incident occured (which is the same level we now have the wind data). We are also going to `floor` the time that the incidents occured to the hour so we have the same time resolution as the weather data.

    /// Note
    We could look into making the fault data `sparse` since the majority of it is zeros.
    ///
    """)
    return


@app.cell
def _(incidents, ukpn_gsps):
    all_hours = pd.date_range(
        start=incidents["start_date_time"].dt.floor("h").min(),
        end=incidents["start_date_time"].dt.ceil("h").max(),
        freq="h", inclusive="both",
    ).tz_localize(None)

    areas = ukpn_gsps.geometry.to_frame()

    faults_xr = (
        incidents
            # Drop duplicate reference numbers so that we only have the main incident (not "sub-incidents")
            .drop_duplicates("incident_reference")
            # Perform a spatial join with GSPs so each fault is associated to a GSP
            # how="right" keeps the geometries from the areas
            # and includes any areas that don't contain incidents
            .sjoin(areas, predicate="within", how="right")
            # Make a new column in the dataframe that is the hour the fault occured
            .assign(
                hour=lambda df: df.start_date_time.dt.floor('h').dt.tz_localize(None)
            )
            # Group by GSP and hour the incident occured
            # Keep any NA values (areas without faults)
            .groupby([areas.index.name, "hour"], dropna=False)
            # Find the size of each group (the number of faults / hour)
            .size()
            # Rename the resulting data
            .rename("faults")
            # Convert to an xarray.DataArray
            .to_xarray()
            # Reindex so that we have an entry for every hour included in the weather dataset
            .reindex(hour=all_hours)
            # Rename hour as valid time for consistency with weather data
            .rename(hour="valid_time")
            # Fill any NA values with 0
            # (if they are NA then it means no incidents occured in that GSP in that hour)
            .fillna(0)
            # Lower the data precision for storage
            .astype("int16")
    )
    # Now convert this so that is is `xvec` like
    faults_xr = (
        faults_xr
            # Assign a new coordinate. Note need to convert Geometry array to a numpy object array
            # The .loc call hopefully ensures that the xarray is aligned properly with the geometry
            .assign_coords(geometry=("grid_supply_point", np.array(areas.loc[faults_xr["grid_supply_point"]].geometry)))
            # Swap dimensions so that geometry is the dimension
            .swap_dims(grid_supply_point="geometry")
            .xvec.set_geom_indexes("geometry", crs=areas.crs)
    )
    faults_xr
    return (faults_xr,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Combining the weather and fault data into a single `xarray.Dataset`

    Now that we have an `xarray.DataArray` of our incident data and an `xarray.Dataset` of our weather we merge them together into a single `xarray.DataSet`.

    /// Note
    There is potentially some tidying to be done in the creation of the two `DataArray` and the merging of them together into the final `DataSet`.
    ///
    """)
    return


@app.cell
def _(faults_xr, mean_wind):
    tester = xr.merge([faults_xr, mean_wind], join="inner", compat="equals")
    tester
    return (tester,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""

    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Let's make a couple of plots to see if the data looks reasonable.
    """)
    return


@app.cell
def _(tester):
    tester.sel(valid_time="2022-02-18 12")["faults"].xvec.plot()
    return


@app.cell
def _(tester):
    tester.sel(valid_time="2022-02-18 12")["wind_mag"].xvec.plot()
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Mean failures per hours versus mean wind speed

    Let's plot a scatter plot of faults per hour versus wind speed. We'll plot every hours faults as grey points and then compute the mean faults per hour binned in wind speed (plotted as orange dots). `searborn` could make a nice plot of this for us too. Here we are overlooking standard deviation of the points and sampling statistics, but we see a nice trend in the faults increasing as the wind speed increases!

    In the [paper Daniel sent me](https://rmets.onlinelibrary.wiley.com/doi/epdf/10.1002/met.2127) they also normalise by (1000) km of overhead line, so that might be the thing to look at next!
    """)
    return


@app.cell
def _(tester):
    # Bins from [0, 25) (not including 25) with spacing of 2.5
    binning = np.arange(0, 25, 2.5)
    fig, ax = plt.subplots()
    tester.plot.scatter(x="wind_mag", y="faults", s=4, facecolor="grey", edgecolor="none", ax=ax)

    means = tester.groupby_bins("wind_mag", bins=binning).mean()

    ax.plot(means["wind_mag_bins"].data.mid, means["faults"], marker="o", color="orange", markeredgecolor="white")
    ax.set(title="", ylabel="New faults per hour")
    return (binning,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    We can go a bit further and break this down into smaller areas. Doing it for something like GSP would get a bit messy, since there are a lot of them, but doing it by DNO should look ok. We can add the DNOs to our `xarray` as an additional coordinate like so:
    """)
    return


@app.cell
def _(tester, ukpn_gsps):
    dno_per_gsp = tester.grid_supply_point.to_index().map(ukpn_gsps["dno"])
    tester.assign_coords(dno=dno_per_gsp)
    return (dno_per_gsp,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    We can combine this with a `groupby("dno")` to loop over DNOs and plot each of them.
    """)
    return


@app.cell
def _(binning, dno_per_gsp, tester):
    def plot_helper(name, df, ax, color):

        def lighten(color, amount=0.5):
            """Lighens the input colour"""
            import matplotlib.colors as mc
            c = mc.to_rgb(color)
            return tuple(1 - (1 - x) * (1 - amount) for x in c)

        df.plot.scatter(x="wind_mag", y="faults", s=4, facecolor=lighten(color), edgecolor="none", ax=ax)
        means = df.groupby_bins("wind_mag", bins=binning).mean()
        ax.plot(
            means["wind_mag_bins"].data.mid,
            means["faults"],
            marker="o", color=color, markeredgecolor="white", label=name
        )

    # Colours from https://coolors.co/palettes/popular/3%20colors
    # (Cherry Ocean Sunset)
    colors = iter(["#edae49", "#d1495b", "#00798c"])

    dno_fig, dno_ax = plt.subplots()
    for group in tester.assign_coords(dno=dno_per_gsp).groupby("dno"):
        plot_helper(*group, ax=dno_ax, color=next(colors))

    dno_ax.set(title="", ylabel="New faults per hour")
    dno_ax.legend()
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    We can see that there is no relation in London, but we see similar trends in the East and South East England DNOs.
    """)
    return


if __name__ == "__main__":
    app.run()
