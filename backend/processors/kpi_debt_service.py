"""
KPI: Debt Service Burden — interest paid on public debt (INSEE D41_S13) as a
percentage of total government revenue. Puts the orphaned debt-interest series
to use as a sustainability-efficiency signal: how much of each revenue euro is
consumed servicing past borrowing before any service is delivered.
France-only; the PRD names no peer source.
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


def compute_debt_service() -> dict:
    """Compute the Debt Service Burden and write kpi_debt_service.json."""
    series = load_insee_series()
    interest = annual_values(series["debt_interest"])
    expenditure = annual_values(series["total_apu_expenditure"])
    balance = annual_values(series["fiscal_balance"])

    france = []
    for y in sorted(set(interest) & set(expenditure) & set(balance)):
        revenue = expenditure[y] + balance[y]
        if revenue:
            france.append({"year": y, "value": round(interest[y] / revenue * 100, 2)})

    payload = {
        "kpi_id": "debt_service",
        "kpi_name": "Debt Service Burden",
        "description": (
            "Interest paid on public debt as a percentage of total government "
            "revenue. A rising burden crowds out service delivery."
        ),
        "unit": "percent",
        "source": "INSEE BDM — CNT-2020-CSI (D41_S13, OTE_S13, B9NF_S13)",
        "methodology": (
            "D41_S13 (interest paid, all APU) / total government revenue, where "
            "revenue = total APU expenditure (OTE) + fiscal balance (B9NF). All "
            "from CNT-2020-CSI quarterly accounts summed to annual."
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": {},
        "latest": build_latest(france),
    }
    write_output("kpi_debt_service.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = compute_debt_service()
    print(f"\nDebt service: {len(r['france'])} France points; latest: {r['latest']}")
