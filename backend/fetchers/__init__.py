import json
import logging
from datetime import date
from pathlib import Path

import requests

from config import RAW_DATA_DIR

log = logging.getLogger(__name__)


def save_raw(source: str, data) -> Path:
    """Write a fetcher's raw response to data/raw/{source}_{YYYY-MM-DD}.json."""
    raw_dir = Path(RAW_DATA_DIR)
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{source}_{date.today().isoformat()}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    log.info(f"Saved raw {source} response to {path}")
    return path


def fetch_ods_records(base: str, dataset_id: str, page_size: int = 100) -> list:
    """
    Fetch every record from an OpenDataSoft Explore API v2.1 dataset,
    paginating until all records are retrieved. page_size 100 is the ODS max.
    """
    url = f"{base}/{dataset_id}/records"
    all_records = []
    offset = 0
    while True:
        params = {"limit": page_size, "offset": offset, "timezone": "UTC"}
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        records = data.get("results", [])
        all_records.extend(records)
        total = data.get("total_count", 0)
        offset += page_size
        if not records or offset >= total:
            break
    return all_records
