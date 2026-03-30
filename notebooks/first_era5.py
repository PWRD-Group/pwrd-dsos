import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")

with app.setup:
    import geopandas as gpd
    import xarray as xr
    import xvec

    # For markdown
    import marimo as mo

    from pwrd.huwise import UKPNClient

    ukpn_client = UKPNClient()


@app.cell
def _():
    mo.md(r"""
    ## First look at ERA5 data

    This is a first look at getting data from ERA5 for future analysis. We get the data via from the [Earth Data Hub](https://earthdatahub.destine.eu/collections/era5) which can be obtained in the [Zarr](https://zarr.dev) format. This means we can do various operations on the data before we do any downloads, stopping us (hopefully) from maxing out of API limits.

    To test aggregating the data by area, GSP data obtained from UKPN, using the `huwise` module. We can get a shortcut to the ERA5 data from our `earthdatahub.era5` module.
    """)
    return


@app.cell
def _():
    from pwrd.earthdatahub.era5 import land_hourly_store
    earth_ds = xr.open_dataset(land_hourly_store, chunks={}, engine="zarr")
    earth_ds.longitude.units
    return (earth_ds,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Note that the ERA5 data from the `earthdatahub` has longitude in units of "degrees east" (0º -> 360º), typically we want our units to be -180º to 180º. We will convert this later.

    We are going to work with data just inside the region covered by UK power networks. To start with, we will load the primary areas of UKPN.
    """)
    return


@app.cell
def _():
    areas = gpd.read_parquet(ukpn_client["ukpn_primary_postcode_area"].file("parquet")).set_geometry("geo_shape")
    return (areas,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Because selecting data by area is a common operation, a helper function exists inside the `earthdatahub` sub-module. It can be accessed through an [xarray accessor](https://docs.xarray.dev/en/stable/internals/extending-xarray.html) named `pwrd`! The accessor also has a method to convert the longitude units from 0º->360º to -180º->180º named `convert_longitude`.
    """)
    return


@app.cell
def _(areas, earth_ds):
    uk_ds = earth_ds.pwrd.era5_from_area_bounds(areas)
    uk_ds = uk_ds.pwrd.convert_longitude()
    return (uk_ds,)


@app.cell
def _():
    # The repr (but not the html_repr) gives us information about the size of the dataset
    # Try not to call `compute` on anything where the data wont fit into memory
    # repr(uk_ds.sel(valid_time="2021").tp)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Select a year to view the per month rainfall:
    """)
    return


@app.cell
def _():
    year_picker = mo.ui.dropdown(range(1950, 2026), value=2021)
    year_picker
    return (year_picker,)


@app.cell
def _(uk_ds, year_picker):
    uk_tp = uk_ds.sel(valid_time=str(year_picker.value)).tp.compute()
    return (uk_tp,)


@app.cell
def _(uk_tp):
    # To get the monthly rainfall we get the final value of `tp` per day (`tp` is cumulative) and sum up over the month
    monthly_rainfall = uk_tp.resample(valid_time="1D").last().groupby("valid_time.month").sum()
    return (monthly_rainfall,)


@app.cell
def _(areas, monthly_rainfall):
    # Use `xvec` to
    tp_agg = (
        monthly_rainfall
        .xvec.zonal_stats(
            areas.geometry,
            x_coords="longitude",
            y_coords="latitude",
            method="iterate",  # polygons are small compared to pixels
            all_touched=True,
            stats="max",
            n_jobs=-1,
        )
    )
    return (tp_agg,)


@app.cell
def _(tp_agg):
    import cartopy.crs as ccrs

    fig_tp_agg, ax_tp_agg = tp_agg.xvec.plot(
        col="month",
        col_wrap=4,
        cmap="Blues",
        subplot_kws={"projection": ccrs.PlateCarree()},
    )

    for ax in ax_tp_agg.ravel():
        ax.coastlines()
        # ax.gridlines(draw_labels=True)
    return (fig_tp_agg,)


@app.cell
def _(fig_tp_agg):
    fig_tp_agg
    return


if __name__ == "__main__":
    app.run()
