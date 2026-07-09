from io import StringIO

import pytest
import geopandas as gpd
import numpy as np
import pandas as pd

from shapely.geometry import Point, Polygon

import pwrd.incidents  # noqa: F401


def generate_incidents(n=20):

    # Random start times over a recent range
    starts = pd.to_datetime(
        np.random.randint(
            pd.Timestamp("2025-01-01").value,
            pd.Timestamp("2025-12-31").value,
            size=n,
        )
    )

    # Random time deltas: 30 minutes to 1 week
    deltas = pd.to_timedelta(
        np.random.randint(
            30 * 60,  # 30 minutes in seconds
            7 * 24 * 3600,  # 1 week in seconds
            size=n,
        ),
        unit="s",
    )

    ends = starts + deltas

    # 1–100 customers
    customers = np.random.randint(1, 101, size=n)

    # Small number of reference numbers so there are duplicates. This
    # isn't very realistic because references probably won't overlap
    reference = [f"REF-{i}" for i in np.random.randint(1, 5, n)]

    df = pd.DataFrame(
        {
            "start": starts.floor("min"),
            "end": ends.floor("min"),
            "customers": customers,
            "reference": reference,
        }
    )

    return df


@pytest.fixture
def incidents() -> pd.DataFrame:
    """Dummy incident data for testing."""

    csv = StringIO("""start,end,customers,reference
    2025-01-15 00:08:00,2025-01-15 15:51:00,5,REF-1
    2025-02-07 23:25:00,2025-02-13 09:27:00,59,REF-2
    2025-02-21 00:53:00,2025-02-21 06:09:00,22,REF-1
    2025-03-17 05:11:00,2025-03-22 23:37:00,51,REF-3
    2025-04-04 10:18:00,2025-04-10 08:28:00,7,REF-3
    2025-04-06 18:06:00,2025-04-11 13:29:00,94,REF-2
    2025-05-03 15:46:00,2025-05-07 22:08:00,84,REF-4
    2025-05-05 15:10:00,2025-05-11 15:00:00,4,REF-3
    2025-05-08 00:30:00,2025-05-10 18:01:00,77,REF-1
    2025-05-28 06:30:00,2025-06-02 05:44:00,72,REF-3
    2025-06-21 00:56:00,2025-06-24 12:57:00,66,REF-2
    2025-08-01 14:23:00,2025-08-08 12:02:00,68,REF-3
    2025-08-11 21:28:00,2025-08-15 21:44:00,21,REF-2
    2025-09-06 02:33:00,2025-09-07 02:18:00,96,REF-2
    2025-09-15 01:31:00,2025-09-17 08:42:00,14,REF-2
    2025-10-18 22:46:00,2025-10-25 06:46:00,56,REF-3
    2025-11-04 22:03:00,2025-11-06 23:14:00,49,REF-1
    2025-12-11 12:47:00,2025-12-14 11:54:00,67,REF-3
    2025-12-11 23:25:00,2025-12-12 10:13:00,64,REF-3
    2025-12-29 15:52:00,2026-01-01 21:38:00,23,REF-3
    """)

    return pd.read_csv(csv, parse_dates=["start", "end"]).convert_dtypes()


@pytest.fixture
def incidents_with_areas(incidents) -> gpd.GeoDataFrame:

    df = incidents
    # Points going anti-clockwise
    points = [Point(0.5, 0.5), Point(0.5, 1.5), Point(1.5, 1.5), Point(1.5, 0.5)] * 5
    # Works providing len(df) == 20
    assert len(df) == len(points)

    df["geometry"] = points
    gdf = gpd.GeoDataFrame(df, geometry="geometry")
    return gdf


def test_resilience(incidents):

    df = incidents.pwrd.resilience("start", "end", "customers")

    # The resilience dataframe should have an individual entry for
    # each start and end time, however, if two incidents start or end
    # at exactly the same time they will be combined in the resilience dataframe
    unique_dates = pd.concat([incidents["start"], incidents["end"]]).drop_duplicates()
    assert len(unique_dates) == len(df)

    # The first element of the resience dataframe should be -the
    # customers in the first row of the incident dataframe (providing
    # no two incidents have the same start time)
    assert df.iloc[0]["resilience"] == -incidents.iloc[0]["customers"]

    # After final entry in the resilience dataframe should be 0
    # i.e. all incidents have finished
    assert df.iloc[-1]["resilience"] == 0


def test_fault_counts(incidents_with_areas):
    """Test that we can aggregate fault data into different time periods."""

    # These boxes should be as:
    # [3][2]
    # [0][1]
    boxes = [
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
        Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
        Polygon([(0, 1), (1, 1), (1, 2), (0, 2)]),
    ]

    areas = gpd.GeoDataFrame(
        geometry=boxes,
        index=pd.Index(["A", "B", "C", "D"], name="area"),
    )

    hour_df = incidents_with_areas.pwrd.fault_counts(areas, "start", "end", "reference")
    daily_df = incidents_with_areas.pwrd.fault_counts(
        areas, "start", "end", "reference", "1D"
    )
    assert len(hour_df.geometry) == len(daily_df) == 4
    assert len(hour_df.valid_time) > len(daily_df.valid_time)

    # No matter whether we do faults/hour or faults/day, the total
    # number of faults should be the same
    assert hour_df.sum().item() == daily_df.sum().item()


if __name__ == "__main__":
    # For (re-)generating test data
    print(generate_incidents().sort_values("start").to_csv(index=False))
