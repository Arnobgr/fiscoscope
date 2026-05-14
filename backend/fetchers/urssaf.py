import logging

import pandas as pd

from fetchers import fetch_ods_records, save_raw

log = logging.getLogger(__name__)
BASE = "https://open.urssaf.fr/api/explore/v2.1/catalog/datasets"
DATASET_ID = "masse-salariale-du-secteur-prive-france-entiere"


def fetch_urssaf_wage_bill() -> pd.DataFrame:
    """
    Fetch the quarterly private-sector wage bill series (France-wide),
    paginating through all records. Saves the raw response before returning.
    """
    log.info(f"Fetching Urssaf private wage bill: {DATASET_ID}")
    records = fetch_ods_records(BASE, DATASET_ID)
    save_raw("urssaf", records)
    return pd.DataFrame(records)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    df = fetch_urssaf_wage_bill()
    print(f"\nUrssaf wage bill: {len(df)} rows, {df.shape[1]} columns")
    print(df.head())
