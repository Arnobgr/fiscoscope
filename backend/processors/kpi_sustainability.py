"""
KPI: Fiscal Deficit Trend — see PRD §5.7.

France general government fiscal balance as % of GDP, from INSEE BDM
(B9_S13 quarterly summed to annual / nominal GDP × 100), plus the Maastricht
public-debt-to-GDP ratio (DETTE-TRIM-APU-2020, year-end stock).

Peers are OECD-sourced (GIP 2025, % of GDP): net lending/borrowing for the
deficit and Maastricht gross debt for the debt, each as a `deficit`/`debt`
sub-block under `peers`, with an unweighted 6-peer OECD_AVG. Peer data starts
2007 (OECD GIP coverage limit).
"""

import logging

from processors import (
    annual_values,
    build_latest,
    load_insee_series,
    load_oecd_long,
    now_iso,
    peer_series,
    write_output,
    year_end_value,
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

    # Maastricht public-debt-to-GDP (year-end stock, base 2020), already a ratio.
    debt_ratio = year_end_value(series["public_debt_ratio"])
    debt_france = [
        {"year": y, "value": round(debt_ratio[y], 2)} for y in sorted(debt_ratio)
    ]

    # Peer raw is pre-filtered to net-lending-%GDP / Maastricht-debt-%GDP by the
    # fetcher key, so country/year/value is all that's needed.
    deficit_peers = load_oecd_long("oecd_deficit")
    debt_peers = load_oecd_long("oecd_debt")
    peers = {
        "deficit": peer_series(deficit_peers[["country", "year", "value"]]),
        "debt": peer_series(debt_peers[["country", "year", "value"]]),
    }

    payload = {
        "kpi_id": "sustainability",
        "kpi_name": "Fiscal Deficit Trend",
        "description": (
            "General government fiscal balance as % of GDP (negative values are "
            "deficits) plus the Maastricht public-debt-to-GDP ratio. Tracks "
            "whether public finances are sustainable over time, benchmarked "
            "against OECD peers."
        ),
        "unit": "percent",
        "source": (
            "INSEE BDM — CNT-2020-CSI + CNA-2020-PIB + DETTE-TRIM-APU-2020 "
            "(Maastricht debt); peers OECD GIP 2025 (DSD_GOV, % of GDP)"
        ),
        "methodology": (
            "Deficit: B9NF_S13 (net lending/borrowing, all APU) summed to annual "
            "/ nominal GDP × 100. Debt: Maastricht public-debt-to-GDP "
            "(DETTE-TRIM-APU-2020, base 2020), taken at the year-end (Q4) quarter "
            "since debt is a stock. Peers: OECD GIP 2025 net lending/borrowing "
            "(GNLB) and Maastricht gross debt (GGDM), both % of GDP — OECD_AVG is "
            "the unweighted mean of DEU/GBR/ITA/ESP/NLD/SWE; peer series start 2007."
        ),
        "last_updated": now_iso(),
        "france": france,
        "debt": {"france": debt_france},
        "peers": peers,
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
