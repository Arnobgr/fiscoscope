# PRD — French Administration Efficiency Dashboard
## Product Requirements Document — v1.0

---

## 1. Project Overview

### 1.1 Goal

Build an open-source, automatically updated dashboard that measures the **productivity and efficiency of the French public administration** using publicly available fiscal data.

The framing is deliberately first-principles: instead of presenting accounting data the way the government does (e.g. "we spent €X on education"), the dashboard computes **efficiency ratios** — for every euro taxed, how much reaches productive use vs. being consumed by administrative overhead? How does France compare to peers? How have these ratios evolved over 30 years?

The target audience is citizens, journalists, and researchers who want a clear, independent, data-driven view of public finance performance — without institutional framing.

### 1.2 Philosophy

- **Ratio-focused, not accounting-focused.** The question is not "how much did we spend" but "what did each euro produce."
- **Longitudinal by default.** Every KPI should be shown over time (ideally 1995–present) to reveal trends, not just snapshots.
- **Peer-benchmarked.** France's numbers are only meaningful relative to comparable countries (Germany, UK, Italy, Spain, OECD average).
- **Fully automated.** No manual data entry. The pipeline fetches from public APIs, computes KPIs, and publishes JSON files on a cron schedule.
- **Independent.** No institutional affiliation. The code and methodology are fully open-source.

### 1.3 Project Name

`fisc-o-scope` (working title, can be changed)

---

## 2. Architecture

### 2.1 High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      VPS (Hetzner)                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Python data pipeline (cron-scheduled)               │  │
│  │  - Fetches raw data from public APIs                 │  │
│  │  - Normalizes and stores raw data locally            │  │
│  │  - Computes KPIs                                     │  │
│  │  - Writes output JSON files                          │  │
│  │  - Uploads JSON to Cloudflare R2                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ rclone / boto3 upload
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Cloudflare R2 (object storage)                 │
│  Public bucket — free tier                                  │
│  URL pattern: https://pub-{hash}.r2.dev/{filename}.json     │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ fetch() at page load
                          ▼
┌─────────────────────────────────────────────────────────────┐
│         Cloudflare Pages (frontend — Phase 2)               │
│         Vite + React + Recharts                             │
│         Static site, deployed from GitHub                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 No Backend API Required

There is **no FastAPI or HTTP server** in v1. The VPS runs only a Python cron job. The frontend fetches pre-computed static JSON files directly from R2. This makes the system:
- Cheaper (no always-on process beyond the cron job)
- More resilient (no server to go down)
- Faster for users (static files served from Cloudflare edge)

A FastAPI layer can be added in a future version if interactive server-side queries are needed.

### 2.3 Backend Directory Structure

```
fisc-o-scope/
├── backend/
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── insee_idbank_resolver.py  # Downloads mapping CSV, resolves idBanks — runs first
│   │   ├── insee_bdm.py              # INSEE BDM SDMX API (reads idBanks from resolver output)
│   │   ├── budget_execution.py       # data.economie.gouv.fr monthly execution
│   │   ├── oecd.py                   # OECD Data Explorer SDMX API
│   │   ├── urssaf.py                 # open.urssaf.fr OpenDataSoft API
│   │   └── unedic.py                 # Unédic unemployment data
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── cofog.py             # COFOG classification and spend bucketing
│   │   ├── kpi_overhead.py      # Administrative Overhead Rate
│   │   ├── kpi_friction.py      # Friction Ratio
│   │   ├── kpi_allocation.py    # Productive Spend Ratio, Pension/Investment
│   │   ├── kpi_outcomes.py      # Spend vs. outcome KPIs
│   │   ├── kpi_sustainability.py # Deficit trend, Debt-Adjusted Return
│   │   └── kpi_monthly.py       # Monthly execution KPIs
│   ├── publishers/
│   │   ├── __init__.py
│   │   └── r2_upload.py         # Upload JSON output files to Cloudflare R2
│   ├── data/
│   │   ├── raw/                 # Raw API responses, cached locally
│   │   └── output/              # Final JSON files before upload
│   │       ├── meta.json
│   │       ├── kpi_overhead_rate.json
│   │       ├── kpi_friction_ratio.json
│   │       ├── kpi_productive_spend.json
│   │       ├── kpi_pension_investment.json
│   │       ├── kpi_monthly_execution.json
│   │       ├── kpi_outcomes.json
│   │       ├── kpi_sustainability.json
│   │       └── kpi_tax_expenditure.json
│   ├── config.py                # All configuration constants and API endpoints
│   ├── run_pipeline.py          # Main entry point: orchestrates all steps
│   └── requirements.txt
├── frontend/                    # Phase 2 — Vite + React app (not in scope now)
├── .env                         # Secrets: R2 credentials
├── README.md
└── PRD.md
```

### 2.4 Scheduling

The pipeline runs via a `systemd` timer on the VPS. Two schedules:
- **Monthly** (1st of each month, 06:00): fetches budget execution, Urssaf, Unédic, CPI
- **Annual** (February 1st): fetches INSEE COFOG national accounts, OECD data, PLF annexes (published ~May, so a second annual run in June)

```ini
# /etc/systemd/system/fisoscope-monthly.timer
[Timer]
OnCalendar=*-*-01 06:00:00
Persistent=true

# /etc/systemd/system/fisoscope-annual.timer
[Timer]
OnCalendar=*-02-01 06:00:00
Persistent=true
```

---

## 3. Data Sources

