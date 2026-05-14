import logging
import time
from io import StringIO

import pandas as pd
import requests

from config import OECD_COUNTRIES, OECD_START_YEAR
from fetchers import save_raw

log = logging.getLogger(__name__)
OECD_BASE = "https://sdmx.oecd.org/public/rest/data"

# Dataset IDs reference the 2025 Government at a Glance edition — update when 2027 ships.
COFOG_DATASET = "OECD.GOV.GIP,DSD_GOV_COFOG@DF_GOV_COFOG_2025"
FISCAL_DATASET = "OECD.GOV.GIP,DSD_GOV_TRANSACTION@DF_GOV_TRANSACTION_2025"

# OECD rate limit is 20 requests/minute — pause between calls.
RATE_LIMIT_SLEEP = 3


def _fetch_oecd_csv(dataset: str, filter_expr: str, start_year: int) -> pd.DataFrame:
    """Fetch a single OECD SDMX dataset slice as CSV, respecting the rate limit."""
    url = f"{OECD_BASE}/{dataset}/{filter_expr}"
    params = {"startPeriod": str(start_year), "format": "csvfilewithlabels"}
    log.info(f"Fetching OECD dataset {dataset} (filter: {filter_expr})")
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    time.sleep(RATE_LIMIT_SLEEP)
    return pd.read_csv(StringIO(response.text))


def fetch_oecd_cofog(countries: list[str] = None, start_year: int = OECD_START_YEAR) -> pd.DataFrame:
    """Fetch COFOG expenditure by function as % of GDP for the peer countries."""
    countries = countries or OECD_COUNTRIES
    filter_expr = f"A.{'+'.join(countries)}..PT_GDP."
    df = _fetch_oecd_csv(COFOG_DATASET, filter_expr, start_year)
    save_raw("oecd_cofog", df.to_dict(orient="records"))
    return df


def fetch_oecd_fiscal(countries: list[str] = None, start_year: int = OECD_START_YEAR) -> pd.DataFrame:
    """Fetch fiscal balance, revenue and expenditure indicators for the peer countries."""
    countries = countries or OECD_COUNTRIES
    filter_expr = f"A.{'+'.join(countries)}..."
    df = _fetch_oecd_csv(FISCAL_DATASET, filter_expr, start_year)
    save_raw("oecd_fiscal", df.to_dict(orient="records"))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cofog = fetch_oecd_cofog()
    print(f"\nOECD COFOG: {len(cofog)} rows, {cofog.shape[1]} columns")
    fiscal = fetch_oecd_fiscal()
    print(f"OECD fiscal: {len(fiscal)} rows, {fiscal.shape[1]} columns")
