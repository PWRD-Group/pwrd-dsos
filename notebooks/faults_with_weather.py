import marimo

__generated_with = "0.22.4"
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
    from pwrd.earthdatahub import LocalCache, era5

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
    from pwrd.huwise import UKPNClient
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
    return client, incidents, uk_ds, ukpn_gsps, ukpn_primary


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
    This logic now all happens inside the `incidents` module, and can be accessed using the `pwrd` accessor.
    ///

    /// Note
    We could look into making the fault data `sparse` since the majority of it is zeros.
    ///
    """)
    return


@app.cell
def _(incidents, ukpn_gsps):
    import pwrd.incidents
    faults_xr = incidents.pwrd.fault_counts(ukpn_gsps, start="start_date_time", end="end_date_time", reference="incident_reference")
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


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Adding powerline data

    In the [resilience paper](https://rmets.onlinelibrary.wiley.com/doi/epdf/10.1002/met.2127), the faults per hour are normalised by overhead line length in each area. We can compute the length of overhead lines by reading in the powerline data and using the `line_length_in_areas` method of the `pwrd` accessor (see the `power_lines.py` notebook for more information about this).
    """)
    return


@app.cell
def _(client):
    all_overhead_lines = []
    for name, resource in client.items():
        if "overhead" not in name:
            continue
        all_overhead_lines.append(gpd.read_parquet(resource.file("parquet")))
        # Check that the length of the loaded parquet file is the same as we expect from the resource
        assert len(resource) == len(all_overhead_lines[-1])
    all_overhead_lines = pd.concat(all_overhead_lines).set_geometry("geo_shape")
    return (all_overhead_lines,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Counter intuitively it is faster to compute the line lengths on smaller areas and then aggregate those results. There is a `groupby` keyword on the `line_length_in_areas` method to do this i.e.

    ```python
    # Don't do
    gsp_overhead_lines = all_overhead_lines.pwrd.line_length_in_areas(ukpn_gsps, crs=27700)
    # Instead do
    gsp_overhead_lines = all_overhead_lines.pwrd.line_length_in_areas(ukpn_primaries, crs=27700, groupby="grid_supply_point")
    ```
    The two methods should return the same results, but the second will be faster.
    """)
    return


@app.cell
def _(all_overhead_lines, ukpn_primary):
    gsp_overhead_lengths = all_overhead_lines.pwrd.line_length_in_areas(
        ukpn_primary.set_index("primary"), crs=27700, groupby="grid_supply_point"
    )
    return (gsp_overhead_lengths,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    This can then be merged with our existing data. We'll keep the DNO coordinate too.
    """)
    return


@app.cell
def _(dno_per_gsp, gsp_overhead_lengths, tester):
    data_with_lengths = xr.merge([tester.assign_coords(dno=dno_per_gsp), gsp_overhead_lengths], compat="equals")
    return (data_with_lengths,)


@app.cell
def _(data_with_lengths):
    data_with_lengths
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    We can see that the `xarray.Dataset` now contains a data variable called length. Let's revisit our plotting function to see what data looks like after normalising by length.
    """)
    return


@app.cell
def _(binning, data_with_lengths):
    def length_plot_helper(name, df, ax, color, statistic="mean", plot_scatter=True):

        def lighten(color, amount=0.5):
            """Lighens the input colour"""
            import matplotlib.colors as mc
            c = mc.to_rgb(color)
            return tuple(1 - (1 - x) * (1 - amount) for x in c)

        df["faults_per_1000km"] = 1000 * df["faults"] / df["length"]

        # If length is 0, then we can get infinite values for
        # faults_per_1000km, which isn't really what we want. We can set those values to NaN
        df["faults_per_1000km"] = df["faults_per_1000km"].where(np.isfinite)

        if plot_scatter:
            df.plot.scatter(x="wind_mag", y="faults_per_1000km", s=4, facecolor=lighten(color), edgecolor="none", ax=ax)
        stat = getattr(df.groupby_bins("wind_mag", bins=binning), statistic)()
        ax.plot(
            stat["wind_mag_bins"].data.mid,
            stat["faults_per_1000km"],
            marker="o", color=color, markeredgecolor="white", label=name
        )

    # Colours from https://coolors.co/palettes/popular/3%20colors
    # (Cherry Ocean Sunset)
    _colors = iter(["#edae49", "#d1495b", "#00798c"])

    _fig, _ax = plt.subplots()
    for _group in data_with_lengths.groupby("dno"):
        length_plot_helper(*_group, ax=_ax, color=next(_colors))

    _ax.set(title="", ylabel="New faults per hour\nper 1000km of overhead line")
    _ax.legend()
    _ax
    return (length_plot_helper,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    This doesn't look as nice as what we had before! There are a few things going on.

    + The DNO lines probably aren't quite what we want here (and perhaps not in the previous plot either). We are first computing the faults / hour / 1000km in each GSP, and then getting the mean of those values (so the lines aren't sum(faults) / sum(lines) for the entire DNO).
    + The banding structure we had previously (due to new faults being a discrete value) is made worse after normalising by line length. If a GSP has almost no overhead lines dividing by a small number makes the resulting value very large. It also gives us large outliers. Let's just not plot each GSP individually.
    + Due to the outliers, using the `median` instead of the mean might make a nicer plot.
    """)
    return


