"""
KPI: Public Wage Bill Share (formerly "Administrative Overhead Rate") — see
PRD §5.2. Renamed in roadmap Phase 0.1: total D1 includes teachers, health
staff and police, so it is not an administrative-overhead measure.

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
    """Compute the Public Wage Bill Share and write kpi_overhead_rate.json."""
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
        "kpi_name": "Public Wage Bill Share",
        "description": (
            "Public sector wage bill as % of total public expenditure. Covers "
            "all public employees — teachers, health staff, police, soldiers — "
            "not only administrative functions, so it is not an overhead rate."
        ),
        "unit": "percent",
        "source": "INSEE BDM — CNT-2020-CSI (quarterly, base 2020)",
        "methodology": (
            "D1_S13 (rémunération des salariés, ensemble des APU) / OTE_S13 "
            "(dépense totale des APU) × 100. Séries trimestrielles cumulées sur "
            "l'année ; les années incomplètes sont écartées."
            " La rémunération des salariés (D1) couvre l'ensemble des agents "
            "publics — enseignants, personnels de santé, forces de l'ordre, "
            "militaires — et pas seulement les fonctions administratives : ce "
            "ratio n'est donc pas un taux de frais administratifs."
            " Pays comparés : OCDE GIP 2025, D1 / dépense totale (en % du PIB de "
            "part et d'autre) — comparable au ratio français ; la « moyenne des "
            "6 pays » (clé OECD_AVG) est la moyenne non pondérée de "
            "DEU/GBR/ITA/ESP/NLD/SWE, et non la moyenne de l'OCDE ; les séries "
            "des pays comparés débutent en 2007."
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
