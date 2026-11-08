"""
Eurostat dissemination API (JSON-stat 2.0, no key) — roadmap sources S1, S2, S4.

  - gov_10a_exp   (S1): general-government expenditure by COFOG function ×
                        transaction (TE total, D1 compensation, P51G investment).
  - gov_10a_main  (S2): main aggregates by sub-sector (balance B9, revenue TR,
                        interest payable D41PAY).
  - gov_10dd_ggd  (S4): Maastricht debt by holder sector (France only — the
                        holder split starts in 2020 for France).

Each response is saved untouched (PRD §12 constraint 3); processors decode it
with decode_jsonstat(). Eurostat has no UK (post-Brexit): peers are DE/IT/ES/
NL/SE plus the EU27 aggregate.
"""

import logging

import requests

from config import INSEE_START_YEAR
from fetchers import DEFAULT_HEADERS, save_raw

log = logging.getLogger(__name__)

EUROSTAT_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
EUROSTAT_GEOS = ["FR", "DE", "IT", "ES", "NL", "SE", "EU27_2020"]
COFOG_CODES = ["TOTAL", *[f"GF{i:02d}" for i in range(1, 11)], "GF1002"]


def _fetch(dataset: str, filters: dict[str, list[str]]) -> dict:
    """GET one Eurostat dataset slice; filters become repeated query params."""
    params = [("format", "JSON"), ("sinceTimePeriod", str(INSEE_START_YEAR))]
    params += [(dim, code) for dim, codes in filters.items() for code in codes]
    log.info(f"Fetching Eurostat {dataset}")
    response = requests.get(
        f"{EUROSTAT_BASE}/{dataset}", params=params, headers=DEFAULT_HEADERS, timeout=60
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("value"):
        raise ValueError(f"Eurostat {dataset}: response has no values")
    return data


def decode_jsonstat(d: dict) -> dict[tuple, float]:
    """
    Decode a JSON-stat 2.0 dataset into {(code per dimension, ...): value}.
    Keys follow the order of d["id"], e.g. ('A','MIO_EUR','S13','GF01','D1','FR','2024').
    `value` is sparse and keyed by the flat row-major index; nulls are dropped.
    """
    dims, sizes = d["id"], d["size"]
    codes = [
        sorted(d["dimension"][k]["category"]["index"].items(), key=lambda x: x[1])
        for k in dims
    ]
    out = {}
    for flat, v in d["value"].items():
        if v is None:
            continue
        i, pos = int(flat), []
        for s in reversed(sizes):
            pos.append(i % s)
            i //= s
        pos.reverse()
        out[tuple(codes[j][p][0] for j, p in enumerate(pos))] = v
    return out


def fetch_eurostat_expenditure() -> dict:
    """S1 — expenditure by COFOG function (level 1 + GF1002 old age) × transaction."""
    data = _fetch(
        "gov_10a_exp",
        {
            "geo": EUROSTAT_GEOS,
            "sector": ["S13"],
            "unit": ["MIO_EUR", "PC_GDP"],
            "na_item": ["TE", "D1", "P51G"],
            "cofog99": COFOG_CODES,
        },
    )
    save_raw("eurostat_exp", data)
    return data


def fetch_eurostat_main() -> dict:
    """S2 — balance, revenue and interest payable, general government and sub-sectors."""
    data = _fetch(
        "gov_10a_main",
        {
            "geo": EUROSTAT_GEOS,
            "sector": ["S13", "S1311", "S1313", "S1314"],
            "unit": ["MIO_EUR", "PC_GDP"],
            "na_item": ["B9", "TR", "D41PAY"],
        },
    )
    save_raw("eurostat_main", data)
    return data


def fetch_eurostat_debt() -> dict:
    """S4 — France Maastricht debt (% of GDP) by holder: total, non-residents, central bank."""
    data = _fetch(
        "gov_10dd_ggd",
        {
            "geo": ["FR"],
            "sector": ["S13"],
            "na_item": ["GD"],
            "maturity": ["TOTAL"],
            "unit": ["PC_GDP"],
            "sector2": ["S1_S2", "S2", "S121"],
        },
    )
    save_raw("eurostat_debt", data)
    return data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for fn in (fetch_eurostat_expenditure, fetch_eurostat_main, fetch_eurostat_debt):
        print(f"{fn.__name__}: {len(fn()['value'])} values")
