import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import RAW_DATA_DIR, OUTPUT_DATA_DIR

log = logging.getLogger(__name__)


def now_iso() -> str:
    """Current UTC timestamp, second precision, e.g. 2026-05-01T06:00:00Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_year(date_str) -> int:
    """Extract the calendar year from a BDM time-period id ('1995' or '2026-01')."""
    return int(str(date_str)[:4])


def latest_raw(source: str) -> Path | None:
    """Return the most recent data/raw/{source}_*.json path, or None if absent."""
    matches = sorted(Path(RAW_DATA_DIR).glob(f"{source}_*.json"))
    return matches[-1] if matches else None


def load_insee_series() -> dict[str, pd.DataFrame]:
    """
    Rebuild the logical_name -> DataFrame(date, value) mapping from the cached
    INSEE BDM raw response, without re-fetching. Reads the latest
    data/raw/insee_bdm_*.json and data/raw/insee_idbanks.json.
    """
    from fetchers.insee_bdm import _parse_sdmx_json

    raw_path = latest_raw("insee_bdm")
    if raw_path is None:
        raise FileNotFoundError(
            "No data/raw/insee_bdm_*.json found — run the INSEE fetcher first."
        )
    idbank_path = Path(RAW_DATA_DIR) / "insee_idbanks.json"
    if not idbank_path.exists():
        raise FileNotFoundError(
            "No data/raw/insee_idbanks.json found — run the idBank resolver first."
        )

    df = _parse_sdmx_json(json.loads(raw_path.read_text()), [])
    idbanks = json.loads(idbank_path.read_text())
    reverse = {v: k for k, v in idbanks.items()}
    df["series_name"] = df["idbank"].map(reverse)
    return {
        name: df[df["series_name"] == name][["date", "value"]].reset_index(drop=True)
        for name in idbanks
    }


def annual_values(df: pd.DataFrame) -> dict[int, float]:
    """Collapse a (date, value) DataFrame to a {year: value} dict, dropping nulls."""
    return {
        to_year(row.date): float(row.value)
        for row in df.itertuples()
        if pd.notna(row.value)
    }


def build_latest(france: list[dict]) -> dict | None:
    """Build the §5.1 'latest' block from the France series (peers omitted)."""
    if not france:
        return None
    last = france[-1]
    latest = {"year": last["year"], "value": last["value"]}
    if len(france) > 1:
        latest["yoy_change"] = round(last["value"] - france[-2]["value"], 2)
    return latest


def write_output(filename: str, payload: dict) -> Path:
    """Write a KPI payload to data/output/{filename} as indented JSON."""
    out_dir = Path(OUTPUT_DATA_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    log.info(f"Wrote {filename} ({len(payload.get('france', []))} France data points)")
    return path
