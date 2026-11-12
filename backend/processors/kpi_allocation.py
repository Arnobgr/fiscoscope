"""
KPI: Economic Affairs, Environment & Housing Share (formerly "Productive Spend
Ratio", PRD §5.4), Social Protection / Investment Ratio (PRD §5.5) and
Old-Age Expenditure (roadmap 1.3).

All three read Eurostat gov_10a_exp (COFOG × transaction, 1995–2024 on one
basis), for France and peers alike — this replaced the INSEE 1995–2020 + OECD
2021+ stitch (roadmap 1.9).
"""

import logging

from processors import (
    EU27_AVG_KEY,
    EUROSTAT_PEER_NOTE,
    EUROSTAT_PEERS,
    PER_CAPITA_SOURCE,
    build_latest,
    france_and_peers,
    france_values,
    load_eurostat_long,
    now_iso,
    per_capita_block,
    per_capita_note,
    pick,
    ratio,
    write_output,
)

log = logging.getLogger(__name__)

PEER_CODES = [*EUROSTAT_PEERS, EU27_AVG_KEY]


def cofog_sum(eur, codes: list[str], na_item: str = "TE"):
    """Sum of several COFOG functions per (country, year); rows missing any code are dropped."""
    sub = eur[eur["cofog99"].isin(codes) & (eur["na_item"] == na_item)]
    g = sub.groupby(["country", "year"])["value"]
    out = g.sum().to_frame("value").assign(n=g.size()).reset_index()
    return out[out["n"] == len(codes)][["country", "year", "value"]]


def compute_productive_spend() -> dict:
    """Compute the Economic Affairs, Environment & Housing Share (kpi_productive_spend.json)."""
    exp = load_eurostat_long("eurostat_exp")
    eur = exp[exp["unit"] == "MIO_EUR"]
    shares = ratio(
        cofog_sum(eur, ["GF04", "GF05", "GF06"]), pick(eur, cofog99="TOTAL", na_item="TE")
    )
    france, peers = france_and_peers(shares, PEER_CODES)

    payload = {
        "kpi_id": "productive_spend",
        "kpi_name": "Economic Affairs, Environment & Housing Share",
        "description": (
            "Share of total public expenditure going to three COFOG functions: "
            "economic affairs (GF04), environmental protection (GF05) and "
            "housing and community amenities (GF06). Education and health are "
            "not included."
        ),
        "unit": "percent",
        "source": "Eurostat — gov_10a_exp (dépenses des APU par fonction COFOG)",
        "methodology": (
            "Fonctions COFOG GF04 (affaires économiques) + GF05 (protection de "
            "l'environnement) + GF06 (logement et équipements collectifs) / "
            "dépense publique totale (toutes fonctions) × 100, ensemble des APU, "
            "en millions d'euros courants. L'éducation (GF09) et la santé (GF07) "
            "n'en font pas partie. " + EUROSTAT_PEER_NOTE
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": peers,
        "latest": build_latest(france),
    }
    write_output("kpi_productive_spend.json", payload)
    return payload


def compute_pension_investment() -> dict:
    """Compute the Social Protection / Investment Ratio and write kpi_pension_investment.json."""
    exp = load_eurostat_long("eurostat_exp")
    eur = exp[exp["unit"] == "MIO_EUR"]
    ratios = ratio(
        pick(eur, cofog99="GF10", na_item="TE"),
        pick(eur, cofog99="TOTAL", na_item="P51G"),
        scale=1,
    )
    france, peers = france_and_peers(ratios, PEER_CODES)

    payload = {
        "kpi_id": "pension_investment",
        "kpi_name": "Social Protection / Investment Ratio",
        "description": (
            "Total social protection expenditure (COFOG GF10 — pensions, "
            "unemployment, family, sickness and other transfers, not pensions "
            "alone) relative to public investment, as a multiple. A rising "
            "ratio means the state increasingly consumes its own productive "
            "capacity rather than building it."
        ),
        "unit": "ratio",
        "source": "Eurostat — gov_10a_exp (dépenses des APU par fonction COFOG et par opération)",
        "methodology": (
            "COFOG GF10 (dépenses de protection sociale dans leur ensemble — "
            "retraites, chômage, famille, maladie, etc., et non les seules "
            "retraites) / P51G (formation brute de capital fixe, toutes "
            "fonctions), ensemble des APU, en millions d'euros courants. Le "
            "résultat est un multiple (sans unité). " + EUROSTAT_PEER_NOTE
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": peers,
        "latest": build_latest(france),
    }
    write_output("kpi_pension_investment.json", payload)
    return payload


def compute_pensions() -> dict:
    """Compute Old-Age Expenditure (share of spending and % of GDP) — kpi_pensions.json."""
    exp = load_eurostat_long("eurostat_exp")
    eur = exp[exp["unit"] == "MIO_EUR"]
    shares = ratio(
        pick(eur, cofog99="GF1002", na_item="TE"), pick(eur, cofog99="TOTAL", na_item="TE")
    )
    france, peers = france_and_peers(shares, PEER_CODES)
    pct_gdp = pick(exp, unit="PC_GDP", cofog99="GF1002", na_item="TE")
    gdp_france, gdp_peers = france_and_peers(pct_gdp, PEER_CODES)
    old_age_eur = pick(eur, cofog99="GF1002", na_item="TE")
    per_capita = per_capita_block({"france": {y: v * 1e6 for y, v in france_values(old_age_eur).items()}})

    payload = {
        "kpi_id": "pensions",
        "kpi_name": "Old-Age Expenditure",
        "description": (
            "Public expenditure on old age (COFOG GF1002: pensions and care for "
            "the elderly) as % of total public expenditure, and as % of GDP."
        ),
        "unit": "percent",
        "source": "Eurostat — gov_10a_exp (dépenses des APU par fonction COFOG, niveau 2)"
        + PER_CAPITA_SOURCE,
        "methodology": (
            "Fonction COFOG GF1002 « vieillesse », ensemble des APU : pensions de "
            "retraite (régimes de base et complémentaires, retraites des "
            "fonctionnaires) et prestations liées à la perte d'autonomie des "
            "personnes âgées (allocation personnalisée d'autonomie, aide sociale "
            "à l'hébergement). "
            "Les pensions de réversion relèvent de GF1003 « survivants » et ne "
            "sont pas comprises. Part de la dépense : GF1002 / dépense publique "
            "totale × 100, en millions d'euros courants. En % du PIB : valeur "
            "publiée par Eurostat (arrondie au dixième). " + EUROSTAT_PEER_NOTE
            + per_capita_note(per_capita["base_year"])
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": peers,
        "pct_gdp": {"france": gdp_france, "peers": gdp_peers},
        "per_capita": per_capita,
        "latest": build_latest(france),
    }
    write_output("kpi_pensions.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for fn in (compute_productive_spend, compute_pension_investment, compute_pensions):
        r = fn()
        print(f"{r['kpi_id']}: {len(r['france'])} France points; latest {r['latest']}")
