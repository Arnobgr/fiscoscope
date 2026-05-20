"""
KPI: Spend vs. Outcome Ratios (PRD §5.9) and Tax Expenditure Cost (PRD §5.8).

  - Spend vs. Outcome — HEALTH ONLY for now. France health spend (COFOG GF07,
    % of GDP, stitched INSEE+OECD) is emitted alongside life expectancy at
    birth (OECD Health Statistics) as two parallel time series — the reader
    judges whether outcomes track spending. Peer benchmarking is deferred
    (Phase 1.5), so there is no "indexed to OECD average" transform.
    The EDUCATION side (spend vs. PISA) is a documented gap: PISA scores are
    not available via OECD's SDMX API (only enrolment / per-student spend /
    instruction-time are), so they cannot be fetched programmatically yet.
    See the Session 9 note in CLAUDE.md.

  - Tax Expenditure needs the PLF "dépenses fiscales" annex (PRD §3.6). The
    Session 8-era catalog probe confirmed the costed tabular data is NOT
    published: only an uncosted 468-row descriptive list and an 8-row top-IR
    snapshot exist. The full chiffrage lives in the Tome II PDF.
    compute_tax_expenditure() therefore stays NotImplementedError. See the
    Session 9 note in CLAUDE.md for the two fallback paths (PDF parse;
    headline aggregate).
"""

import json
import logging

import pandas as pd

from processors import (
    annual_values,
    latest_raw,
    load_insee_series,
    now_iso,
    write_output,
)
from processors.cofog import STITCH_NOTE, function_eur_stitched

log = logging.getLogger(__name__)


def _life_expectancy_france() -> list[dict]:
    """France life expectancy at birth (years) per year, from cached OECD raw."""
    raw_path = latest_raw("oecd_life_expectancy")
    if raw_path is None:
        log.warning("No cached oecd_life_expectancy raw — life-expectancy series empty")
        return []
    df = pd.DataFrame(json.loads(raw_path.read_text()))
    df = df[
        (df["REF_AREA"] == "FRA")
        & (df["MEASURE"] == "LFEXP")
        & (df["AGE"] == "Y0")
        & (df["SEX"] == "_T")
    ]
    rows = (
        df[["TIME_PERIOD", "OBS_VALUE"]]
        .dropna()
        .astype({"TIME_PERIOD": int, "OBS_VALUE": float})
        .sort_values("TIME_PERIOD")
    )
    return [{"year": int(r.TIME_PERIOD), "value": round(float(r.OBS_VALUE), 1)} for r in rows.itertuples()]


def compute_outcomes() -> dict:
    """Compute the health Spend-vs-Outcome KPI and write kpi_outcomes.json."""
    series = load_insee_series()
    gdp = annual_values(series["gdp_nominal"])

    health_spend = [
        {
            "year": pt["year"],
            "value": round(pt["value"] / gdp[pt["year"]] * 100, 2),
            "source": pt["source"],
        }
        for pt in function_eur_stitched("GF07", series, gdp)
        if pt["year"] in gdp and gdp[pt["year"]]
    ]
    life_expectancy = _life_expectancy_france()

    latest = None
    if health_spend and life_expectancy:
        latest = {
            "spend_year": health_spend[-1]["year"],
            "spend_pct_gdp": health_spend[-1]["value"],
            "life_expectancy_year": life_expectancy[-1]["year"],
            "life_expectancy_years": life_expectancy[-1]["value"],
        }

    payload = {
        "kpi_id": "outcomes",
        "kpi_name": "Spend vs. Outcome — Health",
        "description": (
            "France public health spend (COFOG GF07) as % of GDP set against "
            "life expectancy at birth, as two parallel time series. A widening "
            "gap between rising spend and flat outcomes signals declining "
            "efficiency."
        ),
        "unit": "mixed",
        "source": (
            "INSEE BDM + OECD GIP 2025 (health spend, % of GDP); "
            "OECD Health Statistics (life expectancy at birth)"
        ),
        "methodology": (
            "Health block: GF07 (health) COFOG spend / nominal GDP × 100, "
            "stitched INSEE 1995–2020 + OECD 2021+ (each point source-tagged). "
            "Life expectancy at birth, total population, from OECD Health "
            "Statistics (DF_LE). Education (spend vs. PISA) is omitted — PISA "
            "is not available via OECD's SDMX API. Peer benchmarking deferred. "
            + STITCH_NOTE
        ),
        "last_updated": now_iso(),
        "health": {
            "spend_pct_gdp": health_spend,
            "life_expectancy_years": life_expectancy,
        },
        "education": None,
        "peers": {},
        "latest": latest,
    }
    write_output("kpi_outcomes.json", payload)
    return payload


def compute_tax_expenditure() -> dict:
    """
    Compute the Tax Expenditure Cost KPI and write kpi_tax_expenditure.json.

    Blocked: KPI 5.8 needs a costed, multi-year dépenses-fiscales table, but
    no such tabular dataset is published (verified Session 9). data.gouv.fr /
    data.economie.gouv.fr expose only an uncosted 468-row list and an 8-row
    top-IR snapshot; the full chiffrage is PDF-only (PLF Voies et Moyens
    Tome II). Two fallback paths are documented in CLAUDE.md Session 9:
    (2) parse the Tome II PDF; (3) track the headline aggregate total only.
    """
    raise NotImplementedError(
        "compute_tax_expenditure is blocked: no costed tabular dépenses-fiscales "
        "dataset is published (only an uncosted 468-row list + an 8-row top-IR "
        "snapshot). Full chiffrage is PDF-only. See CLAUDE.md Session 9 for the "
        "PDF-parse and headline-aggregate fallback options."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = compute_outcomes()
    h = result["health"]
    print(
        f"\nOutcomes (health): {len(h['spend_pct_gdp'])} spend points, "
        f"{len(h['life_expectancy_years'])} life-expectancy points"
    )
    if result["latest"]:
        print(f"Latest: {result['latest']}")
