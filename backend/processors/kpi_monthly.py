"""
KPI: Monthly Budget Execution — see PRD §5.6.

Reshapes the cached data.economie.gouv.fr "situations mensuelles budgétaires —
séries longues" dataset into cumulative monthly revenue / spending / balance
series for the most recent year, plus a year-on-year comparison.

The values in that dataset are already cumulated from January 1 (PRD §5.6), so
this processor only normalises and reshapes — it does not re-cumulate.

The OpenDataSoft field names for this dataset are only confirmed at runtime.
The candidate lists below cover the expected names; if none match,
`_resolve_column` raises a detailed error listing the columns actually present
(same pattern as the INSEE idBank resolver).
"""

import json
import logging

import pandas as pd

from processors import latest_raw, now_iso, write_output

log = logging.getLogger(__name__)

# Candidate OpenDataSoft field names — verify on first live run and adjust if
# _resolve_column raises "no column found".
DATE_FIELDS = ["date", "mois", "periode", "date_mois", "annee_mois"]
LABEL_FIELDS = ["libelle", "indicateur", "intitule", "libelle_poste", "poste"]
VALUE_FIELDS = ["valeur", "montant", "value"]

# Label substrings (case-insensitive) used to classify each row.
REVENUE_CATEGORIES = {
    "TVA": ["tva", "valeur ajout"],
    "IR": ["impot sur le revenu", "impôt sur le revenu"],
    "IS": ["impot sur les societes", "impôt sur les sociétés"],
}
REVENUE_TOTAL_KEYS = ["total des recettes", "recettes totales", "recettes nettes"]
SPENDING_TOTAL_KEYS = ["total des depenses", "total des dépenses", "depenses nettes", "dépenses nettes"]


def _resolve_column(columns: set, candidates: list[str], role: str) -> str:
    """Return the first candidate present in `columns`, else raise a detailed error."""
    for name in candidates:
        if name in columns:
            return name
    raise RuntimeError(
        f"Monthly execution: no '{role}' column found. Tried {candidates}; "
        f"available columns: {sorted(columns)}. Update the *_FIELDS lists in "
        f"processors/kpi_monthly.py to match the dataset."
    )


def _matches(label, keys: list[str]) -> bool:
    low = str(label).lower()
    return any(k in low for k in keys)


def _monthly_series(frame: pd.DataFrame, months: list[str], keys: list[str]) -> list[float]:
    """Cumulative value per month for rows whose label matches `keys`."""
    sel = frame[frame["label"].apply(lambda l: _matches(l, keys))]
    by_month = sel.groupby("month")["value"].sum()
    return [round(float(by_month.get(m, 0.0)), 2) for m in months]


def compute_monthly_execution() -> dict:
    """Compute the Monthly Budget Execution KPI and write kpi_monthly_execution.json."""
    raw_path = latest_raw("budget_execution")
    if raw_path is None:
        raise FileNotFoundError(
            "No data/raw/budget_execution_*.json found — run the budget "
            "execution fetcher first."
        )
    records = json.loads(raw_path.read_text())
    df = pd.DataFrame(records)
    if df.empty:
        raise ValueError(f"{raw_path} contains no records")

    cols = set(df.columns)
    date_col = _resolve_column(cols, DATE_FIELDS, "date")
    label_col = _resolve_column(cols, LABEL_FIELDS, "label")
    value_col = _resolve_column(cols, VALUE_FIELDS, "value")

    df = df[[date_col, label_col, value_col]].copy()
    df.columns = ["month", "label", "value"]
    df["month"] = df["month"].astype(str).str.slice(0, 7)  # YYYY-MM
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    df["year"] = df["month"].str.slice(0, 4).astype(int)

    latest_year = int(df["year"].max())
    current = df[df["year"] == latest_year]
    previous = df[df["year"] == latest_year - 1]
    months = sorted(current["month"].unique())
    if not months:
        raise ValueError(f"No monthly rows for {latest_year} in {raw_path}")
    last_month = months[-1]
    prev_same_month = f"{latest_year - 1}-{last_month[5:]}"

    revenues = {"months": months}
    for key, terms in REVENUE_CATEGORIES.items():
        revenues[key] = _monthly_series(current, months, terms)
    revenues["total"] = _monthly_series(current, months, REVENUE_TOTAL_KEYS)

    spending_total = _monthly_series(current, months, SPENDING_TOTAL_KEYS)
    balance_cumulative = [
        round(rev - spend, 2) for rev, spend in zip(revenues["total"], spending_total)
    ]

    def _total_at(frame, month, keys):
        sel = frame[
            (frame["month"] == month) & frame["label"].apply(lambda l: _matches(l, keys))
        ]
        return float(sel["value"].sum())

    def _yoy(keys):
        prev_val = _total_at(previous, prev_same_month, keys)
        cur_val = _total_at(current, last_month, keys)
        if not prev_val:
            return None
        return round((cur_val - prev_val) / prev_val * 100, 2)

    payload = {
        "kpi_id": "monthly_execution",
        "year": latest_year,
        "last_month": last_month,
        "last_updated": now_iso(),
        "revenues": revenues,
        "spending": {"months": months, "total": spending_total},
        "balance": {"months": months, "cumulative": balance_cumulative},
        "yoy": {
            "revenue_change_pct": _yoy(REVENUE_TOTAL_KEYS),
            "spending_change_pct": _yoy(SPENDING_TOTAL_KEYS),
        },
    }
    write_output("kpi_monthly_execution.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = compute_monthly_execution()
    print(
        f"\nMonthly execution: year {result['year']}, "
        f"{len(result['revenues']['months'])} months through {result['last_month']}"
    )
