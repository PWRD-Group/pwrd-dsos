import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")

with app.setup:
    import geopandas as gpd
    import marimo as mo
    import pandas as pd
    from pwrd.huwise import UKPNClient

    client = UKPNClient()


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Faults per kilometer of powerline (132 kV)

    In this notebook I'm going to attempt to combine different data sources together. As a first test, I am going to get all the incident data and make a plot of incidents per kilometer of powerline. The incident data contains sub-incidents (parts of incidents so that the progress of each incident can be studied), for this test, we just want unique incidents (although the conclusions don't seem to change much).
    """)
    return


@app.cell
def _():
    ukpn_primary_areas = gpd.read_parquet(client["ukpn_primary_postcode_area"].file("parquet")).set_geometry("geo_shape")
    power_lines = gpd.read_parquet(client["ukpn-132kv-overhead-lines"].file("parquet")).set_geometry("geo_shape")
    incidents = gpd.read_parquet(client["ukpn-iis"].file("parquet"))
    return incidents, power_lines, ukpn_primary_areas


@app.cell
def _():
    # Compute faults per area, use sjoin to find faults in each sub-area
    def points_in_areas(points, areas):
        return (    
            points
                # Argument needs to be GeoDataFrame
                .sjoin(areas.geometry.to_frame(), predicate="within")
                # Group by area index so we can count the number of faults in each area
                .groupby(areas.index.name).size()
                # Be sure to reindex because if there are unrepresented areas in the groupby then they will be dropped
                .reindex(areas.index, fill_value=0)
        )


    def length_in_areas(lines, areas):
        return (
            lines
                # Overlay breaks up lines at area boundaries
                .overlay(areas.reset_index(), how="intersection")
                # Need to ensure we are in a CRS with a meaningful unit
                .to_crs("EPSG:27700")
                .assign(x=lambda df: df.length / 1000)
                # We want to recombine into areas
                .groupby(areas.index.name)["x"]
                .sum()
                # Be sure to reindex because if there are unrepresented areas in the groupby then they will be dropped
                .reindex(areas.index, fill_value=0)
        )


    def plot_faults_per_powerline_length(areas, points, lines):
        new_df = pd.DataFrame({
            "Faults": points_in_areas(points, areas), 
            "Length of Powerlines [km]": length_in_areas(lines, areas)
        })

        # Print the correlation between the two 
        print(new_df.corr())
        return new_df.plot.scatter("Length of Powerlines [km]", "Faults")

    return (plot_faults_per_powerline_length,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Primary areas
    """)
    return


@app.cell
def _(
    incidents,
    plot_faults_per_powerline_length,
    power_lines,
    ukpn_primary_areas,
):
    # Define areas so we can change how we aggregate the data easily
    plot_faults_per_powerline_length(
        ukpn_primary_areas.set_index("primary"), 
        incidents.drop_duplicates("incident_reference"), 
        power_lines
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Here we can see a plot of incidents in each area versus the length of powerlines in each area. There is a 11% correlation between incidents and length of powerlines.

    ## Grid Supply Points
    """)
    return


@app.cell
def _(
    incidents,
    plot_faults_per_powerline_length,
    power_lines,
    ukpn_primary_areas,
):
    plot_faults_per_powerline_length(
        ukpn_primary_areas.dissolve("grid_supply_point"), 
        incidents.drop_duplicates("incident_reference"), 
        power_lines
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Ah! After combining primary areas into grid supply points we see a much stronger correlation - 87%! Perhaps this is just because GSPs with more powerlines are larger, and maybe incidents are just relative to GSP size?
    """)
    return


if __name__ == "__main__":
    app.run()