### 3.1 INSEE BDM — Banque de Données Macroéconomiques

**What it provides:** National accounts time series including COFOG expenditure by function, public sector wage bill, revenues, GDP, CPI. Historical depth from 1978 (some series from 1995).

**API:** REST/SDMX, no authentication, no API key required.

**Base URL:** `https://api.insee.fr/series/BDM/V1/data/SERIES_BDM/{idbanks}`

---

#### 3.1.1 idBank Discovery — Programmatic Approach

The BDM API identifies every series by a 9-digit `idBank`. INSEE publishes a complete flat mapping file — `correspondance_idbank_dimension.csv` — that lists every series with its dimensions (operation code, sector code, unit, frequency, etc.). This file is updated continuously and is the authoritative source for idBank lookup.

**The pipeline must run `fetchers/insee_idbank_resolver.py` as its very first step**, before any data is fetched. This script downloads the mapping file, filters it for the series needed by this project, and writes the resolved idBanks to `data/raw/insee_idbanks.json`. All subsequent INSEE fetchers read from that file rather than hardcoding idBanks.

```python
# fetchers/insee_idbank_resolver.py

import requests
import pandas as pd
import json
import logging
from pathlib import Path
from config import RAW_DATA_DIR

log = logging.getLogger(__name__)

MAPPING_URL = "https://www.insee.fr/fr/statistiques/fichier/2862759/correspondance_idbank_dimension.csv"

# Search terms for each series we need.
# Each entry is: logical_name -> list of (column, value) filters that must ALL match.
# Column names are from the INSEE mapping file header — verify on first run.
# Key dimension codes follow the ESA 2010 national accounts nomenclature:
#   OPERATION: D1=compensation of employees, P51=gross fixed capital formation,
#              D62=social benefits in cash, B9=net lending/borrowing, D41=interest
#   SECT_INST: S13=all APU, S1311=central govt, S1313=local govt, S1314=social security
#   UNITE: Milliards d'euros courants (current prices, billions EUR)
#   FREQ: A=annual, M=monthly, T=quarterly
SERIES_SEARCH_RULES = {
    # --- APU aggregate accounts ---
    "wage_bill_apu": [
        ("OPERATION", "D1"),
        ("SECT_INST", "S13"),
        ("FREQ", "A"),
    ],
    "wage_bill_central": [
        ("OPERATION", "D1"),
        ("SECT_INST", "S1311"),
        ("FREQ", "A"),
    ],
    "public_investment": [
        ("OPERATION", "P51"),
        ("SECT_INST", "S13"),
        ("FREQ", "A"),
    ],
    "social_benefits": [
        ("OPERATION", "D62"),
        ("SECT_INST", "S13"),
        ("FREQ", "A"),
    ],
    "fiscal_balance": [
        ("OPERATION", "B9"),
        ("SECT_INST", "S13"),
        ("FREQ", "A"),
    ],
    "debt_interest": [
        ("OPERATION", "D41"),
        ("SECT_INST", "S13"),
        ("FREQ", "A"),
    ],
    "total_apu_expenditure": [
        ("OPERATION", "TE"),       # Total expenditure — verify exact code in mapping file
        ("SECT_INST", "S13"),
        ("FREQ", "A"),
    ],
    # --- GDP and prices ---
    "gdp_nominal": [
        ("OPERATION", "PIB"),      # Verify exact code
        ("FREQ", "A"),
    ],
    "cpi": [
        ("OPERATION", "IPC"),      # Indice des Prix à la Consommation — verify
        ("FREQ", "M"),
    ],
    # --- COFOG functions (APU total, annual, current prices) ---
    # COFOG dimension name in the mapping file may be "FONCTION" or "COFOG" — verify on first run
    "cofog_gf01": [("COFOG", "GF01"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf02": [("COFOG", "GF02"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf03": [("COFOG", "GF03"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf04": [("COFOG", "GF04"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf05": [("COFOG", "GF05"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf06": [("COFOG", "GF06"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf07": [("COFOG", "GF07"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf08": [("COFOG", "GF08"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf09": [("COFOG", "GF09"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf10": [("COFOG", "GF10"), ("SECT_INST", "S13"), ("FREQ", "A")],
}


def download_mapping(force_refresh: bool = False) -> pd.DataFrame:
    """
    Download the INSEE BDM idBank mapping file and return as a DataFrame.
    Cached locally as data/raw/insee_idbank_mapping.csv.
    Re-downloads if the file is older than 30 days or force_refresh=True.
    """
    cache_path = Path(RAW_DATA_DIR) / "insee_idbank_mapping.csv"
    
    if not force_refresh and cache_path.exists():
        age_days = (pd.Timestamp.now() - pd.Timestamp(cache_path.stat().st_mtime, unit="s")).days
        if age_days < 30:
            log.info(f"Using cached idBank mapping ({age_days}d old)")
            return pd.read_csv(cache_path, sep=";", dtype=str, low_memory=False)
    
    log.info("Downloading INSEE idBank mapping file...")
    response = requests.get(MAPPING_URL, timeout=120)
    response.raise_for_status()
    
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(response.content)
    log.info(f"Saved idBank mapping to {cache_path} ({len(response.content) / 1024:.0f} KB)")
    
    # Try common separators; INSEE has used both ";" and ","
    for sep in [";", ","]:
        try:
            df = pd.read_csv(cache_path, sep=sep, dtype=str, low_memory=False)
            if df.shape[1] > 3:
                log.info(f"Parsed mapping with sep='{sep}': {len(df)} rows, {df.shape[1]} columns")
                log.info(f"Columns: {list(df.columns)}")
                return df
        except Exception:
            continue
    raise ValueError("Could not parse INSEE idBank mapping file — check separator and encoding")


def resolve_idbanks(df: pd.DataFrame) -> dict:
    """
    Apply SERIES_SEARCH_RULES to the mapping DataFrame.
    Returns a dict of logical_name -> idBank string.
    Raises a detailed error for any series that cannot be resolved or is ambiguous.
    """
    resolved = {}
    errors = []

    for name, filters in SERIES_SEARCH_RULES.items():
        mask = pd.Series([True] * len(df), index=df.index)
        for col, val in filters:
            if col not in df.columns:
                errors.append(
                    f"[{name}] Column '{col}' not found in mapping. "
                    f"Available columns: {list(df.columns)}"
                )
                mask = pd.Series([False] * len(df), index=df.index)
                break
            mask &= df[col].str.upper().str.strip() == val.upper().strip()

        matches = df[mask]

        if len(matches) == 0:
            errors.append(
                f"[{name}] No series found for filters: {filters}. "
                f"Check dimension codes against mapping file columns."
            )
        elif len(matches) > 1:
            # Try to narrow: prefer rows where UNITE contains "milliard" (billions EUR)
            narrow = matches[
                matches.get("UNITE", pd.Series(dtype=str))
                .str.lower()
                .str.contains("milliard", na=False)
            ]
            if len(narrow) == 1:
                matches = narrow
            else:
                idbanks = matches["idbank"].tolist() if "idbank" in matches.columns else matches.iloc[:, 0].tolist()
                errors.append(
                    f"[{name}] Ambiguous: {len(matches)} series match filters {filters}. "
                    f"Candidate idBanks: {idbanks[:5]}. Refine filters in SERIES_SEARCH_RULES."
                )
                continue

        idbank_col = "idbank" if "idbank" in matches.columns else matches.columns[0]
        resolved[name] = str(matches.iloc[0][idbank_col]).strip()
        log.info(f"Resolved [{name}] -> {resolved[name]}")

    if errors:
        error_msg = "\n".join(errors)
        raise RuntimeError(
            f"idBank resolution failed for {len(errors)} series:\n{error_msg}\n\n"
            f"ACTION REQUIRED: Inspect data/raw/insee_idbank_mapping.csv, "
            f"find the correct column names and dimension codes, "
            f"and update SERIES_SEARCH_RULES in this file."
        )

    return resolved


def run_idbank_resolver(force_refresh: bool = False) -> dict:
    """
    Main entry point. Downloads mapping, resolves idBanks, writes to
    data/raw/insee_idbanks.json, and returns the resolved dict.
    """
    df = download_mapping(force_refresh=force_refresh)
    resolved = resolve_idbanks(df)

    output_path = Path(RAW_DATA_DIR) / "insee_idbanks.json"
    output_path.write_text(json.dumps(resolved, indent=2, ensure_ascii=False))
    log.info(f"Wrote {len(resolved)} resolved idBanks to {output_path}")

    return resolved


if __name__ == "__main__":
    # Run standalone to verify resolution before running the full pipeline
    import logging
    logging.basicConfig(level=logging.INFO)
    result = run_idbank_resolver(force_refresh=True)
    print("\nResolved idBanks:")
    for k, v in result.items():
        print(f"  {k}: {v}")
```

