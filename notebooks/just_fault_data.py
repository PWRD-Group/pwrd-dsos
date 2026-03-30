import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")

with app.setup:
    import geopandas as gpd
    import marimo as mo
    import pandas as pd

    from pwrd.huwise import UKPNClient


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Fault data

    This notebook looks at data collected from UK Power Networks. The primary area dataset is downloaded directly from the website, while the indident data was downloaded via the API piece-by-piece before being combined into a single parquet file. Let's have a look at what the data shows us.

    /// Note | Primary areas
    In this notebook I am assuming that the primary areas are the atomic unit from which all other definitions of area are made up. This may not be the case. However, if it is then it would be great, as we can easily construct other boundaries from these primary areas e.g. we know which GSP and DNO each primary area is in, so we don't need to download a seperate dataset for each of those!
    ///
    """)
    return


@app.cell
def _():
    client = UKPNClient()
    # Load the primary areas and the incident data
    ukpn_primary_areas = gpd.read_parquet(client["ukpn_primary_postcode_area"].file("parquet")).set_geometry("geo_shape")
    incidents = gpd.read_parquet(client["ukpn-iis"].file("parquet"))
    return incidents, ukpn_primary_areas


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    These files are both GeoDataFrames read into GeoPandas from (geo-)parquet files. To start with, we will plot the outlines of the primary areas and the incidents as red points.
    """)
    return


@app.cell
def _(incidents, ukpn_primary_areas):
    ax = ukpn_primary_areas.plot(fc="none", lw=0.1)
    incidents.plot(ax=ax, marker='o', c="red", alpha=0.2, markersize=0.2)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    It appears that every incident in a specific area is given the same point.
    This gives us a vague overview of where incidents occured but lets make a choropleth map showing the number of incidents in each area.
    There is a bit of magic done here, but the idea is that we do a spatial join of the datasets, using the predicate="within".
    Note that we actually lose a few incidents that don't have a geo-point associated with them.
    We use `groupby("index_right").size()` to get the number of incidents in each of the areas,
    before re-indexing according to the area dataframe,
    filling any areas that don't have incidents with a value of 0.

    We can also select the resolution that we want to perform our aggregations.

    /// attention | Grid sites
    For some reason, some of the primaries don't contain a grid site i.e. they are `null`. It might be possible to resolve this using another dataset. To be investigated!
    ///
    """)
    return


@app.cell
def _():
    resolution_radio = mo.ui.radio(["Primary", "GSP", "Operational Zone", "DNO", "Grid Site"], inline=True, value="Primary")
    resolution_radio
    return (resolution_radio,)


@app.cell
def _(incidents, resolution_radio, ukpn_primary_areas):
    import cartopy.crs as ccrs
    import matplotlib.pyplot as plt 

    match resolution_radio.value:
        case "GSP":
            areas = ukpn_primary_areas.dissolve("grid_supply_point").reset_index()
        case "Operational Zone":
            areas = ukpn_primary_areas.dissolve("operational_zone").reset_index()
        case "DNO":
            areas = ukpn_primary_areas.dissolve("dno").reset_index()
        case "Grid Site":
            areas = ukpn_primary_areas.dissolve("grid_site").reset_index()
        case _:
            areas = ukpn_primary_areas

    fig, ax2 = plt.subplots(subplot_kw=dict(projection=ccrs.PlateCarree()))

    fault_count = (
        incidents.sjoin(areas, predicate="within")
                 .groupby("index_right").size()
                 .reindex(areas.index, fill_value=0)
    )

    areas.assign(fault_count=fault_count).plot(
        "fault_count", legend=True, ax=ax2, legend_kwds={"label": "Incidents"}, vmin=0,
    )
    ax2.coastlines()
    glines = ax2.gridlines(draw_labels=True, color='lightgray', alpha=0.2, x_inline=False)
    glines.right_labels = False
    fig
    return (plt,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    This is a first example of working with the fault data, but it is a bit more complex than I initially thought. Each row in the incidents dataframe seems to correspond to only part of a single incident. While it is more complicated than what is above, it does mean that we can make resilience curves like Figure 7 of [the polcy brief produced by Daniel et al](https://doi.org/10.25500/epapers.bham.00004399).

    ## Resilence curves
    """)
    return


@app.cell
def _(incidents):
    import pwrd.incidents  # For pwrd accessor
    test = incidents.pwrd.resilience("start_date_time", "end_date_time", "customers_restored")
    return (test,)


@app.cell
def _(test):
    test.plot()
    return


