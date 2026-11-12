"""
KPI: Fiscal Deficit Trend — see PRD §5.7.

France general government fiscal balance as % of GDP, from INSEE BDM
(B9_S13 quarterly summed to annual / nominal GDP × 100), plus the Maastricht
public-debt-to-GDP ratio (DETTE-TRIM-APU-2020, year-end stock).

Peers are OECD-sourced (GIP 2025, % of GDP): net lending/borrowing for the
deficit and Maastricht gross debt for the debt, each as a `deficit`/`debt`
sub-block under `peers`, with an unweighted 6-peer OECD_AVG. Peer data starts
2007 (OECD GIP coverage limit). The `debt_holders` block (roadmap 1.6) splits
France's debt by holder from Eurostat gov_10dd_ggd (available from 2020).

Also: Deficit by Sub-sector (roadmap 1.4) — balance of central government,
local government and social security, Eurostat gov_10a_main, 1995 onwards.
"""

import logging

from processors import (
    PER_CAPITA_SOURCE,
    annual_values,
    build_latest,
    france_values,
    load_eurostat_long,
    load_insee_series,
    load_oecd_long,
    now_iso,
    peer_series,
    per_capita_block,
    per_capita_note,
    pick,
    series_by_country,
    write_output,
    year_end_value,
)

log = logging.getLogger(__name__)

DEBT_HOLDERS_METHODOLOGY = (
    " Détenteurs de la dette (depuis 2020) : Eurostat gov_10dd_ggd, dette "
    "consolidée au sens de Maastricht en % du PIB, par secteur détenteur — "
    "non-résidents (S2), Banque de France (S121, titres acquis pour l'essentiel "
    "dans le cadre des programmes d'achats de l'Eurosystème) et autres résidents "
    "(banques, assurances, fonds, ménages…), ces derniers obtenus par différence "
    "entre le total et les deux autres. La ventilation par détenteur n'est "
    "publiée qu'à partir de 2020 pour la France."
)


def debt_holders() -> dict:
    """France debt by holder (% of GDP): non-residents, Banque de France, other residents."""
    debt = load_eurostat_long("eurostat_debt")
    fr = debt[debt["country"] == "FRA"].pivot_table(
        index="year", columns="sector2", values="value"
    ).dropna(subset=["S1_S2", "S2", "S121"])
    fr["other"] = fr["S1_S2"] - fr["S2"] - fr["S121"]

    def points(col: str) -> list[dict]:
        return [{"year": int(y), "value": round(float(v), 2)} for y, v in fr[col].items()]

    return {
        "france": {
            "non_residents": points("S2"),
            "central_bank": points("S121"),
            "other_residents": points("other"),
        }
    }


def compute_fiscal_sustainability() -> dict:
    """Compute the Fiscal Deficit Trend and write kpi_sustainability.json."""
    series = load_insee_series()
    balance = annual_values(series["fiscal_balance"])
    gdp = annual_values(series["gdp_nominal"])

    france = [
        {"year": year, "value": round(balance[year] / gdp[year] * 100, 2)}
        for year in sorted(set(balance) & set(gdp))
        if gdp[year]
    ]

    # Maastricht public-debt-to-GDP (year-end stock, base 2020), already a ratio.
    debt_ratio = year_end_value(series["public_debt_ratio"])
    debt_france = [
        {"year": y, "value": round(debt_ratio[y], 2)} for y in sorted(debt_ratio)
    ]

    # Peer raw is pre-filtered to net-lending-%GDP / Maastricht-debt-%GDP by the
    # fetcher key, so country/year/value is all that's needed.
    deficit_peers = load_oecd_long("oecd_deficit")
    debt_peers = load_oecd_long("oecd_debt")
    peers = {
        "deficit": peer_series(deficit_peers[["country", "year", "value"]]),
        "debt": peer_series(debt_peers[["country", "year", "value"]]),
    }

    # € per inhabitant (roadmap 2.1): balance in M€, Maastricht debt in Md€.
    debt_eur = year_end_value(series["public_debt_eur"])
    per_capita = per_capita_block({
        "deficit": {y: v * 1e6 for y, v in balance.items()},
        "debt": {y: v * 1e9 for y, v in debt_eur.items()},
    })

    payload = {
        "kpi_id": "sustainability",
        "kpi_name": "Fiscal Deficit Trend",
        "description": (
            "General government fiscal balance as % of GDP (negative values are "
            "deficits) plus the Maastricht public-debt-to-GDP ratio. Tracks "
            "whether public finances are sustainable over time, benchmarked "
            "against OECD peers."
        ),
        "unit": "percent",
        "source": (
            "INSEE BDM — CNT-2020-CSI + CNA-2020-PIB + DETTE-TRIM-APU-2020 "
            "(Maastricht debt); peers OECD GIP 2025 (DSD_GOV, % of GDP)"
            + PER_CAPITA_SOURCE
        ),
        "methodology": (
            "Déficit : B9NF_S13 (capacité/besoin de financement, ensemble des "
            "APU) cumulé sur l'année / PIB nominal × 100. Dette : ratio dette "
            "publique/PIB au sens de Maastricht (DETTE-TRIM-APU-2020, base 2020), "
            "relevé au dernier trimestre de l'année (T4) puisque la dette est un "
            "stock. Pays comparés : OCDE GIP 2025, capacité/besoin de financement "
            "(GNLB) et dette brute de Maastricht (GGDM), en % du PIB de part et "
            "d'autre — la « moyenne des 6 pays » (clé OECD_AVG) est la moyenne non "
            "pondérée de DEU/GBR/ITA/ESP/NLD/SWE, et non la moyenne de l'OCDE ; "
            "les séries des pays comparés débutent en 2007."
            + DEBT_HOLDERS_METHODOLOGY
            + per_capita_note(per_capita["base_year"])
            + " La dette, un stock relevé en fin d'année, est rapportée de la "
            "même façon à la population et aux prix moyens de l'année."
        ),
        "last_updated": now_iso(),
        "france": france,
        "debt": {"france": debt_france},
        "debt_holders": debt_holders(),
        "per_capita": per_capita,
        "peers": peers,
        "latest": build_latest(france),
    }
    write_output("kpi_sustainability.json", payload)
    return payload