@app.cell
def _(data_with_lengths, length_plot_helper):
    # Colours from https://coolors.co/palettes/popular/3%20colors
    # (Cherry Ocean Sunset)
    _colors = iter(["#edae49", "#d1495b", "#00798c"])

    _fig, _ax = plt.subplots()
    for _group in data_with_lengths.groupby("dno"):
        length_plot_helper(*_group, ax=_ax, color=next(_colors), statistic="median", plot_scatter=False)

    _ax.set(
        title="",
        xlabel="10 metre wind magnitude [ms$^{-1}$]",
        ylabel="New faults per hour\nper 1000km of overhead line",
    )
    _ax.legend()
    _ax
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    But this probably still isn't what we want, due to the way we are computing a statistic across GSPs! The simplest thing to do would be to repeat the whole analysis starting with DNOs rather than GSPs, and then we know we have the right statistics. Let's do that!

    ## Full analysis starting with DNOS
    """)
    return


@app.cell
def _(all_overhead_lines, incidents, ukpn_primary, wind_ds):
    # Dissolve the DNOs from primaries
    ukpn_dnos = ukpn_primary.dissolve("dno")
    # wind data
    mean_wind_dno = wind_ds.xvec.zonal_stats(
        ukpn_dnos.geometry,
        x_coords="longitude",
        y_coords="latitude",
        method="iterate",  # polygons are small compared to pixels
        all_touched=True,
        stats="mean",
        n_jobs=-1,
    )
    # fault data
    faults_dno = incidents.pwrd.fault_counts(ukpn_dnos, start="start_date_time", end="end_date_time", reference="incident_reference")
    # overhead data
    overhead_lengths_dno = all_overhead_lines.pwrd.line_length_in_areas(ukpn_primary.set_index("primary"), crs=27700, groupby="dno")
    return faults_dno, mean_wind_dno, overhead_lengths_dno


@app.cell
def _(faults_dno, mean_wind_dno, overhead_lengths_dno):
    all_dno_data = xr.merge([mean_wind_dno, faults_dno, overhead_lengths_dno], join="outer", compat="equals")
    return (all_dno_data,)


@app.cell
def _(all_dno_data):
    all_dno_data
    return


@app.cell
def _(all_dno_data, length_plot_helper):
    # Colours from https://coolors.co/palettes/popular/3%20colors
    # (Ocean Sunset)
    _colors = iter(["#edae49",  "#00798c"])

    _fig, _ax = plt.subplots()
    for _group in all_dno_data.groupby("dno"):
        if _group[0] == "LPN":
            continue
        length_plot_helper(*_group, ax=_ax, color=next(_colors))

    _ax.set(
        title="",
        xlabel="10 metre wind magnitude [ms$^{-1}$]",
        ylabel="New faults per hour\nper 1000km of overhead line",
    )
    _ax.legend()
    _ax.set(ylim=(0, 10))
    _ax
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    This looks like what we might expect. Note that we've dropped the London data here because there are so few overhead powerlines it doesn't make a huge amount of sense.
    """)
    return


if __name__ == "__main__":
    app.run()
