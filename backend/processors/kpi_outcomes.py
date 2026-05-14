"""
KPI: Spend vs. Outcome Ratios (PRD §5.9) and Tax Expenditure Cost (PRD §5.8).

Both KPIs depend on data sources not yet wired up:

  - Spend vs. Outcome needs OECD health/education spend, life expectancy and
    PISA series. The outcome side and all peer benchmarking are OECD-sourced;
    per the Session 4 decision (see Runtime discoveries in CLAUDE.md), OECD
    wiring is deferred to Session 7. compute_outcomes() emits a well-formed
    placeholder so the pipeline stays runnable until then.

  - Tax Expenditure needs the PLF "dépenses fiscales" annex (PRD §3.6), for
    which no fetcher module exists yet. compute_tax_expenditure() raises
    NotImplementedError until that fetcher is built.
"""

import logging

from processors import now_iso, write_output

log = logging.getLogger(__name__)


def compute_outcomes() -> dict:
    """
    Write a placeholder kpi_outcomes.json.

    The outcome series (life expectancy, PISA) and peer benchmarking are
    OECD-sourced and deferred to Session 7; france and peers are populated once
    the OECD fetcher's live column layout is confirmed.
    """
    payload = {
        "kpi_id": "outcomes",
        "kpi_name": "Spend vs. Outcome Ratios",
        "description": (
            "Health spend per capita vs. life expectancy and education spend "
            "per pupil vs. PISA scores, indexed to the OECD average."
        ),
        "unit": "index",
        "source": "OECD Data Explorer — health expenditure, life expectancy, PISA",
        "methodology": (
            "Deferred to Session 7: the outcome series (life expectancy, PISA) "
            "and peer benchmarking are OECD-sourced and require live column "
            "layouts to be confirmed before wiring up. PISA is triennial and "
            'will be linearly interpolated between survey years, with '
            'interpolated points marked "interpolated": true.'
        ),
        "last_updated": now_iso(),
        "france": [],
        "peers": {},
        "latest": None,
    }
    write_output("kpi_outcomes.json", payload)
    return payload


def compute_tax_expenditure() -> dict:
    """
    Compute the Tax Expenditure Cost KPI and write kpi_tax_expenditure.json.

    Blocked: this KPI needs the PLF "dépenses fiscales" annex, for which no
    fetcher module exists yet. Build a PLF fetcher (PRD §3.6) before
    implementing this processor.
    """
    raise NotImplementedError(
        "compute_tax_expenditure requires a PLF 'dépenses fiscales' fetcher "
        "(PRD §3.6), which does not exist yet — see Session 5 notes in CLAUDE.md."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = compute_outcomes()
    print(f"\nOutcomes: {len(result['france'])} France data points (placeholder)")