@app.cell
def _(plt, test):
    date_range = {
        "Arwen": slice("2021-11-27", "2021-11-28 02"),
        "Isha": slice("2024-01-21", "2024-01-22"),
        "Eunice": slice("2022-02-17", "2022-02-23"),
    }.get("Arwen")

    tmp = test.loc[date_range] - test.loc[date_range].iloc[0]
    tmp.plot()
    plt.gca().fill_between(tmp.index, 0, tmp["resilience"], color="lightgrey")
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    So storm Arwen didn't have nearly as large of an impact in the south east compared with some other DNOs. Looking at [the met office report](https://www.metoffice.gov.uk/binaries/content/assets/metofficegovuk/pdf/weather/learn-about/uk-past-events/interesting/2021/2021_07_storm_arwen.pdf) this perhaps isn't surprising, as red warnings were in North East England and Scotland. Note that this plot is for all three DNOs run by UKPN combined.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Daily customer minutes lost

    Given that each row in the incidents data had a number of customers affected and a start and end time, it should be reasonably straight forward to work out "customer minutes lost".
    """)
    return


@app.cell
def _(incidents):
    # Get "unique" incidents based on the reference code, get earliest start and latest end.
    pd.DataFrame({
        "start": incidents.groupby("incident_reference")["start_date_time"].min(), 
        "end": incidents.groupby("incident_reference")["end_date_time"].max()
    }).assign(
        duration=lambda df: (df["end"] - df["start"])
    ).sort_values("duration", ascending=False)

    # So we can see the longest incident lasted over 231 days!
    # We should consider what data from the original incident data can be joined to this
    # "unique incidents" data. In particular, I'm wondering how we know if the incident is
    # caused by the weather...
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Getting customer minutes lost takes a few stages, depending on exactly what we want. If we want **daily** customer minutes lost, then we need to first split up sub-incidents across day boundaries. By that I mean that if a sub-incidents lasts from 11pm to 2pm, we want to split that into two sub-sub-incidents (for want of a better term) from 11pm-12am and 12am-2pm.
    """)
    return


@app.cell
def _(incidents):
    def make_daily_date_range(row):
        return pd.date_range(
            start=row["start_date_time"].normalize(),
            end=row["end_date_time"].normalize(),
            freq="D",
        )

    # This is slow because of the apply, it might be worth investigating 
    # alternative methods (maybe a case for polars)
    split_incidents = (
        incidents
            .assign(date=incidents.apply(make_daily_date_range, axis=1))
            .explode("date")
            .assign(
                new_start=lambda df: df[["start_date_time", "date"]].max(axis=1),
                new_end=lambda df: df[["end_date_time", "date"]].min(axis=1) + pd.Timedelta(days=1),    
            )
            .assign(
                new_end=lambda df: df[["new_end", "end_date_time"]].min(axis=1)
            )
            .drop(columns=["start_date_time", "end_date_time", "date"])
            .rename(
                columns=dict(new_start="start_date_time", new_end="end_date_time"),
            )
    )
    return (split_incidents,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    We can check that the new "split" incidents, gives us the same total duration as the original incidents for each incident.
    """)
    return


@app.cell
def _(split_incidents):
    pd.DataFrame({
        "start": split_incidents.groupby("incident_reference")["start_date_time"].min(), 
        "end": split_incidents.groupby("incident_reference")["end_date_time"].max()
    }).assign(
        duration=lambda df: (df["end"] - df["start"])
    ).sort_values(
        "duration", ascending=False
    ).head()
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Looks good. Now that we have split incidents we can compute customer minutes lost. I am assuming that customer minutes lost is customers affected multiplied by duration of incident in minutes. We would add this to our original `split_incidents` creation to keep things neat.
    """)
    return


@app.cell
def _(split_incidents):
    split_incidents.assign(
        duration=lambda df: df["end_date_time"] - df["start_date_time"],
        customer_mins_lost=lambda df: df["customers_restored"] * df["duration"],
    )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    So, the whole reason I wanted to split by day is because the [policy document](https://doi.org/10.25500/epapers.bham.00004399) has a Figure (Fig. 4) of daily customer minutes lost. So now that we've split eveything up, and computed `customer_mins_lost` we can groupby day to get this value! At the same time we'll get the total number of unique incidents.
    """)
    return


@app.cell
def _(split_incidents):
    tester = split_incidents.assign(
        duration=lambda df: df["end_date_time"] - df["start_date_time"],
        customer_mins_lost=lambda df: df["customers_restored"] * df["duration"],
    ).groupby(
        # Use floor to keep as datetime
        split_incidents.start_date_time.dt.floor("D")
    ).agg(
        {"incident_reference": "nunique", "customer_mins_lost": "sum"}
    ).assign(
        customer_mins_lost=lambda df: df["customer_mins_lost"].dt.total_seconds().div(60),
    ).rename(
        columns={"incident_reference": "n_incidents"}
    )
    tester
    return (tester,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    With this we can now make a plot similar to that of Figure 4 in the policy document (but without distinguishing by named storms). The very high data points in early 2022 are from [Storms Dudley, Eunice, and Franklin](https://www.metoffice.gov.uk/binaries/content/assets/metofficegovuk/pdf/weather/learn-about/uk-past-events/interesting/2022/2022_02_storms_dudley_eunice_franklin.pdf), with a peak on the 18th of February, the day Eunice hit the UK.

    /// Note | Bubble size
    The policy document says that the size of the bubble shows the number of outages. I am unsure whether this is new outages on each day or continuing outages i.e. if an outage starts on day 1 but continues to day 5 it will be counted in my plot 5 times.
    """)
    return


@app.cell
def _(plt, tester):
    def plot_customer_mins_lost(df, ax=None, color="xkcd:teal"):

        from matplotlib.ticker import EngFormatter
        from matplotlib.dates import YearLocator

        ax = ax or plt.gca()

        plt.scatter(x=df.index, y=df.customer_mins_lost, s=df.n_incidents, ec="k", color=color)
        ax.yaxis.set_major_formatter(EngFormatter())
        ax.xaxis.set_major_locator(YearLocator())
        ax.set(
            xlabel="Year", 
            ylabel="Daily Customer Minutes Lost (CML)", 
            ylim=(None, ax.get_ylim()[1] * 1.1),
        )
        return ax

    plot_customer_mins_lost(tester, color="xkcd:teal blue")
    return


if __name__ == "__main__":
    app.run()
