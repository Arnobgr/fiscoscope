import logging
from io import StringIO

import pandas as pd
import requests

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
    Fetch the annual final budget execution (PLRG) for a given year:
    spending by mission, program, title, category.
    """
    dataset_id = f"projet-de-loi-relatif-aux-resultats-de-la-gestion-{year}"
    url = f"{BASE}/{dataset_id}/exports/csv"
    log.info(f"Fetching PLRG execution: {dataset_id}")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text), sep=";", encoding="utf-8")
    save_raw(f"budget_plrg_{year}", df.to_dict(orient="records"))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    df = fetch_monthly_execution()
    print(f"\nMonthly execution: {len(df)} rows, {df.shape[1]} columns")
    print(df.head())
