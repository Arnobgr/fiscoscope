import logging

import pandas as pd

from fetchers import fetch_ods_records, save_raw

log = logging.getLogger(__name__)
BASE = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets"
MONTHLY_DATASET = "situations-mensuelles-budgetaires-series-longues"


def fetch_monthly_execution() -> pd.DataFrame:
    """
    Fetch the long-series monthly budget execution dataset (2013–present),
    paginating through all records. Saves the raw response before returning.
    """
    log.info(f"Fetching monthly budget execution: {MONTHLY_DATASET}")
    records = fetch_ods_records(BASE, MONTHLY_DATASET)
    save_raw("budget_execution", records)
    return pd.DataFrame(records)


def fetch_plrg_execution(year: int) -> pd.DataFrame:
    """
    Fetch the annual final budget execution (PLRG) for a given year.

    As of Session 7d the ODS publishes only a PDF "notice explicative" under each
    PLRG dataset (slug varies: `plrg-2024`, `projet-de-loi-...-plrg-2025`, …);
    the CSV/Excel mission-program-title breakdown is no longer offered. Until a
    tabular republish appears (or a PDF parser is written), raise
    NotImplementedError so the orchestrator marks this step `skipped` — matching
    the tax_expenditure convention. No KPI processor currently consumes PLRG.
    """
    raise NotImplementedError(
        f"PLRG {year} datasets on data.economie.gouv.fr now contain only a PDF "
        "notice; the tabular export was discontinued. Re-enable when a CSV/Excel "
        "resource reappears."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    df = fetch_monthly_execution()
    print(f"\nMonthly execution: {len(df)} rows, {df.shape[1]} columns")
    print(df.head())