**Important notes on column names:** The exact column names in `correspondance_idbank_dimension.csv` are only known at runtime. On first run, the script logs all available columns. Common names seen in INSEE documentation include `IDBANK`, `OPERATION`, `SECT_INST`, `COFOG`, `FREQ`, `UNITE`, `TITRE`. If the resolver raises a "Column not found" error, inspect the cached CSV and update `SERIES_SEARCH_RULES` column names accordingly — this is a one-time adjustment.

---

#### 3.1.2 Fetching Series Data

Once idBanks are resolved, fetching is straightforward:

```python
# fetchers/insee_bdm.py

import requests
import pandas as pd
import json
import logging
from pathlib import Path
from config import RAW_DATA_DIR, INSEE_START_YEAR
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
    Fetch one or more BDM time series by idBank list.
    Returns a DataFrame with columns: idbank, date, value.
    """
    ids = "+".join(idbanks)
    url = f"{BDM_BASE}/{ids}"
    params = {"startPeriod": str(start_year), "format": "sdmx-json"}
    headers = {"Accept": "application/json"}

    response = requests.get(url, params=params, headers=headers, timeout=60)
    response.raise_for_status()
    return _parse_sdmx_json(response.json(), idbanks)


def fetch_all_insee_series() -> dict[str, pd.DataFrame]:
    """
    Fetch all series needed for KPI computation.
    Returns a dict of logical_name -> DataFrame.
    Saves each raw response to data/raw/insee_{name}_{date}.json.
    """
    idbanks = load_idbanks()
    results = {}

    # Fetch in batches of up to 400 (BDM API limit)
    items = list(idbanks.items())
    batch_size = 50  # conservative batch to avoid oversized responses
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        names = [n for n, _ in batch]
        ids = [v for _, v in batch]
        log.info(f"Fetching INSEE batch {i//batch_size + 1}: {names}")
        df = fetch_insee_series(ids)
        # Map idBank back to logical name
        reverse = {v: k for k, v in idbanks.items()}
        df["series_name"] = df["idbank"].map(reverse)
        for name in names:
            results[name] = df[df["series_name"] == name][["date", "value"]].copy()

    return results


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
        raise ValueError(f"Unexpected SDMX-JSON structure: {e}. Response keys: {list(data.keys())}")

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
```

