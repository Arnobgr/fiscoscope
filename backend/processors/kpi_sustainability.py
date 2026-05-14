"""
KPI: Fiscal Deficit Trend — see PRD §5.7.

France general government fiscal balance as % of GDP, from INSEE BDM
(B9_S13 / nominal GDP × 100).

Peer countries and public-debt-to-GDP are OECD-sourced. Per the Session 4
decision (see Runtime discoveries in CLAUDE.md), OECD wiring is deferred to
Session 7 — live column layouts are not inspectable offline — so the `peers`
block is emitted empty and debt is omitted for now.
"""

import logging

from processors import (
    annual_values,
    build_latest,
    load_insee_series,
    now_iso,
    write_output,
)

log = logging.getLogger(__name__)


def compute_fiscal_sustainability() -> dict:
    """Compute the Fiscal Deficit Trend and write kpi_sustainability.json."""
    series = load_insee_series()
    balance = annual_values(series["fiscal_balance"])
    gdp = annual_values(series["gdp_nominal"])

    france = [
        {"year": year, "value": round(balance[year] / gdp[year] * 100, 2)}
        for year in sorted(set(balance) & set(gdp))
        if gdp[year]
    ]

    payload = {
        "kpi_id": "sustainability",
        "kpi_name": "Fiscal Deficit Trend",
        "description": (
            "General government fiscal balance as % of GDP. Negative values are "
            "deficits. Tracks whether public finances are sustainable over time."
        ),
        "unit": "percent",
        "source": "INSEE BDM — Comptes des APU",
        "methodology": (
            "B9_S13 (net lending/borrowing, all APU) / nominal GDP × 100. Peer "
            "countries and public-debt-to-GDP are OECD-sourced and deferred — "
            "emitted empty until live OECD column layouts are confirmed "
            "(Session 7)."
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": {},
        "latest": build_latest(france),
    }
    write_output("kpi_sustainability.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = compute_fiscal_sustainability()
    print(f"\nFiscal sustainability: {len(result['france'])} France data points")
    if result["latest"]:
        print(f"Latest: {result['latest']}")
