"""
KPI: Debt Service Burden — interest paid on public debt (INSEE D41_S13) as a
percentage of total government revenue. Puts the orphaned debt-interest series
to use as a sustainability-efficiency signal: how much of each revenue euro is
consumed servicing past borrowing before any service is delivered.
Peers (roadmap 1.8): Eurostat gov_10a_main interest payable (D41PAY) / total
revenue (TR), same definition; France's own Eurostat values agree with the
INSEE series to within 0.1 pt.
"""

import logging

from processors import (
    EU27_AVG_KEY,
    EUROSTAT_PEER_NOTE,
    EUROSTAT_PEERS,
    annual_values,
    build_latest,
    load_eurostat_long,
    load_insee_series,
    now_iso,
    pick,
    ratio,
    series_by_country,
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

    main = load_eurostat_long("eurostat_main")
    s13 = main[(main["unit"] == "MIO_EUR") & (main["sector"] == "S13")]
    peer_ratio = ratio(pick(s13, na_item="D41PAY"), pick(s13, na_item="TR"))
    peers = series_by_country(peer_ratio, [*EUROSTAT_PEERS, EU27_AVG_KEY])

    payload = {
        "kpi_id": "debt_service",
        "kpi_name": "Debt Service Burden",
        "description": (
            "Interest paid on public debt as a percentage of total government "
            "revenue. A rising burden crowds out service delivery."
        ),
        "unit": "percent",
        "source": (
            "INSEE BDM — CNT-2020-CSI (D41_S13, OTE_S13, B9NF_S13) ; pays comparés : "
            "Eurostat — gov_10a_main (D41PAY, TR)"
        ),
        "methodology": (
            "D41_S13 (intérêts versés, ensemble des APU) / total des recettes "
            "publiques, où recette = dépense totale des APU (OTE) + solde public "
            "(B9NF). Le tout issu des comptes trimestriels CNT-2020-CSI cumulés "
            "sur l'année. Pays comparés : intérêts payables (D41PAY) / recettes "
            "totales (TR) des APU, Eurostat gov_10a_main, en millions d'euros "
            "courants ; calculé de la même façon pour la France, ce ratio Eurostat "
            "s'écarte de moins de 0,1 point de la série INSEE. "
            + EUROSTAT_PEER_NOTE
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": peers,
        "latest": build_latest(france),
    }
    write_output("kpi_debt_service.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = compute_debt_service()
    print(f"\nDebt service: {len(r['france'])} France points; latest: {r['latest']}")