**Update frequency:** Annual (national accounts published May–June each year). CPI is monthly.

---

### 3.2 data.economie.gouv.fr — Monthly Budget Execution

**What it provides:** Monthly cumulative budget execution for the French state: tax revenues by category (TVA, IR, IS, TICPE, other), spending by mission and program, fiscal balance. Covers 2013–present.

**API:** OpenDataSoft REST API v2, no authentication required.

**Base URL:** `https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/`

**Key datasets:**
- `situations-mensuelles-budgetaires-series-longues` — Long series of monthly execution (2013–present), the primary dataset
- `projet-de-loi-relatif-aux-resultats-de-la-gestion-et-portant-approbation-des-comptes-de-lannee-plrg-{year}` — Annual final execution by mission/program/title/category

**How to fetch:**

```python
import requests
import pandas as pd

BASE = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets"

def fetch_monthly_execution(limit: int = 1000) -> pd.DataFrame:
    """
    Fetch the long-series monthly budget execution dataset.
    Paginates automatically if more than `limit` records.
    """
    dataset_id = "situations-mensuelles-budgetaires-series-longues"
    url = f"{BASE}/{dataset_id}/records"
    
    all_records = []
    offset = 0
    
    while True:
        params = {
            "limit": limit,
            "offset": offset,
            "timezone": "UTC"
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        records = data.get("results", [])
        all_records.extend(records)
        
        total = data.get("total_count", 0)
        offset += limit
        if offset >= total:
            break
    
    return pd.DataFrame(all_records)


def fetch_plrg_execution(year: int) -> pd.DataFrame:
    """
    Fetch the annual final budget execution (PLRG) for a given year.
    Returns spending by mission, program, title, category.
    """
    dataset_id = f"projet-de-loi-relatif-aux-resultats-de-la-gestion-{year}"
    # The exact dataset ID varies per year — verify on data.economie.gouv.fr
    url = f"{BASE}/{dataset_id}/exports/csv"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    from io import StringIO
    return pd.read_csv(StringIO(response.text), sep=";", encoding="utf-8")
```

**Update frequency:** Monthly (within ~30 days of month end).

---

### 3.3 OECD Data Explorer — Cross-Country Benchmarks

**What it provides:** COFOG expenditure as % of GDP across all OECD countries, fiscal balance, public employment, trust indicators. Enables peer comparison (France vs. Germany, UK, Italy, Spain, OECD average).

**API:** SDMX REST, no authentication required. Rate limit: 20 requests/minute.

**Base URL:** `https://sdmx.oecd.org/public/rest/data/`

**Key datasets:**

| Dataset ID | Description |
|---|---|
| `OECD.GOV.GIP,DSD_GOV_COFOG@DF_GOV_COFOG_2025` | Expenditure by COFOG function, % GDP, all OECD countries |
| `OECD.GOV.GIP,DSD_GOV_TRANSACTION@DF_GOV_TRANSACTION_2025` | Public finance main indicators (deficit, debt, revenue) |

**How to fetch:**

```python
import requests
import pandas as pd
from io import StringIO

OECD_BASE = "https://sdmx.oecd.org/public/rest/data"

def fetch_oecd_cofog(countries: list[str] = None, start_year: int = 2000) -> pd.DataFrame:
    """
    Fetch COFOG expenditure by function as % of GDP from OECD.
    countries: list of ISO-2 codes, e.g. ['FRA', 'DEU', 'GBR', 'ITA', 'ESP']
               If None, fetches all OECD countries.
    """
    if countries is None:
        country_filter = ""
    else:
        country_filter = "+".join(countries)
    
    dataset = "OECD.GOV.GIP,DSD_GOV_COFOG@DF_GOV_COFOG_2025"
    # Filter: frequency=Annual, countries, all COFOG functions, % of GDP
    filter_expr = f"A.{country_filter}..PT_GDP."
    
    url = f"{OECD_BASE}/{dataset}/{filter_expr}"
    params = {
        "startPeriod": str(start_year),
        "format": "csvfilewithlabels"
    }
    
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


def fetch_oecd_fiscal(countries: list[str] = None, start_year: int = 1995) -> pd.DataFrame:
    """
    Fetch fiscal balance, revenue, expenditure as % of GDP from OECD.
    """
    if countries is None:
        country_filter = ""
    else:
        country_filter = "+".join(countries)
    
    dataset = "OECD.GOV.GIP,DSD_GOV_TRANSACTION@DF_GOV_TRANSACTION_2025"
    filter_expr = f"A.{country_filter}..."
    
    url = f"{OECD_BASE}/{dataset}/{filter_expr}"
    params = {
        "startPeriod": str(start_year),
        "format": "csvfilewithlabels"
    }
    
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))
```

**Countries to always fetch:** `['FRA', 'DEU', 'GBR', 'ITA', 'ESP', 'NLD', 'SWE', 'OECD']`

**Update frequency:** Annual (Government at a Glance, published June each year, data updated continuously on the Explorer).

---

### 3.4 open.urssaf.fr — Private Sector Wage Bill

**What it provides:** Quarterly private sector wage bill and headcount. Enables computation of the public/private wage bill ratio.

