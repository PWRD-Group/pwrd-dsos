import marimo

__generated_with = "0.22.4"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import matplotlib.pyplot as plt
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

    To aggregate powerline data into areas, we need both the powerline data and the area data.
    """)
    return


@app.cell
def _():
    ukpn_primary_areas = gpd.read_parquet(ukpn_client["ukpn_primary_postcode_area"].file("parquet")).set_geometry("geo_shape")
    power_lines_132kv = gpd.read_parquet(ukpn_client["ukpn-132kv-overhead-lines"].file("parquet")).set_geometry("geo_shape")
    return power_lines_132kv, ukpn_primary_areas


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    We can plot both of these to see where these powerlines are
    """)
    return


@app.cell
def _(power_lines_132kv, ukpn_primary_areas):
    ax = ukpn_primary_areas.plot(fc="none", lw=0.1)
    power_lines_132kv.plot(ax=ax)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    We can see the 132kV overhead lines. The next question is how we can aggregate these by area. To do this we can use the `line_length_in_areas` method that can be accessed via the `pwrd` accessor. This operates on the line data (the powerlines) and takes areas as an argument. The areas must have a named index. The accessor method also needs an explicit CRS, since not every CRS can be used to compute a meaningful length. The accessor method returns an `xarray` that is in the right format to be used with `xvec` for plotting.
    """)
    return


@app.cell
def _(power_lines_132kv, ukpn_primary_areas):
    _, axes = (
        power_lines_132kv
            .pwrd.line_length_in_areas(ukpn_primary_areas.set_index("primary"), crs="EPSG:27700")
            .rename("Powerline length [km]")
            .xvec.plot(figsize=(5, 5), cmap="BuPu", ec="k", lw=0.1)
    )
    power_lines_132kv.plot(ax=axes, color="red", lw=0.5)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    This looks pretty good. We can see that primary areas that contain powerlines have a darker colour.
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
    _, axes_all = (
        all_overhead_lines
            .pwrd.line_length_in_areas(ukpn_primary_areas.set_index("primary"), crs="EPSG:27700")
            .rename("Powerline length [km]")
            .xvec.plot(figsize=(5, 5), cmap="BuPu", ec="k", lw=0.1)
    )
    all_overhead_lines.plot(ax=axes_all, color="red", lw=0.1)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    It takes longer to run (about 45 seconds on my machine) but gives us the powerline length for all overhead powerlines in the UKPN area.
    """)
    return


if __name__ == "__main__":
    app.run()
