import json
import logging
from pathlib import Path

import pandas as pd
import requests

from config import RAW_DATA_DIR, INSEE_START_YEAR
from fetchers import save_raw
from fetchers.insee_idbank_resolver import run_idbank_resolver

log = logging.getLogger(__name__)
BDM_BASE = "https://api.insee.fr/series/BDM/V1/data/SERIES_BDM"


def load_idbanks() -> dict:
    """Load resolved idBanks from cache, re-resolving if not found."""
    idbank_path = Path(RAW_DATA_DIR) / "insee_idbanks.json"
    if not idbank_path.exists():
        log.info("idBanks not cached — running resolver")
        return run_idbank_resolver()
    return json.loads(idbank_path.read_text())


def fetch_insee_series(idbanks: list[str], start_year: int = INSEE_START_YEAR) -> pd.DataFrame:
    """
    Fetch one or more BDM time series by idBank list (BDM API limit: 400 per call).
    Saves the raw SDMX-JSON response, then returns a DataFrame with columns:
    idbank, date, value.
    """
    ids = "+".join(idbanks)
    url = f"{BDM_BASE}/{ids}"
    params = {"startPeriod": str(start_year), "format": "sdmx-json"}
    headers = {"Accept": "application/json"}

    response = requests.get(url, params=params, headers=headers, timeout=60)
    response.raise_for_status()
    raw = response.json()
    save_raw("insee_bdm", raw)
    return _parse_sdmx_json(raw, idbanks)


def fetch_all_insee_series() -> dict[str, pd.DataFrame]:
    """
    Fetch every series needed for KPI computation in a single batched call
    (~27 series, well under the 400-idBank BDM limit).
    Returns a dict of logical_name -> DataFrame with columns: date, value.
    """
    idbanks = load_idbanks()
    df = fetch_insee_series(list(idbanks.values()))

    reverse = {v: k for k, v in idbanks.items()}
    df["series_name"] = df["idbank"].map(reverse)
    return {
        name: df[df["series_name"] == name][["date", "value"]].reset_index(drop=True)
        for name in idbanks
    }


def _parse_sdmx_json(data: dict, requested_idbanks: list[str]) -> pd.DataFrame:
    """Parse INSEE SDMX-JSON response into a flat DataFrame."""
    try:
        series_data = data["dataSets"][0]["series"]
        structure = data["structure"]
        time_periods = [
            obs["id"]
            for obs in structure["dimensions"]["observation"][0]["values"]
        ]
        idbank_values = [
            v["id"]
            for v in structure["dimensions"]["series"][0]["values"]
        ]
    except (KeyError, IndexError) as e:
        raise ValueError(
            f"Unexpected SDMX-JSON structure: {e}. Response keys: {list(data.keys())}"
        )

    rows = []
    for series_key, series_values in series_data.items():
        series_idx = int(series_key.split(":")[0])
        idbank = idbank_values[series_idx] if series_idx < len(idbank_values) else series_key
        for obs_key, obs_values in series_values["observations"].items():
            idx = int(obs_key)
            rows.append({
                "idbank": idbank,
                "date": time_periods[idx],
                "value": float(obs_values[0]) if obs_values[0] is not None else None,
            })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    series = fetch_all_insee_series()
    print(f"\nFetched {len(series)} INSEE series:")
    for name, df in series.items():
        print(f"  {name}: {len(df)} rows")