**API:** OpenDataSoft REST API v2, no authentication required.

**Base URL:** `https://open.urssaf.fr/api/explore/v2.1/catalog/datasets/`

**Key dataset:** `masse-salariale-du-secteur-prive-france-entiere`

**How to fetch:**

```python
def fetch_urssaf_wage_bill() -> pd.DataFrame:
    """
    Fetch quarterly private sector wage bill series (France-wide).
    Returns both early estimate and stabilized estimate.
    """
    base = "https://open.urssaf.fr/api/explore/v2.1/catalog/datasets"
    dataset_id = "masse-salariale-du-secteur-prive-france-entiere"
    url = f"{base}/{dataset_id}/records"
    
    response = requests.get(url, params={"limit": 200, "timezone": "UTC"}, timeout=30)
    response.raise_for_status()
    return pd.DataFrame(response.json().get("results", []))
```

**Update frequency:** Quarterly, ~50 days after quarter end.

---

### 3.5 data.gouv.fr — Unédic Unemployment Insurance

**What it provides:** Monthly count of unemployment insurance recipients (allocataires), total indemnification cost, entries and exits. Useful as a social protection efficiency signal.

**API:** CKAN REST API (data.gouv.fr catalog), then direct CSV download.

**Dataset slug:** Search for "unedic allocataires" on data.gouv.fr to get the current dataset ID and resource URL. The resource URL changes occasionally — always resolve it programmatically.

**How to fetch:**

```python
DATAGOUV_API = "https://www.data.gouv.fr/api/1"

def fetch_unedic_allocataires() -> pd.DataFrame:
    """
    Fetch monthly Unédic unemployment insurance data from data.gouv.fr.
    Resolves the current CSV resource URL dynamically via the catalog API.
    """
    # Search for the dataset
    search_url = f"{DATAGOUV_API}/datasets/"
    params = {"q": "unedic allocataires assurance chomage mensuel", "page_size": 5}
    response = requests.get(search_url, params=params, timeout=30)
    response.raise_for_status()
    
    datasets = response.json().get("data", [])
    if not datasets:
        raise ValueError("Unédic dataset not found on data.gouv.fr")
    
    # Get resources from the first matching dataset
    dataset_id = datasets[0]["id"]
    dataset_url = f"{DATAGOUV_API}/datasets/{dataset_id}/"
    resources = requests.get(dataset_url, timeout=30).json().get("resources", [])
    
    # Find the CSV resource
    csv_resource = next((r for r in resources if r["format"].lower() == "csv"), None)
    if not csv_resource:
        raise ValueError("No CSV resource found for Unédic dataset")
    
    csv_url = csv_resource["url"]
    response = requests.get(csv_url, timeout=60)
    response.raise_for_status()
    
    from io import StringIO
    return pd.read_csv(StringIO(response.text), sep=";", encoding="utf-8")
```

**Update frequency:** Monthly.

---

### 3.6 data.economie.gouv.fr — PLF Tax Expenditure Annex

**What it provides:** Annual count and estimated cost of all tax expenditures (niches fiscales) by tax category. Needed for the Tax Expenditure Cost KPI.

**Access:** The PLF budget datasets are published annually on data.economie.gouv.fr and data.gouv.fr. Search for "PLF {year} voies et moyens" or "dépenses fiscales" to find the current CSV.

**How to fetch:** Same pattern as the PLRG fetcher above — search data.gouv.fr catalog API for "depenses fiscales PLF", resolve the CSV resource URL, download.

**Update frequency:** Annual (September–October, when the PLF is tabled in Parliament).

---

## 4. COFOG Classification — Spend Bucketing

The COFOG taxonomy groups government expenditure into 10 top-level functions. For the efficiency KPIs, these must be mapped into three buckets:

```python
# config.py

COFOG_PRODUCTIVE = [
    "GF04",  # Economic affairs (infrastructure, transport, energy, R&D)
    "GF05",  # Environmental protection
    "GF06",  # Housing and community amenities
    "GF09",  # Education (investment component)
]

COFOG_REDISTRIBUTIVE = [
    "GF07",  # Health
    "GF08",  # Recreation, culture, religion
    "GF09",  # Education (transfer component)
    "GF10",  # Social protection (pensions, unemployment, family)
]

COFOG_ADMINISTRATIVE = [
    "GF01",  # General public services (includes debt interest)
    "GF02",  # Defence
    "GF03",  # Public order and safety
]
```

**Important caveat:** Education (GF09) and Health (GF07) contain both investment (productive) and transfer (redistributive) components. The national accounts split these differently depending on the year and base. The processor should flag this ambiguity in the output metadata and use the following rule: classify the full COFOG function based on its dominant component, but note that the classification is an approximation.

This bucketing is not pre-computed by any official source — it is the **core intellectual value-add** of this dashboard. Document the methodology clearly in the output JSON and in the README.

---

## 5. KPI Specifications

Each KPI processor reads from the raw/processed data and outputs a standardized JSON structure. All values are in either **billions of euros** (absolute) or **percentages** (ratios). All series are **annual** unless explicitly noted as monthly.

### 5.1 Standard Output JSON Schema

