"""
KPI: Friction Ratio — see PRD §5.3.

The administrative COFOG bucket (GF01 general public services + GF02 defence
+ GF03 public order) is treated as friction; debt interest sits inside GF01
and is therefore not added separately.

No direct tax-revenue series is resolved in the INSEE idBanks, so total
government revenue is derived as total APU expenditure + fiscal balance
(B9_S13) and used as the denominator — an approximation, per PRD §5.3.
France-only; the PRD names no peer source.

COFOG inputs are stitched INSEE 1995–2020 + OECD 2021+ (see processors/cofog.py).
For OECD years, revenue is approximated as the sum of GF01..GF10 (total
expenditure) + INSEE's fiscal_balance, since OECD's fiscal raw does not
expose B9 in the current cache.
"""

import logging

from processors import (
    annual_values,
    build_latest,
    load_insee_series,
    now_iso,
    write_output,
)
from processors.cofog import STITCH_NOTE, bucket_cofog
from processors.kpi_allocation import _cofog_bucket_peers

log = logging.getLogger(__name__)


def compute_friction_ratio() -> dict:
    """Compute the Friction Ratio and write kpi_friction_ratio.json."""
    series = load_insee_series()
    gdp = annual_values(series["gdp_nominal"])
    buckets = bucket_cofog(series, gdp)
    balance = annual_values(series["fiscal_balance"])

    france = []
    for row in buckets.itertuples():
        year = int(row.year)
        if year not in balance:
            continue
        # Total expenditure: COFOG sum (matches INSEE OTE for 1995–2020,
        # and is the OECD-side total for post-2020).
        revenue = row.total + balance[year]
        if not revenue:
            continue
        france.append(
            {
                "year": year,
                "value": round(row.administrative / revenue * 100, 2),
                "source": row.source,
            }
        )

    payload = {
        "kpi_id": "friction_ratio",
        "kpi_name": "Friction Ratio",
        "description": (
            "Share of government revenue consumed by administrative friction "
            "(general public services, defence, public order, debt interest) "
            "rather than reaching end beneficiaries as services or transfers."
        ),
        "unit": "percent",
        "source": "INSEE BDM (1995–2020) + OECD GIP 2025 (2021+)",
        "methodology": (
            "Le bloc administratif COFOG (GF01 + GF02 + GF03) est considéré "
            "comme de la friction ; les intérêts de la dette sont compris dans "
            "GF01 et ne sont pas ajoutés séparément. Le dénominateur est le "
            "total des recettes publiques, calculé comme la dépense COFOG totale "
            "+ le solde public (B9_S13, INSEE), faute de série directe de "
            "recettes fiscales. Il s'agit d'une approximation — voir PRD §5.3. "
            + STITCH_NOTE
            + " Pays comparés : OCDE GIP 2025, bloc administratif "
            "(GF01+GF02+GF03) / COFOG total. NB : côté France, le dénominateur "
            "est la recette (dépense + solde) tandis que côté pays comparés "
            "c'est la dépense totale ; les comparaisons portent donc sur les "
            "TENDANCES, et non sur les niveaux. OECD_AVG = moyenne non pondérée "
            "des 6 pays comparés ; les séries des pays comparés débutent en 2007."
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": _cofog_bucket_peers(["GF01", "GF02", "GF03"]),
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
