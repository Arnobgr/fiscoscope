import io
import logging

import pandas as pd
import requests

from fetchers import DEFAULT_HEADERS, save_raw

log = logging.getLogger(__name__)

DATAGOUV_API = "https://www.data.gouv.fr/api/1"
# "Allocataires de l'assurance chômage" — re-published by France Travail
# (ex-Pôle Emploi / ex-Unédic) as XLSX-only.
DATASET_ID = "561fa8bbc751df54a1cdbb48"
# "Brut France" sheet = France métropolitaine et Dom, données brutes, total
# indemnisés ventilés par allocation. Header is in row index 5 (0-indexed):
# row 3 carries top-level groupings (AC, ETAT, FORMATION, ...), row 4 is
# blank, row 5 carries the individual allocation columns, data starts row 6.
NATIONAL_SHEET = "Brut France"
HEADER_ROW = 5


def _resolve_xlsx_url() -> str:
    meta = requests.get(
        f"{DATAGOUV_API}/datasets/{DATASET_ID}/", headers=DEFAULT_HEADERS, timeout=30
    )
    meta.raise_for_status()
    resources = meta.json().get("resources", [])
    xlsx = next(
        (r for r in resources
         if (r.get("format") or "").lower() in ("xlsx", "excel")
         and "indem" in (r.get("url") or "").lower()
         and "region" not in (r.get("title") or "").lower()),
        None,
    )
    if not xlsx:
        raise ValueError(
            "No national XLSX resource found for France Travail dataset "
            f"{DATASET_ID}. Available formats: "
            f"{[r.get('format') for r in resources]}"
        )
    return xlsx["url"]


def fetch_unedic_allocataires() -> pd.DataFrame:
    """
    Fetch the monthly France Travail (ex-Unédic) national allocataires series.
    Returns the wide 'Brut France' sheet: one row per month, one column per
    allocation type (~48 columns) with the first column 'date'.
    """
    url = _resolve_xlsx_url()
    log.info(f"Downloading France Travail XLSX from {url}")
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=180, allow_redirects=True)
    resp.raise_for_status()

    df = pd.read_excel(
        io.BytesIO(resp.content),
        engine="openpyxl",
        sheet_name=NATIONAL_SHEET,
        header=HEADER_ROW,
    )
    df = df.rename(columns={df.columns[0]: "date"})
    df = df.dropna(subset=["date"])
    save_raw("france_travail_allocataires", df.to_dict(orient="records"))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    df = fetch_unedic_allocataires()
    print(f"\nFrance Travail allocataires: {len(df)} rows, {df.shape[1]} columns")
    print(df.head())
