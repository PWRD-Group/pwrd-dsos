import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import pandas as pd
    import geopandas as gpd
    from pwrd.huwise import UKPNClient

    ukpn_client = UKPNClient()


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Powerline data

    This notebook is an example of using the powerline data. It "completes" the testing of different types of data. Since we have

    1. Point data (incidents)
    2. Line data (this notebook)
    3. Area data (e.g. primary areas used in this and other notebooks)

    For now I'm (usually) getting data using the "export" functionality on the UKPN website. Need to decide if it is better to use the API.
    """)
    return


@app.cell
def _():
    ukpn_primary_areas = gpd.read_parquet(ukpn_client["ukpn_primary_postcode_area"].file("parquet")).set_geometry("geo_shape")
    power_lines_132kv = gpd.read_parquet(ukpn_client["ukpn-132kv-overhead-lines"].file("parquet")).set_geometry("geo_shape")
    return power_lines_132kv, ukpn_primary_areas


@app.cell
def _(power_lines_132kv, ukpn_primary_areas):
    ax = ukpn_primary_areas.plot(fc="none", lw=0.1)
    power_lines_132kv.plot(ax=ax)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Ok, cool, so we can see the 132kV overhead lines. The next question I suppose is how we can aggregate these by area
    """)
    return


@app.cell
def _(power_lines_132kv, ukpn_primary_areas):
    lines_in_areas = gpd.overlay(power_lines_132kv, ukpn_primary_areas, how="intersection")
    # Make sure we are in a sensible CRS to compute length EPSG:27700 is the OS projection for GB
    lines_in_areas["length"] = lines_in_areas.to_crs("EPSG:27700").length / 1000.  # km

    ax2 = ukpn_primary_areas.plot(fc="none", lw=0.1)
    ukpn_primary_areas.join(lines_in_areas.groupby("primary")["length"].sum().reindex(ukpn_primary_areas.primary), on="primary").plot("length", ax=ax2, legend=True, legend_kwds={"label": "Powerline length [km]"})
    power_lines_132kv.plot(ax=ax2, color="orange", lw=0.5)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    This looks pretty good. We can see that only primary areas that contain powerlines seem to have a colour, which suggests it might be working somewhat as we expect. There isn't an immediate correlation between powerline length and number of faults.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Using all overhead lines

    With the UKPN client, it is pretty easy to get all overhead lines and perform the same analysis. Let's try that.
    """)
    return


@app.cell
def _():
    all_overhead_lines = []
    for name, resource in ukpn_client.items():
        if "overhead" not in name:
            continue
        all_overhead_lines.append(gpd.read_parquet(resource.file("parquet")))
        # Check that the length of the loaded parquet file is the same as we expect from the resource
        assert len(resource) == len(all_overhead_lines[-1])
    all_overhead_lines = pd.concat(all_overhead_lines).set_geometry("geo_shape")
    return (all_overhead_lines,)


@app.cell
def _(all_overhead_lines, ukpn_primary_areas):
    ax3 = ukpn_primary_areas.plot(fc="none", lw=0.1)
    all_overhead_lines.plot(ax=ax3)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    So far more overhead lines when we include more than just the 132kV lines! Let's try and get the lengths as we did before
    """)
    return


@app.cell
def _(all_overhead_lines, ukpn_primary_areas):
    all_lines_in_areas = gpd.overlay(all_overhead_lines, ukpn_primary_areas, how="intersection")
    # Make sure we are in a sensible CRS to compute length EPSG:27700 is the OS projection for GB
    all_lines_in_areas["length"] = all_lines_in_areas.to_crs("EPSG:27700").length / 1000.  # km

    ax4 = ukpn_primary_areas.plot(fc="none", lw=0.1)
    ukpn_primary_areas.join(
        all_lines_in_areas.groupby("primary")["length"].sum().reindex(ukpn_primary_areas.primary),
        on="primary"
    ).plot("length", ax=ax4, legend=True, legend_kwds={"label": "Powerline length [km]"})
    all_overhead_lines.plot(ax=ax4, color="orange", lw=0.1)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Ok, so it takes longer to run (about 45 seconds on my machine) but it seems to work!
    """)
    return


if __name__ == "__main__":
    app.run()
