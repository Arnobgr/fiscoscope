"""
KPI: Public Employment (roadmap 1.7) — general-government employment as a
share of total employment, OECD Government at a Glance 2025 (2007 onwards).
France and the 6 peers; the dataflow publishes no OECD aggregate.
"""

import logging

from processors import (
    OECD_PEERS,
    build_context,
    build_latest,
    france_and_peers,
    load_oecd_long,
    now_iso,
    write_output,
)
from processors.kpi_tax_burden import one_per_year

log = logging.getLogger(__name__)


def compute_public_employment() -> dict:
    """Compute the Public Employment share and write kpi_public_employment.json."""
    df = load_oecd_long("oecd_public_employment")
    df = one_per_year(df[(df["measure"] == "EMPG") & (df["unit_measure"] == "PT_EMP")])
    france, peers = france_and_peers(df, OECD_PEERS)

    payload = {
        "kpi_id": "public_employment",
        "kpi_name": "Public Employment",
        "description": (
            "Employment in general government as % of total employment "
            "(OECD Government at a Glance 2025)."
        ),
        "unit": "percent",
        "source": "OCDE — Government at a Glance 2025 (DF_GOV_EMPPS_REP_2025)",
        "methodology": (
            "Emploi dans les administrations publiques (État, collectivités "
            "locales, hôpitaux publics, sécurité sociale) en % de l'emploi total, "
            "selon la définition harmonisée de l'OCDE (Government at a Glance "
            "2025). Le périmètre suit les comptes nationaux : un même service "
            "(santé, éducation, transports) peut être assuré par des agents publics "
            "dans un pays et par des entreprises ou associations financées sur "
            "fonds publics dans un autre, ce qui limite la comparaison des niveaux. "
            "Pays comparés : Allemagne, Espagne, Italie, Pays-Bas, Royaume-Uni et "
            "Suède ; l'OCDE ne publie pas de moyenne pour cette série."
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": peers,
        "latest": build_latest(france),
        "context": build_context(france, peers),
    }
    write_output("kpi_public_employment.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = compute_public_employment()
    print(f"Public employment: {len(r['france'])} France points; latest {r['latest']}")