```json
{
  "kpi_id": "overhead_rate",
  "kpi_name": "Administrative Overhead Rate",
  "description": "Public sector wage bill as % of total public expenditure. Measures how much of every euro spent goes to running the administrative apparatus rather than delivering services or transfers.",
  "unit": "percent",
  "source": "INSEE BDM — Comptes des APU",
  "methodology": "D1_S13 (compensation of employees, all APU) / total APU expenditure. Based on national accounts base 2020.",
  "last_updated": "2026-05-01T06:00:00Z",
  "france": [
    { "year": 1995, "value": 19.2 },
    { "year": 1996, "value": 19.5 }
  ],
  "peers": {
    "DEU": [{ "year": 2000, "value": 17.1 }],
    "GBR": [{ "year": 2000, "value": 16.8 }],
    "ITA": [{ "year": 2000, "value": 22.1 }],
    "ESP": [{ "year": 2000, "value": 21.0 }],
    "OECD_AVG": [{ "year": 2000, "value": 18.4 }]
  },
  "latest": {
    "year": 2024,
    "value": 23.1,
    "yoy_change": 0.2,
    "vs_oecd_avg": 4.7
  }
}
```

---

### 5.2 KPI: Administrative Overhead Rate

**File:** `kpi_overhead_rate.json`

**Formula:** `Public sector wage bill (D1_S13) / Total APU expenditure × 100`

**Sources:** INSEE BDM (D1_S13, total APU expenditure), OECD for peer comparison.

**Interpretation:** Higher = more of each tax euro consumed by the state apparatus itself. France's trend has been rising since the 1990s.

**Processor:** `processors/kpi_overhead.py`

---

### 5.3 KPI: Friction Ratio

**File:** `kpi_friction_ratio.json`

**Formula:** `(Total taxes collected − Value reaching end beneficiary) / Total taxes collected × 100`

**"Value reaching end beneficiary"** is approximated as: social benefits paid (D62_S13) + public investment (P51_S13) + education and health service delivery. Administrative expenditure (COFOG GF01 + GF02 + GF03) and debt interest are treated as friction.

**Sources:** INSEE BDM (COFOG functions, APU accounts).

**Note:** This is an approximation. The methodology and its limitations must be documented in the output JSON's `methodology` field.

**Processor:** `processors/kpi_friction.py`

---

### 5.4 KPI: Productive Spend Ratio

**File:** `kpi_productive_spend.json`

**Formula:** `COFOG_PRODUCTIVE bucket / Total APU expenditure × 100`

**Sources:** INSEE BDM COFOG tables 3.301–3.307.

**Historical depth:** 1995–present.

**Processor:** `processors/kpi_allocation.py`

---

### 5.5 KPI: Pension / Investment Ratio

**File:** `kpi_pension_investment.json`

**Formula:** `Social protection expenditure (COFOG GF10) / Gross fixed capital formation (P51_S13)`

**Sources:** INSEE BDM.

**Interpretation:** This ratio measures intergenerational resource allocation. A rising ratio means the state increasingly consumes its own productive capacity. France: approximately 5:1 as of 2024.

**Processor:** `processors/kpi_allocation.py`

---

### 5.6 KPI: Monthly Budget Execution

**File:** `kpi_monthly_execution.json`

**This is the only monthly-cadence KPI file.** Updated each month.

**Contents:**
- Tax revenues by category (TVA, IR, IS, TICPE, other) — cumulated from Jan 1 of current year
- Spending by major mission — cumulated from Jan 1
- Running fiscal balance
- Year-on-year comparison (same month previous year)

**Formula:** Direct from the situations mensuelles data — no transformation needed, just normalization and reshaping.

**Sources:** data.economie.gouv.fr situations mensuelles budgétaires.

**Output structure:**

```json
{
  "kpi_id": "monthly_execution",
  "year": 2026,
  "last_month": "2026-04",
  "last_updated": "2026-05-01T06:00:00Z",
  "revenues": {
    "months": ["2026-01", "2026-02", "2026-03", "2026-04"],
    "TVA": [24.1, 23.8, 25.2, 26.1],
    "IR": [8.2, 7.9, 8.5, 9.1],
    "IS": [3.1, 2.8, 3.4, 3.9],
    "total": [38.6, 37.2, 40.1, 42.3]
  },
  "spending": {
    "months": ["2026-01", "2026-02", "2026-03", "2026-04"],
    "total": [65.0, 63.2, 67.1, 68.4]
  },
  "balance": {
    "months": ["2026-01", "2026-02", "2026-03", "2026-04"],
    "cumulative": [-26.4, -52.4, -79.4, -105.5]
  },
  "yoy": {
    "revenue_change_pct": 3.2,
    "spending_change_pct": 1.8
  }
}
```

**Processor:** `processors/kpi_monthly.py`

---

### 5.7 KPI: Fiscal Deficit Trend

**File:** `kpi_sustainability.json`

**Contents:**
- France fiscal balance as % of GDP, 1995–present
- Peer countries same series
- Public debt as % of GDP, France and peers

**Formula:** Direct from OECD fiscal data (B9_S13 / PIB). Cross-check with INSEE BDM.

**Sources:** OECD Data Explorer (`DF_GOV_TRANSACTION_2025`), INSEE BDM for France detail.

**Processor:** `processors/kpi_sustainability.py`

---

### 5.8 KPI: Tax Expenditure Cost

**File:** `kpi_tax_expenditure.json`

**Formula:** `Total cost of niches fiscales / Total tax revenues × 100`

**Contents:** Count of tax expenditures, total cost in €Bn, ratio to total revenues, year-over-year trend.

**Sources:** PLF annexes on data.gouv.fr.

**Processor:** `processors/kpi_outcomes.py`

