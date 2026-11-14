"""
KPI: Tax Burden (roadmap 1.5) — total tax revenue as % of GDP, OECD Revenue
Statistics, 1965 onwards. France, the 6 peers (incl. the UK) and the OECD's
own aggregate, kept under its OECD code `OECD_REP` — the only series that may
be labelled "Moyenne OCDE" (the 6-peer mean `OECD_AVG` is not built here).
"""

import logging

from processors import (
    OECD_PEERS,
    PER_CAPITA_SOURCE,
    annual_values,
    build_context,
    build_latest,
    france_and_peers,
    france_values,
    load_insee_series,
    load_oecd_long,
    now_iso,
    per_capita_block,
    per_capita_note,
    write_output,
)

log = logging.getLogger(__name__)

OECD_REP_KEY = "OECD_REP"


def one_per_year(df):
    """Fail loudly if an OECD slice holds several rows per country-year."""
    dup = df[df.duplicated(["country", "year"], keep=False)]
    if not dup.empty:
        raise ValueError(f"Several observations per country-year, e.g.:\n{dup.head()}")
    return df


def compute_tax_burden() -> dict:
    """Compute the Tax Burden and write kpi_tax_burden.json."""
    df = load_oecd_long("oecd_tax_revenue")
    df = one_per_year(df[(df["measure"] == "TAX_REV") & (df["unit_measure"] == "PT_B1GQ")])
    france, peers = france_and_peers(df, [*OECD_PEERS, OECD_REP_KEY])

    # € per inhabitant (roadmap 2.1): the OECD raw holds % of GDP only, so the
    # euro amount is that rate × INSEE nominal GDP (M€).
    gdp = annual_values(load_insee_series()["gdp_nominal"])
    per_capita = per_capita_block({
        "france": {y: r / 100 * gdp[y] * 1e6 for y, r in france_values(df).items() if y in gdp}
    })

    payload = {
        "kpi_id": "tax_burden",
        "kpi_name": "Tax Burden",
        "description": (
            "Total tax revenue of general government, including social security "
            "contributions, as % of GDP (OECD Revenue Statistics)."
        ),
        "unit": "percent",
        "source": (
            "OCDE — Revenue Statistics (DF_RSOECD), recettes fiscales totales en % du PIB"
            "; PIB nominal : INSEE BDM (CNA-2020-PIB)" + PER_CAPITA_SOURCE
        ),
        "methodology": (
            "Recettes fiscales totales de l'ensemble des administrations publiques "
            "(impôts et cotisations sociales effectives) en % du PIB, selon la "
            "définition harmonisée de l'OCDE (Revenue Statistics). Ce taux diffère "
            "légèrement du taux de prélèvements obligatoires publié par l'INSEE et "
            "de l'agrégat d'Eurostat (périmètre des cotisations imputées, impôts "
            "versés à l'Union européenne, impôts dus mais non recouvrés) : une "
            "seule définition est utilisée ici, pour la France comme pour les pays "
            "comparés. Pays comparés : Allemagne, Espagne, Italie, Pays-Bas, "
            "Royaume-Uni et Suède. La « moyenne OCDE » (clé OECD_REP) est la "
            "moyenne des pays membres publiée par l'OCDE (« OECD average »)."
            " Montant en euros (pour la vue par habitant) : taux de l'OCDE × PIB "
            "nominal publié par l'INSEE ; l'OCDE ne fournit ici que le taux, et "
            "son PIB de référence peut différer très légèrement du dernier PIB "
            "publié par l'INSEE."
            + per_capita_note(per_capita["base_year"])
        ),
        "last_updated": now_iso(),
        "france": france,
        "per_capita": per_capita,
        "peers": peers,
        "latest": build_latest(france),
        "context": build_context(france, peers),
    }
    write_output("kpi_tax_burden.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = compute_tax_burden()
    print(f"Tax burden: {len(r['france'])} France points; latest {r['latest']}")
