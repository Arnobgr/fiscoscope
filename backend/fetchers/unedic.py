import logging
from io import StringIO

import pandas as pd
import requests

from fetchers import DEFAULT_HEADERS, save_raw

log = logging.getLogger(__name__)
DATAGOUV_API = "https://www.data.gouv.fr/api/1"


def fetch_unedic_allocataires() -> pd.DataFrame:
    """
    Fetch monthly Unédic unemployment insurance data from data.gouv.fr.
    Resolves the current CSV resource URL dynamically via the catalog API,
    since the resource URL changes occasionally.
    """
    search_url = f"{DATAGOUV_API}/datasets/"
    params = {"q": "unedic allocataires assurance chomage mensuel", "page_size": 5}
    response = requests.get(search_url, params=params, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()

    datasets = response.json().get("data", [])
    if not datasets:
        raise ValueError("Unédic dataset not found on data.gouv.fr")

    dataset_id = datasets[0]["id"]
    log.info(f"Resolved Unédic dataset: {datasets[0].get('title')} ({dataset_id})")
    dataset_url = f"{DATAGOUV_API}/datasets/{dataset_id}/"
    resources = requests.get(dataset_url, headers=DEFAULT_HEADERS, timeout=30).json().get("resources", [])

    csv_resource = next(
        (r for r in resources if (r.get("format") or "").lower() == "csv"), None
    )
    if not csv_resource:
        raise ValueError("No CSV resource found for Unédic dataset")

    response = requests.get(csv_resource["url"], headers=DEFAULT_HEADERS, timeout=60)
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text), sep=";", encoding="utf-8")
    save_raw("unedic", df.to_dict(orient="records"))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    df = fetch_unedic_allocataires()
    print(f"\nUnédic allocataires: {len(df)} rows, {df.shape[1]} columns")
    print(df.head())