---

### 5.9 KPI: Spend vs. Outcome Ratios

**File:** `kpi_outcomes.json`

**Contents (all indexed to OECD average = 100 for comparability):**
- Health: Assurance Maladie spend per capita vs. life expectancy, France and peers
- Education: spend per pupil vs. PISA scores, France and peers

**Sources:** OECD Data Explorer (health expenditure, life expectancy, PISA datasets), INSEE COFOG for France spend detail.

**Note:** PISA data is triennial (2000, 2003, 2006... 2022). Interpolate linearly between available years for display purposes and mark interpolated values in the output.

**Processor:** `processors/kpi_outcomes.py`

---

## 6. Main Pipeline Orchestration

### 6.1 `run_pipeline.py`

This is the entry point called by the systemd timer. It:
1. Determines which fetchers to run based on the schedule (monthly vs. annual)
2. Calls each fetcher and caches raw data to `data/raw/`
3. Calls each processor which reads from `data/raw/` and writes to `data/output/`
4. Writes `data/output/meta.json` with pipeline run metadata
5. Calls the R2 uploader to sync all files in `data/output/` to the R2 bucket

```python
# run_pipeline.py

import argparse
import logging
from datetime import datetime

from fetchers.insee_bdm import fetch_all_insee_series
from fetchers.budget_execution import fetch_monthly_execution, fetch_plrg_execution
from fetchers.oecd import fetch_oecd_cofog, fetch_oecd_fiscal
from fetchers.urssaf import fetch_urssaf_wage_bill
from fetchers.unedic import fetch_unedic_allocataires
from processors.kpi_overhead import compute_overhead_rate
from processors.kpi_friction import compute_friction_ratio
from processors.kpi_allocation import compute_productive_spend, compute_pension_investment
from processors.kpi_monthly import compute_monthly_execution
from processors.kpi_sustainability import compute_fiscal_sustainability
from processors.kpi_outcomes import compute_outcomes, compute_tax_expenditure
from publishers.r2_upload import upload_all_outputs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

def run_monthly():
    """Run monthly pipeline: budget execution, CPI, Urssaf, Unédic."""
    log.info("Starting monthly pipeline run")
    fetch_monthly_execution()
    fetch_urssaf_wage_bill()
    fetch_unedic_allocataires()
    compute_monthly_execution()
    upload_all_outputs(prefix="monthly")

def run_annual():
    """Run annual pipeline: INSEE COFOG, OECD, PLRG, all structural KPIs."""
    log.info("Starting annual pipeline run")
    # Step 0: resolve INSEE idBanks from the official mapping file (cached 30 days)
    from fetchers.insee_idbank_resolver import run_idbank_resolver
    run_idbank_resolver()
    fetch_all_insee_series()
    fetch_oecd_cofog()
    fetch_oecd_fiscal()
    fetch_plrg_execution(year=datetime.now().year - 1)
    compute_overhead_rate()
    compute_friction_ratio()
    compute_productive_spend()
    compute_pension_investment()
    compute_fiscal_sustainability()
    compute_outcomes()
    compute_tax_expenditure()
    upload_all_outputs(prefix="annual")

def run_full():
    """Run both monthly and annual pipelines. Used for initial setup."""
    run_annual()
    run_monthly()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["monthly", "annual", "full"], default="full")
    args = parser.parse_args()
    
    if args.mode == "monthly":
        run_monthly()
    elif args.mode == "annual":
        run_annual()
    else:
        run_full()
    
    log.info("Pipeline complete")
```

---

## 7. Configuration

### 7.1 `config.py`

```python
# config.py

# INSEE BDM series idBanks are NOT hardcoded here.
# They are resolved automatically at pipeline startup by fetchers/insee_idbank_resolver.py,
# which downloads INSEE's official mapping file and writes the resolved idBanks to
# data/raw/insee_idbanks.json. All INSEE fetchers load from that file.
#
# The logical series names used throughout the pipeline are:
#   wage_bill_apu, wage_bill_central, public_investment, social_benefits,
#   fiscal_balance, debt_interest, total_apu_expenditure, gdp_nominal, cpi,
#   cofog_gf01 through cofog_gf10
#
# To inspect or debug resolved idBanks, run standalone:
#   python -m fetchers.insee_idbank_resolver

# OECD
OECD_COUNTRIES = ["FRA", "DEU", "GBR", "ITA", "ESP", "NLD", "SWE"]
OECD_START_YEAR = 2000

# INSEE start year for COFOG (available from 1995)
INSEE_START_YEAR = 1995

# Data paths
RAW_DATA_DIR = "data/raw"
OUTPUT_DATA_DIR = "data/output"

# Cloudflare R2 (loaded from environment)
import os
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "")  # e.g. https://pub-xxx.r2.dev

# COFOG bucket classification
COFOG_PRODUCTIVE = ["cofog_gf04", "cofog_gf05", "cofog_gf06"]
COFOG_REDISTRIBUTIVE = ["cofog_gf07", "cofog_gf08", "cofog_gf09", "cofog_gf10"]
COFOG_ADMINISTRATIVE = ["cofog_gf01", "cofog_gf02", "cofog_gf03"]
```

### 7.2 `.env` (never commit to git)

```
R2_BUCKET_NAME=fisoscope-data
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_PUBLIC_URL=https://pub-yourhash.r2.dev
```

---

## 8. R2 Upload

### 8.1 `publishers/r2_upload.py`

