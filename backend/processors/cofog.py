"""
COFOG classification, bucketing, and INSEE+OECD stitching — see PRD §4.

The 10 top-level COFOG functions are grouped into three efficiency buckets
(productive / redistributive / administrative) per the classification in
config.py. This bucketing is the dashboard's core value-add.

INSEE's CNA-2014-DEP-APU (the only INSEE family carrying the functional
breakdown) is frozen at 2020 and no base-2020 successor has been published.
To keep the time series moving past 2020, OECD GIP 2025 COFOG values (which
include France) are converted to EUR via INSEE's GDP series and stitched in
for years after the last INSEE observation.

Caveat (PRD §4): Education (GF09) and Health (GF07) mix investment and
transfer components. They are classified by dominant component — GF09 as
redistributive, GF07 as redistributive — which is an approximation.
"""

import json
import logging
import re

import pandas as pd

from config import (
    COFOG_ADMINISTRATIVE,
    COFOG_PRODUCTIVE,
    COFOG_REDISTRIBUTIVE,
)
from processors import annual_values, latest_raw

log = logging.getLogger(__name__)

BUCKETS = {
    "productive": COFOG_PRODUCTIVE,
    "redistributive": COFOG_REDISTRIBUTIVE,
    "administrative": COFOG_ADMINISTRATIVE,
}

# Map both logical INSEE names ("cofog_gf04") and OECD codes ("GF04") to bucket.
_GF_TO_BUCKET: dict[str, str] = {}
for _bucket, _gfs in BUCKETS.items():
    for _gf in _gfs:
        _GF_TO_BUCKET[_gf] = _bucket
        _GF_TO_BUCKET[_gf.replace("cofog_gf", "GF").upper()] = _bucket

CLASSIFICATION_CAVEAT = (
    "COFOG functions are grouped into productive/redistributive/administrative "
    "buckets per the dashboard's own classification (PRD §4). Education (GF09) "
    "and Health (GF07) mix investment and transfer components and are classified "
    "by dominant component — this is an approximation."
)

STITCH_NOTE = (
    "INSEE's CNA-2014-DEP-APU COFOG family is frozen at 2020; post-2020 values "
    "are sourced from OECD Government at a Glance 2025 (France only), converted "
    "from % of GDP to EUR via INSEE nominal GDP. Each datapoint is tagged with "
    "its source. INSEE and OECD agree within ±0.4 percentage points of GDP at "
    "the 2020 seam."
)

_TOP_GF_RE = re.compile(r"^GF(0[1-9]|10)$")


def _insee_cofog_eur(series: dict[str, pd.DataFrame]) -> dict[int, dict[str, float]]:
    """Per-year {gf_code: eur} from cached INSEE cofog_gf01..gf10 (annual)."""
    out: dict[int, dict[str, float]] = {}
    for i in range(1, 11):
        gf_logical = f"cofog_gf{i:02d}"
        gf_oecd = f"GF{i:02d}"
        df = series.get(gf_logical)
        if df is None or df.empty:
            log.warning(f"INSEE COFOG series '{gf_logical}' missing or empty")
            continue
        for year, eur in annual_values(df).items():
            out.setdefault(year, {})[gf_oecd] = eur
    return out


def _oecd_cofog_pct_gdp_france() -> dict[int, dict[str, float]]:
    """
    Per-year {gf_code: pct_gdp} from cached OECD COFOG for France.
    Top-10 GF functions only (sub-codes like GF0501 are discarded).
    """
    raw_path = latest_raw("oecd_cofog")
    if raw_path is None:
        log.warning("No cached oecd_cofog raw — OECD stitch will not extend the series")
        return {}
    df = pd.DataFrame(json.loads(raw_path.read_text()))
    fra = df[
        (df["REF_AREA"] == "FRA")
        & (df["MEASURE"] == "GE")
        & (df["UNIT_MEASURE"] == "PT_B1GQ")
        & df["EXPENDITURE"].str.match(_TOP_GF_RE)
    ].copy()
    fra["TIME_PERIOD"] = fra["TIME_PERIOD"].astype(int)
    fra["OBS_VALUE"] = fra["OBS_VALUE"].astype(float)
    out: dict[int, dict[str, float]] = {}
    for (year, gf), val in fra.groupby(["TIME_PERIOD", "EXPENDITURE"])["OBS_VALUE"].first().items():
        out.setdefault(int(year), {})[gf] = float(val)
    return out


def cofog_eur_stitched(
    series: dict[str, pd.DataFrame], gdp_by_year: dict[int, float]
) -> dict[int, dict]:
    """
    Per-year COFOG breakdown in EUR for France, stitched INSEE+OECD.
    Returns {year: {GF01..GF10 → eur, source: "INSEE"|"OECD"}}.

    INSEE values pass through directly (1995–2020). OECD years > last INSEE
    year are converted from % of GDP to EUR via gdp_by_year and appended.
    """
    insee = _insee_cofog_eur(series)
    oecd_pct = _oecd_cofog_pct_gdp_france()

    out: dict[int, dict] = {year: {**vals, "source": "INSEE"} for year, vals in insee.items()}
    cutoff = max(insee) if insee else 0

    for year, by_gf in oecd_pct.items():
        if year <= cutoff:
            continue
        if year not in gdp_by_year:
            log.debug(f"Skipping OECD {year}: no GDP available")
            continue
        gdp = gdp_by_year[year]
        out[year] = {**{gf: pct / 100.0 * gdp for gf, pct in by_gf.items()}, "source": "OECD"}
    return out


def bucket_cofog(
    series: dict[str, pd.DataFrame], gdp_by_year: dict[int, float]
) -> pd.DataFrame:
    """
    Sum the COFOG GF01–GF10 series into the three efficiency buckets by year,
    stitching INSEE (1995–2020) with OECD (post-2020). Returns a DataFrame
    with columns: year, productive, redistributive, administrative, total,
    source — one row per year, monetary columns in EUR (millions).
    """
    eur_by_year = cofog_eur_stitched(series, gdp_by_year)
    rows = []
    for year in sorted(eur_by_year):
        gfs = eur_by_year[year]
        source = gfs.pop("source")
        bucket_totals = {"productive": 0.0, "redistributive": 0.0, "administrative": 0.0}
        for gf, eur in gfs.items():
            bucket = _GF_TO_BUCKET.get(gf)
            if bucket:
                bucket_totals[bucket] += eur
        rows.append(
            {
                "year": year,
                **bucket_totals,
                "total": sum(bucket_totals.values()),
                "source": source,
            }
        )
    return pd.DataFrame(rows)


def function_eur_stitched(
    gf_code: str,
    series: dict[str, pd.DataFrame],
    gdp_by_year: dict[int, float],
) -> list[dict]:
    """
    Single-function EUR series for France, stitched INSEE+OECD.
    gf_code accepts both 'GF10' and 'cofog_gf10'.
    Returns sorted [{year, value, source}, ...].
    """
    code = gf_code.replace("cofog_gf", "GF").upper()
    eur_by_year = cofog_eur_stitched(series, gdp_by_year)
    return [
        {"year": y, "value": eur_by_year[y][code], "source": eur_by_year[y]["source"]}
        for y in sorted(eur_by_year)
        if code in eur_by_year[y]
    ]
