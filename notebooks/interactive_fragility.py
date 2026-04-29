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

    wind_ds_cloud = uk_ds[["v10", "u10"]]
    wind_ds = wind_ds_cloud.compute()
    # Other attrs should potentially be defined,
    # but these are the ones used for plotting
    wind_ds["wind_mag"] = np.hypot(wind_ds.u10, wind_ds.v10).assign_attrs(
        standard_name="Wind magnitude", long_name="10 metre wind magnitude", units=r"ms$^{-1}$")

    all_overhead_lines = []
    for name, resource in client.items():
        if "overhead" not in name:
            continue
        all_overhead_lines.append(gpd.read_parquet(resource.file("parquet")))
        # Check that the length of the loaded parquet file is the same as we expect from the resource
        assert len(resource) == len(all_overhead_lines[-1])
    all_overhead_lines = pd.concat(all_overhead_lines).set_geometry("geo_shape")
    return all_overhead_lines, incidents, ukpn_primary, wind_ds


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
    return mean_wind_dno, overhead_lengths_dno, ukpn_dnos


@app.function
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
    binning = np.arange(0, 25, 2.5)

    if plot_scatter:
        df.plot.scatter(x="wind_mag", y="faults_per_1000km", s=4, facecolor=lighten(color), edgecolor="none", ax=ax)
    stat = getattr(df.groupby_bins("wind_mag", bins=binning), statistic)()
    ax.plot(
        stat["wind_mag_bins"].data.mid,
        stat["faults_per_1000km"],
        marker="o", color=color, markeredgecolor="white", label=name
    )


@app.cell
def _(incidents, mean_wind_dno):
    dno_selection = mo.ui.multiselect(mean_wind_dno.dno.values, label="DNOs:", value=["LPN", "EPN", "SPN"])
    cause_selection = mo.ui.multiselect(sorted(list(incidents["cause_code"].unique())), label="Cause codes:", value=["06"])
    range_slider = mo.ui.range_slider(start=-1, stop=60, value=[-1, 20], label="Y-axis limits:")
    return cause_selection, dno_selection, range_slider


@app.cell
def _(cause_selection, dno_selection, range_slider):
    mo.hstack([dno_selection, cause_selection, range_slider], justify="start")
    return


@app.cell
def _(
    cause_selection,
    dno_selection,
    incidents,
    mean_wind_dno,
    overhead_lengths_dno,
    range_slider,
    ukpn_dnos,
):
    # Colours from https://coolors.co/palettes/popular/3%20colors
    # (Ocean Sunset)
    _colors = iter(["#edae49", "#d1495b", "#00798c"])

    inc_sel = incidents["cause_code"].isin(cause_selection.value)
    selected_faults = incidents[inc_sel].pwrd.fault_counts(
        ukpn_dnos, start="start_date_time", end="end_date_time", reference="incident_reference"
    )
    tester = xr.merge([mean_wind_dno, selected_faults, overhead_lengths_dno], join="inner", compat="equals")

    _fig, _ax = plt.subplots()
    for _group in tester.groupby("dno"):
        if _group[0] not in dno_selection.value:
            continue
        length_plot_helper(*_group, ax=_ax, color=next(_colors))

    _ax.set(
        title="",
        xlabel="10 metre wind magnitude [ms$^{-1}$]",
        ylabel="New faults per hour\nper 1000km of overhead line",
    )
    _ax.legend()
    _ax.set(ylim=range_slider.value)
    _ax
    return


if __name__ == "__main__":
    app.run()
