"""
KPI: Friction Ratio — see PRD §5.3.

Formula: (total taxes collected − value reaching end beneficiary) / total taxes
collected × 100. The administrative COFOG bucket (GF01 general public services
+ GF02 defence + GF03 public order) is treated as friction; debt interest sits
inside GF01 and is therefore not added separately.

No direct tax-revenue series is resolved in the INSEE idBanks, so total
government revenue is derived as total APU expenditure + fiscal balance
(B9_S13) and used as the denominator — an approximation, per PRD §5.3.
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
from processors.cofog import base_break_note, bucket_cofog

log = logging.getLogger(__name__)


def compute_friction_ratio() -> dict:
    """Compute the Friction Ratio and write kpi_friction_ratio.json."""
    series = load_insee_series()
    buckets = bucket_cofog(series)
    expenditure = annual_values(series["total_apu_expenditure"])
    balance = annual_values(series["fiscal_balance"])

    admin = {int(row.year): float(row.administrative) for row in buckets.itertuples()}

    france = []
    for year in sorted(set(admin) & set(expenditure) & set(balance)):
        revenue = expenditure[year] + balance[year]
        if revenue:
            france.append({"year": year, "value": round(admin[year] / revenue * 100, 2)})

    methodology = (
        "Administrative COFOG bucket (GF01 general public services + GF02 "
        "defence + GF03 public order) treated as friction; debt interest is "
        "included within GF01 and is not added separately. Denominator is total "
        "government revenue, derived as total APU expenditure + fiscal balance "
        "(B9_S13) since no direct tax-revenue series is resolved. This is an "
        "approximation — see PRD §5.3."
    )
    note = base_break_note(p["year"] for p in france)
    if note:
        methodology += " " + note

    payload = {
        "kpi_id": "friction_ratio",
        "kpi_name": "Friction Ratio",
        "description": (
            "Share of government revenue consumed by administrative friction "
            "(general public services, defence, public order, debt interest) "
            "rather than reaching end beneficiaries as services or transfers."
        ),
        "unit": "percent",
        "source": "INSEE BDM — Comptes des APU par fonction (COFOG)",
        "methodology": methodology,
        "last_updated": now_iso(),
        "france": france,
        "peers": {},
        "latest": build_latest(france),
    }
    write_output("kpi_friction_ratio.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = compute_friction_ratio()
    print(f"\nFriction ratio: {len(result['france'])} France data points")
    if result["latest"]:
        print(f"Latest: {result['latest']}")