```python
import boto3
import json
import os
import logging
from pathlib import Path
from config import (
    OUTPUT_DATA_DIR, R2_BUCKET_NAME, R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
)

log = logging.getLogger(__name__)

def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto"
    )

def upload_all_outputs(prefix: str = ""):
    """Upload all JSON files from the output directory to R2."""
    client = get_r2_client()
    output_dir = Path(OUTPUT_DATA_DIR)
    
    for json_file in output_dir.glob("*.json"):
        key = json_file.name
        log.info(f"Uploading {key} to R2")
        client.upload_file(
            str(json_file),
            R2_BUCKET_NAME,
            key,
            ExtraArgs={
                "ContentType": "application/json",
                "CacheControl": "public, max-age=3600"
            }
        )
        log.info(f"Uploaded {key}")
```

---

## 9. `meta.json` — Pipeline Metadata

Written at the end of every pipeline run. The frontend uses this to display data freshness.

```json
{
  "last_run": "2026-05-01T06:12:43Z",
  "pipeline_version": "1.0.0",
  "sources": {
    "insee_bdm": {
      "last_fetched": "2026-05-01T06:00:12Z",
      "latest_year": 2024,
      "status": "ok"
    },
    "budget_execution": {
      "last_fetched": "2026-05-01T06:01:03Z",
      "latest_month": "2026-03",
      "status": "ok"
    },
    "oecd": {
      "last_fetched": "2026-05-01T06:03:22Z",
      "latest_year": 2023,
      "status": "ok"
    },
    "urssaf": {
      "last_fetched": "2026-05-01T06:05:01Z",
      "latest_quarter": "2025-Q4",
      "status": "ok"
    },
    "unedic": {
      "last_fetched": "2026-05-01T06:06:44Z",
      "latest_month": "2026-02",
      "status": "ok"
    }
  },
  "output_files": [
    "meta.json",
    "kpi_overhead_rate.json",
    "kpi_friction_ratio.json",
    "kpi_productive_spend.json",
    "kpi_pension_investment.json",
    "kpi_monthly_execution.json",
    "kpi_sustainability.json",
    "kpi_tax_expenditure.json",
    "kpi_outcomes.json"
  ]
}
```

---

## 10. Requirements

### 10.1 `requirements.txt`

```
requests>=2.31.0
pandas>=2.0.0
boto3>=1.34.0
python-dotenv>=1.0.0
```

Note: `pandasdmx` is not required. The INSEE SDMX-JSON responses are parsed directly with the `_parse_sdmx_json` function in `fetchers/insee_bdm.py`. The OECD fetcher requests CSV format directly (`format=csvfilewithlabels`), parsed with `pandas.read_csv`.

### 10.2 Python Version

Python 3.11+

---

## 11. Development Phases

### Phase 1 — Backend (current scope)
- [ ] Set up project structure
- [ ] Implement `fetchers/insee_idbank_resolver.py` and verify it resolves all series correctly against the live mapping file
- [ ] Implement all remaining fetchers with error handling and local caching
- [ ] Implement all KPI processors
- [ ] Implement R2 uploader
- [ ] Implement `run_pipeline.py` orchestrator
- [ ] Run `python -m fetchers.insee_idbank_resolver` standalone to validate idBank resolution before running the full pipeline
- [ ] Test full pipeline run locally with `python run_pipeline.py --mode full`
- [ ] Set up systemd timers on VPS
- [ ] Verify all JSON output files are well-formed and complete

### Phase 2 — Frontend (out of scope for this document)
- Vite + React + Recharts
- Fetches JSON from R2 `pub-xxx.r2.dev` URLs
- KPI cards with sparklines (latest value, YoY change, vs. OECD average)
- Time series charts per KPI with peer country overlays
- "Last updated" badge from `meta.json`
- Deployed to Cloudflare Pages from GitHub

---

## 12. Key Constraints and Notes

1. **idBank resolution is fully automated but requires runtime validation.** The resolver downloads INSEE's `correspondance_idbank_dimension.csv` (the authoritative mapping of all ~150,000 BDM series), filters it using dimension codes defined in `SERIES_SEARCH_RULES`, and caches the resolved idBanks in `data/raw/insee_idbanks.json`. On first run, inspect the logged column names from the mapping file — if any filter raises "Column not found", update the column names in `SERIES_SEARCH_RULES` to match the actual CSV header. The mapping file's column names have historically been stable but are only confirmed at runtime. Run `python -m fetchers.insee_idbank_resolver` standalone before the full pipeline to catch any resolution errors early.

2. **OECD dataset IDs change with each Government at a Glance edition.** The dataset IDs in this PRD reference the 2025 edition. When the 2027 edition is published, the IDs will need to be updated. The fetcher should log the dataset ID used in each run.

3. **Raw data must be cached locally.** Every fetcher must save its raw API response to `data/raw/{source}_{date}.json` before processing. This ensures the pipeline can be re-run without re-fetching if processing fails, and provides an audit trail.

4. **All KPI computations must be reproducible from raw data.** The processor scripts must be deterministic: same raw data → same output JSON, always.

5. **COFOG base changes.** INSEE revised its national accounts base in 2020 (previously base 2014). The COFOG series may have a structural break around 2020. The processor should detect and flag this in the output metadata if the series has inconsistent methodology across years.

6. **No secrets in code or git.** All R2 credentials are loaded from environment variables via `.env`. The `.env` file must be in `.gitignore`.
