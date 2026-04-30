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
    # Fragility curves

    This notebook builds on the `faults_with_weather` notebook, and can be considered a direct follow on.
    """)
    return


@app.cell
def _():
    from pwrd.earthdatahub import LocalCache, era5
    from pwrd.huwise import UKPNClient

    # We are going to cache files in the current directory
    local_cache = LocalCache()
    cached_store = local_cache.create_cache_store(era5.land_hourly_store)

    # Open with xarray
    earth_ds = xr.open_dataset(cached_store, engine="zarr", chunks={}, mode="a")

    client = UKPNClient()
    iis = client["ukpn-iis"]
    incidents = gpd.read_parquet(iis.file("parquet"))

    ukpn_primary = gpd.read_parquet(client["ukpn_primary_postcode_area"].file("parquet")).set_geometry("geo_shape")
    return client, earth_ds, incidents, ukpn_primary


@app.cell
def _(earth_ds, ukpn_primary):
    # We select the uk_ds (badly named, as it is just the UKPN area) from the ERA5 data
    uk_ds = (
        earth_ds
            .pwrd.era5_from_area_bounds(ukpn_primary)
            # ERA5 has longitudes from 0 -> 360, convert to -180 -> 180
            .pwrd.convert_longitude()
            # Select just the years from 2021 to 2024
            .sel(valid_time=slice("2021", "2024"))
    )
    return (uk_ds,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Select ERA5 variables

    Select which ERA5 variables are downloaded and made available. Note that the zonal statistics are computed using the mean and this might not make sense for every variable.
    """)
    return


@app.cell
def _(uk_ds):
    wind_variables = {"v10", "u10"}

    all_varaibles = sorted(set(uk_ds.data_vars) - wind_variables)

    # We are going to limit max selections to 5 but this is
    # somewhat arbitray and just to avoid accidentally downloading too much data
    _label  = "Select ERA5 variables (v10 and u10 are always included):"

    era5_varaible_selector = mo.ui.multiselect(options=all_varaibles, max_selections=5, label=_label)
    era5_varaible_selector
    return era5_varaible_selector, wind_variables


@app.cell
def _(era5_varaible_selector, wind_variables):
    selected = era5_varaible_selector.value + list(wind_variables)
    return (selected,)


@app.cell
def _(selected, uk_ds):
    # Wind are always included because we do some calculations with them below.
    # This could definitely be fixed in the longer term but for now we'll leave as is.


    weather_ds_cloud = uk_ds[selected]
    weather_ds = weather_ds_cloud.compute()
    # Other attrs should potentially be defined,
    # but these are the ones used for plotting
    weather_ds["wind_mag"] = np.hypot(weather_ds.u10, weather_ds.v10).assign_attrs(
        standard_name="Wind magnitude", long_name="10 metre wind magnitude", units=r"ms$^{-1}$")
    return (weather_ds,)


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


@app.cell
def _(ukpn_primary, weather_ds):
    # Dissolve the DNOs from primaries
    ukpn_dnos = ukpn_primary.dissolve("dno")
    # wind data
    mean_weather_dno = weather_ds.xvec.zonal_stats(
        ukpn_dnos.geometry,
        x_coords="longitude",
        y_coords="latitude",
        method="iterate",  # polygons are small compared to pixels
        all_touched=True,
        stats="mean",
        n_jobs=-1,
    )
    return mean_weather_dno, ukpn_dnos


@app.cell
def _(incidents, ukpn_dnos):
    # fault data
    faults_dno = incidents.pwrd.fault_counts(ukpn_dnos, start="start_date_time", end="end_date_time", reference="incident_reference")
    return


@app.cell
def _(all_overhead_lines, ukpn_primary):
    # overhead data
    overhead_lengths_dno = all_overhead_lines.pwrd.line_length_in_areas(ukpn_primary.set_index("primary"), crs=27700, groupby="dno")
    return (overhead_lengths_dno,)


@app.function
def length_plot_helper(name, df, ax, color, variable="wind_mag", statistic="mean", binning=np.arange(0, 25, 2.5), plot_scatter=True):

    def lighten(color, amount=0.5):
        """Lighens the input colour"""
        import matplotlib.colors as mc
        c = mc.to_rgb(color)
        return tuple(1 - (1 - x) * (1 - amount) for x in c)

    df["faults_per_1000km"] = 1000 * df["faults"] / df["length"]

    # If length is 0, then we can get infinite values for
    # faults_per_1000km, which isn't really what we want. We can set those values to NaN
    df["faults_per_1000km"] = df["faults_per_1000km"].where(np.isfinite)

    range = (df[variable].min().item(), df[variable].max().item())

    if plot_scatter:
        df.plot.scatter(x=variable, y="faults_per_1000km", s=4, facecolor=lighten(color), edgecolor="none", ax=ax)
    stat = getattr(df.groupby_bins(variable, bins=binning), statistic)()
    ax.plot(
        stat[f"{variable}_bins"].data.mid,
        stat["faults_per_1000km"],
        marker="o", color=color, markeredgecolor="white", label=name
    )


@app.cell
def _(incidents, mean_weather_dno):
    dno_selection = mo.ui.multiselect(mean_weather_dno.dno.values, label="DNOs:", value=["LPN", "EPN", "SPN"])
    cause_selection = mo.ui.multiselect(sorted(list(incidents["cause_code"].unique())), label="Cause codes:", value=["06"])
    variable_selection = mo.ui.dropdown(options=mean_weather_dno.data_vars, value="wind_mag", allow_select_none=False)
    range_slider = mo.ui.range_slider(start=-1, stop=60, value=[-1, 20], label="Y-axis limits:")
    return cause_selection, dno_selection, range_slider, variable_selection


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Choose variable to analyse
    """)
    return


@app.cell
def _(cause_selection, dno_selection, range_slider, variable_selection):
    mo.hstack([variable_selection, dno_selection, cause_selection, range_slider], justify="start")
    return


@app.cell
def _(
    cause_selection,
    dno_selection,
    incidents,
    mean_weather_dno,
    overhead_lengths_dno,
    range_slider,
    ukpn_dnos,
    variable_selection,
):
    # Colours from https://coolors.co/palettes/popular/3%20colors
    # (Ocean Sunset)
    _colors = iter(["#edae49", "#d1495b", "#00798c"])

    inc_sel = incidents["cause_code"].isin(cause_selection.value)
    selected_faults = incidents[inc_sel].pwrd.fault_counts(
        ukpn_dnos, start="start_date_time", end="end_date_time", reference="incident_reference"
    )
    tester = xr.merge([mean_weather_dno, selected_faults, overhead_lengths_dno], join="inner", compat="equals")

    variable = variable_selection.value

    _min = tester[variable].min().item()
    _max = tester[variable].max().item()

    _fig, _ax = plt.subplots()
    for _name, df in tester.groupby("dno"):
        if _name not in dno_selection.value:
            continue
        length_plot_helper(
            _name, df,
            ax=_ax,
            color=next(_colors),
            variable=variable,
            binning=np.linspace(_min, _max, 10)
        )


    xname = tester[variable].attrs.get("long_name")
    xunits = tester[variable].attrs.get("units")

    xlabel = f"{xname} [{xunits}]" if xunits is not None else xname

    _ax.set(
        title="",
        xlabel=xlabel,
        ylabel="New faults per hour\nper 1000km of overhead line",
    )
    _ax.legend()
    _ax.set(ylim=range_slider.value)
    _ax
    return


if __name__ == "__main__":
    app.run()
