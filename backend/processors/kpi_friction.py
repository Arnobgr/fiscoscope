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
            "Share of government revenue absorbed by the State's core support "
            "and sovereign functions (general public services, defence, public "
            "order and safety) — the running cost of the apparatus before "
            "service delivery and transfers. Not a measure of waste."
        ),
        "unit": "percent",
        "source": "INSEE BDM (1995–2020) + OECD GIP 2025 (2021+)",
        "methodology": (
            "Le bloc COFOG « fonctions support et régaliennes de base » (GF01 "
            "services publics généraux + GF02 défense + GF03 ordre et sécurité "
            "publics) rapporté aux recettes publiques. Les intérêts de la dette "
            "sont compris dans GF01 et ne sont pas ajoutés séparément. Le "
            "dénominateur est le total des recettes publiques, calculé comme la "
            "dépense COFOG totale + le solde public (B9_S13, INSEE), faute de "
            "série directe de recettes fiscales — il s'agit d'une approximation "
            "(voir PRD §5.3). Indicateur France uniquement : aucune comparaison "
            "internationale n'est affichée, le périmètre du dénominateur "
            "(recettes) n'étant pas comparable d'un pays à l'autre. " + STITCH_NOTE
        ),
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
