"""
KPI: Public/Private Wage Bill Ratio — realizes PRD §1.2's public-vs-private
framing. Public sector compensation of employees (INSEE D1_S13) as a percentage
of the private-sector wage bill (Urssaf masse salariale, seasonally adjusted).
France-only; the PRD names no peer source.
"""

import json
import logging

import pandas as pd

from processors import (
    annual_values,
    build_latest,
    latest_raw,
    load_insee_series,
    now_iso,
    write_output,
)

log = logging.getLogger(__name__)

# INSEE CNT-2020-CSI values are in MILLIONS of euros; Urssaf masse salariale is
# in ABSOLUTE euros. Scale the public wage bill by this factor before ratioing.
INSEE_MILLIONS_TO_EUR = 1_000_000


def _private_wage_bill_annual() -> dict[int, float]:
    """Annual private-sector wage bill (EUR) = sum of 4 quarterly CVS values."""
    path = latest_raw("urssaf")
    if path is None:
        raise FileNotFoundError("No data/raw/urssaf_*.json — run the Urssaf fetcher first.")
    df = pd.DataFrame(json.loads(path.read_text()))
    df["annee"] = df["annee"].astype(int)
    counts = df.groupby("annee").size()
    complete = counts[counts == 4].index
    agg = df[df["annee"].isin(complete)].groupby("annee")["ms_t_60j_cvs"].sum()
    return {int(y): float(v) for y, v in agg.items()}


def compute_wage_ratio() -> dict:
    """Compute the Public/Private Wage Bill Ratio and write kpi_wage_ratio.json."""
    public = annual_values(load_insee_series()["wage_bill_apu"])  # millions of EUR
    private = _private_wage_bill_annual()  # absolute EUR

    france = [
        {"year": y, "value": round(public[y] * INSEE_MILLIONS_TO_EUR / private[y] * 100, 2)}
        for y in sorted(set(public) & set(private))
        if private[y]
    ]

    payload = {
        "kpi_id": "wage_ratio",
        "kpi_name": "Public / Private Wage Bill Ratio",
        "description": (
            "Public-sector compensation of employees as a percentage of the "
            "private-sector wage bill. A rising ratio means the public payroll "
            "is growing relative to the market economy that funds it."
        ),
        "unit": "percent",
        "source": "INSEE BDM CNT-2020-CSI (D1_S13) + Urssaf masse salariale (CVS)",
        "methodology": (
            "D1_S13 (public compensation of employees, annual) / private-sector "
            "wage bill (Urssaf ms_t_60j_cvs, seasonally adjusted, summed over 4 "
            "quarters) × 100. INSEE CNT-2020-CSI is in millions of euros while "
            "Urssaf is in absolute euros, so the public figure is scaled by 1e6 "
            "to match units. Years with fewer than 4 Urssaf quarters are dropped."
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": {},
        "latest": build_latest(france),
    }
    write_output("kpi_wage_ratio.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = compute_wage_ratio()
    print(f"\nWage ratio: {len(r['france'])} France points; latest: {r['latest']}")
