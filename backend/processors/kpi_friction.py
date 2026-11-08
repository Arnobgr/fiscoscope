"""
KPI: Friction Ratio — see PRD §5.3.

The core support and sovereign COFOG functions (GF01 general public services
+ GF02 defence + GF03 public order) relative to total government revenue;
debt interest sits inside GF01 and is therefore not added separately.

Eurostat gov_10a_exp (COFOG) and gov_10a_main (TR, total revenue) for France
and peers alike. Until roadmap 1.9 the France series used the INSEE+OECD
COFOG stitch with revenue approximated as expenditure + balance, and peers
were removed because their denominator (expenditure) differed; Eurostat
publishes the same revenue aggregate for every country, so peers are back.
"""

import logging

from processors import (
    EU27_AVG_KEY,
    EUROSTAT_PEER_NOTE,
    EUROSTAT_PEERS,
    build_latest,
    france_and_peers,
    load_eurostat_long,
    now_iso,
    pick,
    ratio,
    write_output,
)
from processors.kpi_allocation import cofog_sum

log = logging.getLogger(__name__)


def compute_friction_ratio() -> dict:
    """Compute the Friction Ratio and write kpi_friction_ratio.json."""
    exp = load_eurostat_long("eurostat_exp")
    main = load_eurostat_long("eurostat_main")
    core = cofog_sum(exp[exp["unit"] == "MIO_EUR"], ["GF01", "GF02", "GF03"])
    revenue = pick(main, unit="MIO_EUR", sector="S13", na_item="TR")
    france, peers = france_and_peers(ratio(core, revenue), [*EUROSTAT_PEERS, EU27_AVG_KEY])

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
        "source": (
            "Eurostat — gov_10a_exp (dépenses par fonction COFOG) et gov_10a_main "
            "(recettes totales des APU)"
        ),
        "methodology": (
            "Le bloc COFOG « fonctions support et régaliennes de base » (GF01 "
            "services publics généraux + GF02 défense + GF03 ordre et sécurité "
            "publics) rapporté aux recettes publiques totales (TR), ensemble des "
            "APU, en millions d'euros courants. Les intérêts de la dette sont "
            "compris dans GF01 et ne sont pas ajoutés séparément. "
            + EUROSTAT_PEER_NOTE
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": peers,
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
