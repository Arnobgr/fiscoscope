import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

from config import RAW_DATA_DIR, INSEE_START_YEAR
from fetchers import DEFAULT_HEADERS, save_raw
from fetchers.insee_idbank_resolver import run_idbank_resolver

log = logging.getLogger(__name__)
BDM_BASE = "https://api.insee.fr/series/BDM/V1/data/SERIES_BDM"
# BDM V1 returns SDMX 2.1 StructureSpecificData XML; the JSON variant was removed.
# In that schema, <Series>/<Obs> are in the empty namespace — only message:*/ss:*
# wrapper elements use prefixed namespaces.


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
    Parses the SDMX-XML response into [{idbank, date, value}] records, saves
    those records as JSON, and returns a DataFrame with columns:
    idbank, date, value.
    """
    ids = "+".join(idbanks)
    url = f"{BDM_BASE}/{ids}"
    params = {"startPeriod": str(start_year)}

    response = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=60)
    response.raise_for_status()
    records = _parse_sdmx_xml(response.text)
    save_raw("insee_bdm", records)
    return pd.DataFrame(records)


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


def _parse_sdmx_xml(xml_text: str) -> list[dict]:
    """Parse SDMX 2.1 StructureSpecificData XML into [{idbank, date, value}]."""
    root = ET.fromstring(xml_text)
    rows = []
    for series in root.iter("Series"):
        idbank = series.attrib.get("IDBANK")
        if not idbank:
            continue
        for obs in series.iter("Obs"):
            time_period = obs.attrib.get("TIME_PERIOD")
            obs_value = obs.attrib.get("OBS_VALUE")
            if time_period is None:
                continue
            rows.append({
                "idbank": idbank,
                "date": time_period,
                "value": float(obs_value) if obs_value not in (None, "") else None,
            })
    return rows


def _parse_sdmx_json(cached, requested_idbanks: list[str] | None = None) -> pd.DataFrame:
    """
    Build a DataFrame from the cached BDM payload. After the BDM JSON variant was
    removed, the fetcher stores pre-parsed [{idbank, date, value}] records, so this
    function just wraps them. Name preserved for backward compatibility with
    processors/__init__.py::load_insee_series().
    """
    if isinstance(cached, list):
        return pd.DataFrame(cached)
    raise ValueError(
        "Cached insee_bdm payload has unexpected shape "
        f"({type(cached).__name__}); expected list of records."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    series = fetch_all_insee_series()
    print(f"\nFetched {len(series)} INSEE series:")
    for name, df in series.items():
        print(f"  {name}: {len(df)} rows")
