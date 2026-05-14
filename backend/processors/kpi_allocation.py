"""
KPI: Productive Spend Ratio (PRD §5.4) and Pension/Investment Ratio (PRD §5.5).

Both are France-only series from INSEE BDM; the PRD names no peer source, so
the `peers` block is empty.
"""

import logging

from processors import (
    annual_values,
    build_latest,
    load_insee_series,
    now_iso,
    write_output,
)
from processors.cofog import CLASSIFICATION_CAVEAT, base_break_note, bucket_cofog

log = logging.getLogger(__name__)


def compute_productive_spend() -> dict:
    """Compute the Productive Spend Ratio and write kpi_productive_spend.json."""
    series = load_insee_series()
    buckets = bucket_cofog(series)
    total = annual_values(series["total_apu_expenditure"])

    france = [
        {"year": int(row.year), "value": round(row.productive / total[int(row.year)] * 100, 2)}
        for row in buckets.itertuples()
        if int(row.year) in total and total[int(row.year)]
    ]

    methodology = (
        "COFOG productive bucket (GF04 economic affairs + GF05 environmental "
        "protection + GF06 housing) / total APU expenditure × 100. "
        + CLASSIFICATION_CAVEAT
    )
    note = base_break_note(p["year"] for p in france)
    if note:
        methodology += " " + note

    payload = {
        "kpi_id": "productive_spend",
        "kpi_name": "Productive Spend Ratio",
        "description": (
            "Share of total public expenditure going to productive functions "
            "(infrastructure, economic affairs, environment, housing) rather "
            "than transfers or administration."
        ),
        "unit": "percent",
        "source": "INSEE BDM — Comptes des APU par fonction (COFOG)",
        "methodology": methodology,
        "last_updated": now_iso(),
        "france": france,
        "peers": {},
        "latest": build_latest(france),
    }
    write_output("kpi_productive_spend.json", payload)
    return payload


def compute_pension_investment() -> dict:
    """Compute the Pension/Investment Ratio and write kpi_pension_investment.json."""
    series = load_insee_series()
    pension = annual_values(series["cofog_gf10"])
    investment = annual_values(series["public_investment"])

    france = [
        {"year": year, "value": round(pension[year] / investment[year], 2)}
        for year in sorted(set(pension) & set(investment))
        if investment[year]
    ]

    payload = {
        "kpi_id": "pension_investment",
        "kpi_name": "Pension / Investment Ratio",
        "description": (
            "Social protection expenditure relative to public investment. A "
            "rising ratio means the state increasingly consumes its own "
            "productive capacity rather than building it."
        ),
        "unit": "ratio",
        "source": "INSEE BDM — Comptes des APU",
        "methodology": (
            "COFOG GF10 (social protection expenditure, all APU) / P51_S13 "
            "(gross fixed capital formation, all APU)."
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": {},
        "latest": build_latest(france),
    }
    write_output("kpi_pension_investment.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ps = compute_productive_spend()
    pi = compute_pension_investment()
    print(f"\nProductive spend: {len(ps['france'])} France data points")
    print(f"Pension/investment: {len(pi['france'])} France data points")
