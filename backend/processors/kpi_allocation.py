"""
KPI: Productive Spend Ratio (PRD §5.4) and Pension/Investment Ratio (PRD §5.5).

Both are France-only series; the PRD names no peer source, so the `peers`
block is empty. COFOG inputs are stitched INSEE 1995–2020 + OECD 2021+
(see processors/cofog.py).
"""

import logging

from processors import (
    annual_values,
    build_latest,
    load_insee_series,
    now_iso,
    write_output,
)
from processors.cofog import (
    CLASSIFICATION_CAVEAT,
    STITCH_NOTE,
    bucket_cofog,
    function_eur_stitched,
)

log = logging.getLogger(__name__)


def compute_productive_spend() -> dict:
    """Compute the Productive Spend Ratio and write kpi_productive_spend.json."""
    series = load_insee_series()
    gdp = annual_values(series["gdp_nominal"])
    buckets = bucket_cofog(series, gdp)

    france = [
        {
            "year": int(row.year),
            "value": round(row.productive / row.total * 100, 2),
            "source": row.source,
        }
        for row in buckets.itertuples()
        if row.total
    ]

    payload = {
        "kpi_id": "productive_spend",
        "kpi_name": "Productive Spend Ratio",
        "description": (
            "Share of total public expenditure going to productive functions "
            "(infrastructure, economic affairs, environment, housing) rather "
            "than transfers or administration."
        ),
        "unit": "percent",
        "source": "INSEE BDM (1995–2020) + OECD GIP 2025 (2021+)",
        "methodology": (
            "COFOG productive bucket (GF04 + GF05 + GF06) / total COFOG "
            "expenditure × 100. " + CLASSIFICATION_CAVEAT + " " + STITCH_NOTE
        ),
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
    gdp = annual_values(series["gdp_nominal"])
    investment = annual_values(series["public_investment"])
    pension_series = function_eur_stitched("GF10", series, gdp)

    france = []
    for pt in pension_series:
        year = pt["year"]
        inv = investment.get(year)
        if not inv:
            continue
        france.append(
            {"year": year, "value": round(pt["value"] / inv, 2), "source": pt["source"]}
        )

    payload = {
        "kpi_id": "pension_investment",
        "kpi_name": "Pension / Investment Ratio",
        "description": (
            "Social protection expenditure relative to public investment. A "
            "rising ratio means the state increasingly consumes its own "
            "productive capacity rather than building it."
        ),
        "unit": "ratio",
        "source": "INSEE BDM (1995–2020) + OECD GIP 2025 (2021+)",
        "methodology": (
            "COFOG GF10 (social protection expenditure, all APU) / P5K2 "
            "(gross fixed capital formation, all APU). " + STITCH_NOTE
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
