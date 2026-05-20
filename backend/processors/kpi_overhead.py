"""
KPI: Administrative Overhead Rate — see PRD §5.2.

Formula: public sector wage bill (D1_S13) / total APU expenditure × 100.
France series from INSEE BDM's CNT-2020-CSI quarterly accounts, summed to
annual values. Peer comparison is deferred to a later session and emitted
as an empty `peers` block.
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
)

log = logging.getLogger(__name__)


def compute_overhead_rate() -> dict:
    """Compute the Administrative Overhead Rate and write kpi_overhead_rate.json."""
    series = load_insee_series()
    wage = annual_values(series["wage_bill_apu"])
    total = annual_values(series["total_apu_expenditure"])

    france = [
        {"year": year, "value": round(wage[year] / total[year] * 100, 2)}
        for year in sorted(set(wage) & set(total))
        if total[year]
    ]

    fiscal = load_oecd_long("oecd_fiscal")
    ge = fiscal[fiscal["measure"] == "GE"]
    d1 = ge[ge["transaction"] == "D1"][["country", "year", "value"]].rename(columns={"value": "d1"})
    # No `_T` total under MEASURE=GE in the cache; total expenditure is the sum
    # of the GE component transactions (all % of GDP) — matches France's own
    # D1/OTE level (verified Session A).
    tot = ge.groupby(["country", "year"])["value"].sum().rename("tot").reset_index()
    merged = d1.merge(tot, on=["country", "year"])
    merged["value"] = merged["d1"] / merged["tot"] * 100
    peers = peer_series(merged[["country", "year", "value"]])

    payload = {
        "kpi_id": "overhead_rate",
        "kpi_name": "Administrative Overhead Rate",
        "description": (
            "Public sector wage bill as % of total public expenditure. Measures "
            "how much of every euro spent goes to running the administrative "
            "apparatus rather than delivering services or transfers."
        ),
        "unit": "percent",
        "source": "INSEE BDM — CNT-2020-CSI (quarterly, base 2020)",
        "methodology": (
            "D1_S13 (compensation of employees, all APU) / OTE_S13 (total APU "
            "expenditure) × 100. Quarterly series summed to annual; incomplete "
            "years dropped."
            " Peers: OECD GIP 2025, D1/total-expenditure (both % of GDP) — "
            "comparable to the France ratio; OECD_AVG is the unweighted mean of "
            "DEU/GBR/ITA/ESP/NLD/SWE; peer series start 2007."
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": peers,
        "latest": build_latest(france),
    }
    write_output("kpi_overhead_rate.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = compute_overhead_rate()
    print(f"\nOverhead rate: {len(result['france'])} France data points")
    if result["latest"]:
        print(f"Latest: {result['latest']}")
