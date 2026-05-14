"""
COFOG classification and spend bucketing — see PRD §4.

The 10 top-level COFOG functions are grouped into three efficiency buckets
(productive / redistributive / administrative) per the classification in
config.py. This bucketing is the dashboard's core value-add; it is not
pre-computed by any official source.

Caveat (PRD §4): Education (GF09) and Health (GF07) mix investment and
transfer components. They are classified by dominant component — GF09 as
redistributive, GF07 as redistributive — which is an approximation.
"""

import logging

import pandas as pd

from config import COFOG_PRODUCTIVE, COFOG_REDISTRIBUTIVE, COFOG_ADMINISTRATIVE
from processors import to_year

log = logging.getLogger(__name__)

# INSEE revised its national accounts base in 2020 (previously base 2014),
# which can introduce a structural break in the COFOG series — PRD §12.5.
COFOG_BASE_CHANGE_YEAR = 2020

BUCKETS = {
    "productive": COFOG_PRODUCTIVE,
    "redistributive": COFOG_REDISTRIBUTIVE,
    "administrative": COFOG_ADMINISTRATIVE,
}

CLASSIFICATION_CAVEAT = (
    "COFOG functions are grouped into productive/redistributive/administrative "
    "buckets per the dashboard's own classification (PRD §4). Education (GF09) "
    "and Health (GF07) mix investment and transfer components and are classified "
    "by dominant component — this is an approximation."
)


def bucket_cofog(series: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Sum the COFOG GF01–GF10 series into the three efficiency buckets by year.

    series: dict of logical_name -> DataFrame(date, value), as returned by
            processors.load_insee_series().
    Returns a DataFrame with columns: year, productive, redistributive,
    administrative — one row per year, values in billions EUR.
    """
    frames = []
    for bucket, names in BUCKETS.items():
        for name in names:
            df = series.get(name)
            if df is None or df.empty:
                log.warning(f"COFOG series '{name}' missing or empty — skipping")
                continue
            tmp = df.dropna(subset=["value"]).copy()
            tmp["year"] = tmp["date"].map(to_year)
            tmp["bucket"] = bucket
            frames.append(tmp[["year", "bucket", "value"]])

    if not frames:
        raise ValueError("No COFOG series available to bucket")

    pivot = (
        pd.concat(frames, ignore_index=True)
        .groupby(["year", "bucket"])["value"]
        .sum()
        .unstack("bucket")
    )
    for bucket in BUCKETS:
        if bucket not in pivot.columns:
            pivot[bucket] = 0.0
    return (
        pivot.reset_index()
        .sort_values("year")[["year", "productive", "redistributive", "administrative"]]
        .reset_index(drop=True)
    )


def base_break_note(years) -> str:
    """
    Return a metadata note if the year range spans the 2020 base change,
    otherwise an empty string. PRD §12.5.
    """
    years = list(years)
    if years and min(years) < COFOG_BASE_CHANGE_YEAR <= max(years):
        return (
            f"Series spans the {COFOG_BASE_CHANGE_YEAR} INSEE national accounts "
            f"base change (base 2014 → base 2020); a structural break may be "
            f"present around {COFOG_BASE_CHANGE_YEAR}."
        )
    return ""
