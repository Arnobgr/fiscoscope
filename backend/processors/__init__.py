import json
import logging
import re
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


_ANNUAL_DATE_RE = re.compile(r"^\d{4}$")
_QUARTERLY_DATE_RE = re.compile(r"^\d{4}-Q[1-4]$")


def annual_values(df: pd.DataFrame) -> dict[int, float]:
    """
    Collapse a (date, value) DataFrame to a {year: value} dict, dropping nulls.

    Accepts two BDM period formats:
      - Annual ('YYYY'): one observation per year, passed through.
      - Quarterly ('YYYY-QN'): 4 observations per year summed into the annual
        total; years with fewer than 4 quarters are dropped.

    Raises ValueError for unrecognized period formats (e.g. monthly 'YYYY-MM').
    """
    tmp = df.dropna(subset=["value"])
    if tmp.empty:
        return {}
    dates = tmp["date"].astype(str)
    if dates.str.match(_ANNUAL_DATE_RE).all():
        return {to_year(d): float(v) for d, v in zip(tmp["date"], tmp["value"])}
    if dates.str.match(_QUARTERLY_DATE_RE).all():
        tmp = tmp.assign(year=dates.map(to_year))
        counts = tmp.groupby("year").size()
        complete = counts[counts == 4].index
        agg = tmp[tmp["year"].isin(complete)].groupby("year")["value"].sum()
        return {int(y): float(v) for y, v in agg.items()}
    raise ValueError(
        f"annual_values: unrecognized date format. Sample dates: "
        f"{sorted(set(dates))[:3]}. Expected 'YYYY' or 'YYYY-QN'."
    )


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


def year_end_value(df: pd.DataFrame) -> dict[int, float]:
    """
    Collapse a quarterly (date, value) DataFrame to {year: Q4_value} — the
    correct annual figure for a STOCK (e.g. outstanding debt). Years without a
    Q4 observation are dropped. Annual ('YYYY') input passes through unchanged.
    """
    tmp = df.dropna(subset=["value"])
    if tmp.empty:
        return {}
    dates = tmp["date"].astype(str)
    if dates.str.match(_ANNUAL_DATE_RE).all():
        return {to_year(d): float(v) for d, v in zip(tmp["date"], tmp["value"])}
    q4 = tmp[dates.str.endswith("-Q4")]
    return {to_year(d): float(v) for d, v in zip(q4["date"], q4["value"])}


OECD_PEERS = ["DEU", "GBR", "ITA", "ESP", "NLD", "SWE"]
OECD_AVG_KEY = "OECD_AVG"


def load_oecd_long(source: str) -> pd.DataFrame:
    """
    Load the most recent data/raw/{source}_*.json into a long DataFrame with
    columns: country, year, value, plus any of transaction/expenditure/measure/
    unit_measure that are present (lower-cased). value is numeric; nulls dropped.
    """
    path = latest_raw(source)
    if path is None:
        raise FileNotFoundError(f"No data/raw/{source}_*.json found — run its fetcher first.")
    df = pd.DataFrame(json.loads(path.read_text()))
    rename = {"REF_AREA": "country", "TIME_PERIOD": "year", "OBS_VALUE": "value"}
    for opt in ("TRANSACTION", "EXPENDITURE", "MEASURE", "UNIT_MEASURE"):
        if opt in df.columns:
            rename[opt] = opt.lower()
    out = df[list(rename)].rename(columns=rename)
    out["year"] = out["year"].astype(int)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    return out.dropna(subset=["value"])


def peer_series(df: pd.DataFrame) -> dict:
    """
    Turn a long DataFrame (columns: country, year, value) into the §5.1 `peers`
    block: {country_code: [{year, value}, ...], "OECD_AVG": [...]}. France is
    excluded from both the per-country output and the average. OECD_AVG is the
    unweighted per-year mean across whatever peer countries are present.
    """
    sub = df[df["country"].isin(OECD_PEERS)]
    out = {}
    for country, g in sub.groupby("country"):
        rows = g.sort_values("year")
        out[country] = [
            {"year": int(r.year), "value": round(float(r.value), 2)} for r in rows.itertuples()
        ]
    avg = sub.groupby("year")["value"].mean().sort_index()
    out[OECD_AVG_KEY] = [{"year": int(y), "value": round(float(v), 2)} for y, v in avg.items()]
    return out