SUBSECTORS = {
    "central": "S1311",
    "local": "S1313",
    "social_security": "S1314",
    "total": "S13",
}


def compute_deficit_subsector() -> dict:
    """Compute the Deficit by Sub-sector and write kpi_deficit_subsector.json."""
    main = load_eurostat_long("eurostat_main")
    subsectors, amounts = {}, {}
    for key, code in SUBSECTORS.items():
        pct = pick(main, unit="PC_GDP", sector=code, na_item="B9")
        eur = pick(main, unit="MIO_EUR", sector=code, na_item="B9")
        amounts[key] = {y: v * 1e6 for y, v in france_values(eur).items()}
        eur = eur.assign(value=eur["value"] / 1000)  # M€ → Md€
        subsectors[key] = {
            "pct_gdp": series_by_country(pct, ["FRA"]).get("FRA", []),
            "eur_bn": series_by_country(eur, ["FRA"]).get("FRA", []),
        }
    france = subsectors["central"]["pct_gdp"]
    per_capita = per_capita_block(amounts)

    payload = {
        "kpi_id": "deficit_subsector",
        "kpi_name": "Deficit by Sub-sector",
        "description": (
            "Balance (deficit or surplus) of each part of general government — "
            "central government, local government, social security — as % of "
            "GDP and in EUR bn. The headline figure is central government."
        ),
        "unit": "percent",
        "source": "Eurostat — gov_10a_main (comptes des APU par sous-secteur)" + PER_CAPITA_SOURCE,
        "methodology": (
            "Capacité (+) ou besoin (−) de financement (B9) de chaque sous-secteur "
            "des administrations publiques : administrations centrales (S1311 — "
            "l'État et les organismes divers d'administration centrale), "
            "administrations locales (S1313 — collectivités territoriales et leurs "
            "établissements) et administrations de sécurité sociale (S1314 — "
            "régimes de sécurité sociale, de retraite complémentaire, assurance "
            "chômage, hôpitaux). La somme des trois égale le solde de l'ensemble "
            "des APU (S13). Chaque solde s'entend après les transferts entre "
            "administrations : l'État finance une partie des ressources des "
            "collectivités et de la sécurité sociale (dotations, compensation "
            "d'allègements de cotisations), si bien que le déficit de l'État "
            "reflète aussi des dépenses exécutées par les autres sous-secteurs. "
            "Les collectivités locales ne peuvent emprunter que pour investir "
            "(règle d'or). En % du PIB : valeurs publiées par Eurostat (arrondies "
            "au dixième) ; en milliards d'euros courants : millions d'euros / 1 000."
            + per_capita_note(per_capita["base_year"])
        ),
        "last_updated": now_iso(),
        "france": france,
        "subsectors": subsectors,
        "per_capita": per_capita,
        "peers": {},
        "latest": build_latest(france),
    }
    write_output("kpi_deficit_subsector.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = compute_fiscal_sustainability()
    print(f"\nFiscal sustainability: {len(result['france'])} France data points")
    if result["latest"]:
        print(f"Latest: {result['latest']}")
    sub = compute_deficit_subsector()
    print(f"Deficit by sub-sector: {len(sub['france'])} France points; latest {sub['latest']}")
