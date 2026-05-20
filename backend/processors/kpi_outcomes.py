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

  - Tax Expenditure Cost (PRD §5.8) is built from GTED (Global Tax Expenditures
    Database, CC-BY-4.0). France's official full costed list is PDF-only (PLF
    Voies-et-Moyens Tome II), but GTED republishes the same per-provision
    revenue-forgone series in tabular form (Session C). compute_tax_expenditure()
    reads the cached GTED France rows and emits annual total cost, provision
    count and cost-to-revenue ratio. See the Session C note in CLAUDE.md.
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
    Compute the Tax Expenditure Cost KPI (PRD §5.8) and write
    kpi_tax_expenditure.json, from the cached GTED France revenue-forgone series.

    Per year: total cost (Σ revenue forgone, EUR bn), the number of provisions
    reported, the cost as a share of total government revenue, and YoY % change.
    France-only — the PRD names no peer source. GTED flags the two most recent
    years as projections (forecasts), marked with "projection": true.
    """
    raw_path = latest_raw("tax_expenditure")
    if raw_path is None:
        raise FileNotFoundError(
            "No data/raw/tax_expenditure_*.json — run the GTED fetcher "
            "(fetchers.tax_expenditure) first."
        )
    df = pd.DataFrame(json.loads(raw_path.read_text()))
    df["Year"] = df["Year"].astype(int)
    df["RF (LCU)"] = pd.to_numeric(df["RF (LCU)"], errors="coerce")

    series = load_insee_series()
    expenditure = annual_values(series["total_apu_expenditure"])
    balance = annual_values(series["fiscal_balance"])
    revenue = {y: expenditure[y] + balance[y] for y in set(expenditure) & set(balance)}

    france = []
    for year in sorted(df["Year"].unique()):
        grp = df[df["Year"] == year]
        total_eur = float(grp["RF (LCU)"].sum())
        total_bn = round(total_eur / 1e9, 2)
        entry = {
            "year": int(year),
            "total_cost_eur_bn": total_bn,
            "count": int(grp["ProvisionID"].nunique()),
            "projection": bool((grp["Projection/Estimate"] == "Projection").all()),
        }
        if revenue.get(year):
            # INSEE revenue is in millions of EUR; GTED RF (LCU) is in absolute
            # EUR — scale revenue to euros before taking the ratio.
            entry["ratio_to_revenue_pct"] = round(
                total_eur / (revenue[year] * 1e6) * 100, 2
            )
        if france:
            prev = france[-1]["total_cost_eur_bn"]
            if prev:
                entry["yoy_change_pct"] = round((total_bn - prev) / prev * 100, 2)
        france.append(entry)

    payload = {
        "kpi_id": "tax_expenditure",
        "kpi_name": "Tax Expenditure Cost",
        "description": (
            "Total cost of France's tax expenditures (dépenses fiscales / niches "
            "fiscales) — revenue the state forgoes through exemptions, reduced "
            "rates, credits and deferrals — in euros, as a count of provisions, "
            "and as a share of total government revenue. A rising ratio means a "
            "growing slice of potential revenue is given up before any spending."
        ),
        "unit": "mixed",
        "source": (
            "Global Tax Expenditures Database (GTED), Tax Expenditures Lab — "
            "Redonda, von Haldenwang & Aliu, CC-BY-4.0, concept DOI "
            "10.5281/zenodo.5940165; revenue denominator from INSEE BDM "
            "CNT-2020-CSI (OTE_S13 + B9NF_S13)."
        ),
        "methodology": (
            "Per year: total_cost_eur_bn = Σ revenue forgone across all France "
            "provisions (GTED 'RF (LCU)', EUR); count = number of provisions "
            "reported that year (includes provisions costed at zero); "
            "ratio_to_revenue_pct = total cost / total government revenue × 100, "
            "where revenue = total APU expenditure (OTE) + fiscal balance (B9NF) "
            "from CNT-2020-CSI — emitted only for years with INSEE revenue. The "
            "two most recent years are GTED projections (projection: true); "
            "earlier years are estimates. GTED is a third-party compilation of "
            "France's PLF Voies-et-Moyens Tome II; its provision count and "
            "revenue-forgone definition differ slightly from the official annex."
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": {},
        "latest": dict(france[-1]) if france else None,
    }
    write_output("kpi_tax_expenditure.json", payload)
    return payload


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
