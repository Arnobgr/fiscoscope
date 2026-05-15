# Upstream Data-Source Fixes Implementation Plan

> **For agentic workers:** Each session below is independent. Do **one session per
> conversation** to keep context tight. Always start by reading `CLAUDE.md` and
> this file's relevant section. Always end by updating `CLAUDE.md`'s **Runtime
> discoveries** and committing.

**Goal:** Restore the live pipeline after four upstream changes that broke it
between Sessions 2/3 and today (2026-05-15). The IP block is gone; the
fetcher *code* now needs to catch up to the new upstream formats.

**Architecture:** No new abstractions. Each session updates one fetcher in
place, keeping the existing module shape (constants, `_fetch_*`, public
function, `if __name__ == "__main__"` smoke run). Tests are the existing
`__main__` blocks plus the full pipeline at the end — matching project
convention. No pytest dependency added.

**Tech stack:** Existing — `requests==2.33.1`, `pandas==2.3.3`,
`boto3==1.43.6`, `python-dotenv==1.2.2`. Session 7c adds `openpyxl` (also
pinned).

**Shared assumptions for all sessions:**
- `backend/.venv` already exists with deps installed.
- `fetchers/__init__.py` already exposes `DEFAULT_HEADERS` (Firefox-style UA);
  reuse it for every `requests.get` call.
- Be polite: never burst more than ~1 request/second to a given host. OECD's
  20-req/min limit is enforced via `time.sleep(3)` inside `_fetch_oecd_csv`.
- Cache raw responses to `data/raw/` before parsing — never re-fetch in the
  same session.

---

## Session 7a — INSEE idBank resolver: handle ZIP + new positional schema

### Background (read this first)

The mapping URL `correspondance_idbank_dimension.csv` returns `500` because
INSEE migrated to a monthly **ZIP** archive whose filename embeds the date,
e.g. `202603_correspondance_idbank_dimension.zip`. The metadata page
`https://www.insee.fr/fr/information/2862759` lists current archive links.

The CSV inside the ZIP has a completely new schema:

```
"famille";"idbank";"list_mod";"list_var"
"CNA-2010-DEP-APU";"001728915";"A.CNA_DEP_APU.S13112.D9.VALEUR_ABSOLUE.FON035.FR-D976.EUROS_COURANTS.BRUT.2010";"PERIODICITE.INDICATEUR.SECT-INST.OPERATION.NATURE.FONCTION.ZONE_GEO.UNITE.CORRECTION.BASIND"
```

- `famille` — dataset family (e.g. `CNA-2010-DEP-APU`, `IPC-2015`, etc.)
- `idbank` — 9-digit ID
- `list_mod` — dot-separated **values**
- `list_var` — dot-separated **dimension names** (same order as `list_mod`)

To filter, zip the two lists into a per-row dict and apply rules.

The dimension *names* changed too:
- `FREQ` → `PERIODICITE` (values still `A`, `M`, ...)
- `SECT_INST` → `SECT-INST` (hyphen, not underscore)
- `COFOG` → `FONCTION` (values look like `FON01`–`FON10` or finer like
  `FON035` — confirm during step 1)
- `OPERATION` → `OPERATION` (unchanged)
- `UNITE` → `UNITE` (unchanged)

A given (OPERATION, SECT-INST, PERIODICITE) tuple can occur in multiple
families, so `famille` may need to be part of the rule set to disambiguate.

### Files
- Modify: `backend/fetchers/insee_idbank_resolver.py`
- The cached ZIP and extracted CSV are already at
  `backend/data/raw/insee_idbank_mapping.zip` and
  `backend/data/raw/insee_idbank_mapping.csv` (saved during Session 7
  exploration on 2026-05-15) — reuse them, don't re-download.

### Step 1: Inspect the new CSV to confirm the dimension vocabulary

Open `backend/data/raw/insee_idbank_mapping.csv` and answer in writing
(in a scratch comment in the module, or as a one-line summary in the commit
message):

```bash
cd backend
source .venv/bin/activate
python <<'PY'
import pandas as pd
df = pd.read_csv('data/raw/insee_idbank_mapping.csv', sep=';', dtype=str, low_memory=False)
print('rows:', len(df), 'columns:', list(df.columns))
print('famille values:', df['famille'].nunique())
print(df['famille'].value_counts().head(20))
# For one APU-related family, list distinct dimension-name sets
fam = 'CNA-2010-DEP-APU'
sub = df[df['famille']==fam]
varsets = sub['list_var'].drop_duplicates()
print(f'\n{fam}: {len(sub)} rows, {len(varsets)} distinct list_var schemas')
for v in varsets.head(3):
    print(' ', v)
# Distinct values for OPERATION and FONCTION in that family
print('\nDistinct OPERATIONs in', fam)
def dimval(row, dim):
    vars_ = row['list_var'].split('.')
    mods = row['list_mod'].split('.')
    if dim in vars_:
        return mods[vars_.index(dim)]
    return None
sub = sub.copy()
sub['op'] = sub.apply(lambda r: dimval(r, 'OPERATION'), axis=1)
sub['fonction'] = sub.apply(lambda r: dimval(r, 'FONCTION'), axis=1)
print(sorted(sub['op'].dropna().unique())[:30])
print('FONCTION:', sorted(sub['fonction'].dropna().unique())[:30])
PY
```

Expected: confirm whether `FONCTION` values are `FON01`–`FON10` (matching
COFOG) or finer-grained codes that need a prefix-match.

### Step 2: Update `MAPPING_URL` discovery to scrape the metadata page

The hardcoded `MAPPING_URL` is wrong. Replace `download_mapping()`'s
download portion with: GET the metadata HTML page, extract the *latest*
`*_correspondance_idbank_dimension.zip` link via regex, then download the
ZIP. Cache the ZIP at `data/raw/insee_idbank_mapping.zip` and the extracted
CSV at `data/raw/insee_idbank_mapping.csv` (existing cache filename).
Reuse `DEFAULT_HEADERS` plus `Referer: https://www.insee.fr/fr/information/2862759`.

Replace the top of the file:

```python
import io
import re
import zipfile
# ... existing imports ...

METADATA_URL = "https://www.insee.fr/fr/information/2862759"
ZIP_FILENAME_RE = re.compile(
    r'(/fr/statistiques/fichier/2862759/\d{6}_correspondance_idbank_dimension\.zip)'
)
```

Replace `download_mapping()`:

```python
def download_mapping(force_refresh: bool = False) -> pd.DataFrame:
    """
    Resolve the latest mapping ZIP from INSEE's metadata page, download it,
    and extract the CSV. Cached at data/raw/insee_idbank_mapping.{zip,csv}.
    Re-downloads if cache is older than 30 days or force_refresh=True.
    """
    cache_csv = Path(RAW_DATA_DIR) / "insee_idbank_mapping.csv"
    cache_zip = Path(RAW_DATA_DIR) / "insee_idbank_mapping.zip"

    if not force_refresh and cache_csv.exists():
        age_days = (pd.Timestamp.now() - pd.Timestamp(cache_csv.stat().st_mtime, unit="s")).days
        if age_days < 30:
            log.info(f"Using cached idBank mapping ({age_days}d old)")
            return _parse_mapping_csv(cache_csv)

    log.info("Resolving latest INSEE idBank mapping ZIP...")
    headers = {**DEFAULT_HEADERS, "Referer": METADATA_URL}
    meta = requests.get(METADATA_URL, headers=headers, timeout=60)
    meta.raise_for_status()
    matches = sorted(set(ZIP_FILENAME_RE.findall(meta.text)))
    if not matches:
        raise RuntimeError(
            f"No mapping ZIP link found on {METADATA_URL}. "
            "INSEE may have restructured the page; inspect the HTML manually."
        )
    zip_path_url = "https://www.insee.fr" + matches[-1]
    log.info(f"Downloading {zip_path_url}")

    cache_zip.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(zip_path_url, headers=headers, timeout=180)
    resp.raise_for_status()
    cache_zip.write_bytes(resp.content)

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
        cache_csv.write_bytes(zf.read(csv_name))
    log.info(f"Extracted {csv_name} → {cache_csv} ({cache_csv.stat().st_size / 1024 / 1024:.1f} MB)")

    return _parse_mapping_csv(cache_csv)
```

### Step 3: Update `SERIES_SEARCH_RULES` to the new dimension vocabulary

Translate every rule:
- `FREQ` → `PERIODICITE`
- `SECT_INST` → `SECT-INST`
- `COFOG` → `FONCTION` (use the value form confirmed in Step 1)

Add a `famille` filter where needed to disambiguate. Likely candidates:
- APU aggregates (`wage_bill_apu`, `social_benefits`, `fiscal_balance`,
  `total_apu_expenditure`, `debt_interest`, `public_investment`,
  `wage_bill_central`): `famille = "CNA-2010-DEP-APU"` (or its successor —
  confirm in Step 1).
- COFOG series: same family or a COFOG-specific one — confirm.
- `gdp_nominal`: comptes nationaux trimestriels/annuels family.
- `cpi`: `IPC-2015` family.

Concrete edit (illustrative — adjust family names to what Step 1 confirms):

```python
SERIES_SEARCH_RULES = {
    "wage_bill_apu": [
        ("famille", "CNA-2010-DEP-APU"),
        ("OPERATION", "D1"),
        ("SECT-INST", "S13"),
        ("PERIODICITE", "A"),
    ],
    # ... apply same translation to every series ...
    "cofog_gf01": [
        ("famille", "CNA-2010-DEP-APU"),
        ("FONCTION", "FON01"),  # value confirmed in Step 1
        ("SECT-INST", "S13"),
        ("PERIODICITE", "A"),
    ],
    # cofog_gf02 ... cofog_gf10 likewise
}
```

### Step 4: Rewrite `resolve_idbanks()` to use the new positional schema

Replace the whole function body:

```python
def resolve_idbanks(df: pd.DataFrame) -> dict:
    """
    Apply SERIES_SEARCH_RULES to the new positional mapping (list_var/list_mod).
    Returns a dict of logical_name -> idBank string.
    Raises a detailed RuntimeError for any series that cannot be resolved or is ambiguous.
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    required = {"famille", "idbank", "list_mod", "list_var"}
    if not required.issubset(df.columns):
        raise ValueError(
            f"Mapping CSV missing required columns. Got: {list(df.columns)}, "
            f"expected superset of: {sorted(required)}"
        )

    # Pre-split list_var/list_mod once (vectorized) for speed
    df["_vars"] = df["list_var"].str.split(".")
    df["_mods"] = df["list_mod"].str.split(".")

    def row_dim(row, dim):
        try:
            return row["_mods"][row["_vars"].index(dim)]
        except (ValueError, IndexError):
            return None

    resolved = {}
    errors = []

    for name, filters in SERIES_SEARCH_RULES.items():
        mask = pd.Series(True, index=df.index)
        for dim, val in filters:
            if dim == "famille":
                mask &= df["famille"].str.strip() == val
            else:
                # Build per-row value for `dim`; cache on df under f"_dim_{dim}"
                col = f"_dim_{dim}"
                if col not in df.columns:
                    df[col] = df.apply(lambda r, d=dim: row_dim(r, d), axis=1)
                mask &= df[col] == val

        matches = df[mask]
        if len(matches) == 0:
            errors.append(f"[{name}] No series found for filters: {filters}")
        elif len(matches) > 1:
            idbanks = matches["idbank"].head(5).tolist()
            errors.append(
                f"[{name}] Ambiguous: {len(matches)} matches for filters {filters}. "
                f"Candidate idBanks: {idbanks}. Add more filters to disambiguate."
            )
        else:
            resolved[name] = str(matches.iloc[0]["idbank"]).strip()
            log.info(f"Resolved [{name}] -> {resolved[name]}")

    if errors:
        raise RuntimeError(
            f"idBank resolution failed for {len(errors)} series:\n"
            + "\n".join(errors)
        )
    return resolved
```

Note: `_parse_mapping_csv()` already tries `;` and `,`. The new file uses
`;` so no change needed there.

### Step 5: Verify

```bash
cd backend
source .venv/bin/activate
python -m fetchers.insee_idbank_resolver
```

Expected:
- Mapping CSV loaded from cache (or re-downloaded) without 500.
- All ~27 logical series names resolve to 9-digit idBanks.
- `data/raw/insee_idbanks.json` written.
- Exit code 0.

If a series is "Ambiguous" or "No series found", iterate on Step 3
(usually means `famille` needs adjusting or `FONCTION` value form is wrong).

### Step 6: Commit

```bash
git add backend/fetchers/insee_idbank_resolver.py
git commit -m "$(cat <<'EOF'
Session 7a — INSEE: handle new ZIP archive and positional schema

INSEE migrated the idBank mapping from a flat CSV (separate columns per
dimension) to a monthly ZIP whose CSV packs dimensions positionally into
list_mod/list_var. Resolver now scrapes the metadata page for the latest
ZIP, extracts the CSV, and projects each row's positional values to a
dict before applying SERIES_SEARCH_RULES (with renamed dimensions:
FREQ→PERIODICITE, SECT_INST→SECT-INST, COFOG→FONCTION).
EOF
)"
```

Update `CLAUDE.md` Runtime discoveries with the format change and the
final SERIES_SEARCH_RULES tweaks you made (especially anything surprising
about `famille` or `FONCTION` values). Commit that as a separate commit.

---

## Session 7b — OECD: rewrite filters for new 8-dimension DSD

### Background

`DSD_GOV_COFOG@DF_GOV_COFOG_2025` and `DSD_GOV_TRANSACTION@DF_GOV_TRANSACTION_2025`
returned `422 Not enough key values in query, expecting 8 got 5` for the
existing 5-dim filter `A.{countries}..PT_GDP.`. The endpoint and dataset IDs
are still valid; only the dimension count changed.

A confirmed-good probe with 8 empty dimensions (no measure filter) returned
21,897 rows and a header beginning:

```
STRUCTURE,STRUCTURE_ID,STRUCTURE_NAME,ACTION,FREQ,Frequency of observation,
REF_AREA,Reference area,MEASURE,Measure,UNIT_MEASURE,Unit of measure,
SECTOR,Institutional sector,EXPENDITURE,Expenditure,EDIT
```

So the dimension order (after `FREQ` and `REF_AREA`) is at minimum:
`MEASURE, UNIT_MEASURE, SECTOR, EXPENDITURE, ...` — eight dimensions total.

### Files
- Modify: `backend/fetchers/oecd.py`

### Step 1: Discover the exact dimension list per dataset

```bash
cd backend
source .venv/bin/activate
python <<'PY'
import requests
h = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0"}
for dsd in ["DSD_GOV_COFOG@DF_GOV_COFOG_2025", "DSD_GOV_TRANSACTION@DF_GOV_TRANSACTION_2025"]:
    url = f"https://sdmx.oecd.org/public/rest/dataflow/OECD.GOV.GIP/{dsd.split('@')[1]}/latest?references=descendants"
    r = requests.get(url, headers={**h, "Accept": "application/vnd.sdmx.structure+json;version=1.0"}, timeout=60)
    print(dsd, r.status_code)
    if r.status_code == 200:
        data = r.json()
        # Walk to the DSD's dimension list
        dsds = data["data"]["dataStructures"]
        for s in dsds:
            print("  DSD id:", s["id"])
            dims = s["dataStructureComponents"]["dimensionList"]["dimensions"]
            for d in dims:
                print("    -", d["id"])
PY
```

This prints the *ordered* dimension IDs. The filter must list them in that
order, separated by `.`, with `+` for OR within a dimension and empty for
"all values".

### Step 2: Build the new filter expressions

For COFOG-by-function-as-%-of-GDP, you want:
- `FREQ = A`
- `REF_AREA = FRA+DEU+GBR+ITA+ESP+NLD+SWE`
- `MEASURE = ` (empty — keep the historical measure)
- `UNIT_MEASURE = PT_GDP`
- `SECTOR = ` (empty — usually defaults to total/general government)
- `EXPENDITURE = ` (empty — we want all COFOG functions)
- `(remaining dims) = ` (empty)

Compose the filter string from the dimension list discovered in Step 1.
Example (final layout depends on Step 1 output):

```python
FRANCE_PEERS = "FRA+DEU+GBR+ITA+ESP+NLD+SWE"

def _cofog_filter() -> str:
    # Order: FREQ.REF_AREA.MEASURE.UNIT_MEASURE.SECTOR.EXPENDITURE.<dim7>.<dim8>
    return f"A.{FRANCE_PEERS}..PT_GDP...."

def _fiscal_filter() -> str:
    # Confirm dimension order from Step 1; PT_GDP for ratio, EUR_MLN for level
    return f"A.{FRANCE_PEERS}..PT_GDP...."
```

### Step 3: Update `fetch_oecd_cofog` and `fetch_oecd_fiscal`

Replace the two functions to use the helpers above:

```python
def fetch_oecd_cofog(countries: list[str] = None, start_year: int = OECD_START_YEAR) -> pd.DataFrame:
    """Fetch COFOG expenditure by function as % of GDP for the peer countries."""
    countries = countries or OECD_COUNTRIES
    filter_expr = _cofog_filter() if countries == OECD_COUNTRIES else (
        f"A.{'+'.join(countries)}..PT_GDP...."
    )
    df = _fetch_oecd_csv(COFOG_DATASET, filter_expr, start_year)
    save_raw("oecd_cofog", df.to_dict(orient="records"))
    return df
```

(Same shape for `fetch_oecd_fiscal`.)

### Step 4: Verify

```bash
cd backend
source .venv/bin/activate
python -m fetchers.oecd
```

Expected:
- Both calls return non-empty DataFrames.
- Raw files appear at `data/raw/oecd_cofog_YYYY-MM-DD.json` and
  `data/raw/oecd_fiscal_YYYY-MM-DD.json`.
- The 3-second sleep between calls is honored.

### Step 5: Commit

```bash
git add backend/fetchers/oecd.py
git commit -m "$(cat <<'EOF'
Session 7b — OECD: rewrite filters for new 8-dimension DSD layout

DSD_GOV_COFOG and DSD_GOV_TRANSACTION (2025 edition) now expose 8 key
dimensions instead of 5. Filter expressions rebuilt from the live
dataflow definition; FREQ.REF_AREA.MEASURE.UNIT_MEASURE.SECTOR.EXPENDITURE.*.*
with PT_GDP at UNIT_MEASURE position.
EOF
)"
```

Update `CLAUDE.md` Runtime discoveries with the exact dimension order you
observed.

---

## Session 7c — France Travail (formerly Unédic): switch to Excel reader

### Background

The `unedic` fetcher fails because:
1. The dataset has been re-published by **France Travail** (rebranded Pôle
   Emploi); its title no longer contains the word "unédic", so the
   keyword search returns 0 results.
2. The dataset (`561fa8bbc751df54a1cdbb48`) now publishes **Excel only**
   (`format = excel`), no CSV resource. The download URL itself is a
   redirect to a France Travail statistics portal.

The two listed Excel resources point to:
- `https://statistiques.francetravail.org/indem/teleindemalloc` (national
  series, brut + CVS) — this is what we want
- a regional version (not needed for the national-level KPI)

We still need: monthly count of unemployment-insurance allocataires (or
indemnisés), national, time series.

### Files
- Modify: `backend/fetchers/unedic.py` (rename module to `france_travail.py`
  is tempting but defer — keep filename for surgical scope; rename the
  public function instead.)
- Modify: `backend/requirements.txt` — add `openpyxl`.

### Step 1: Pin and install openpyxl

Pick a version older than 1 week from PyPI (today is 2026-05-15). Use
`pip index versions openpyxl` and pick the latest dated `<= 2026-05-08`.
At time of writing, `openpyxl==3.1.5` (released 2024-06-28) is the
current stable; verify and pin.

```bash
cd backend
source .venv/bin/activate
pip index versions openpyxl   # pick a version >= 1 week old
```

Edit `backend/requirements.txt`:

```
requests==2.33.1
pandas==2.3.3
boto3==1.43.6
python-dotenv==1.2.2
openpyxl==3.1.5
```

Then:

```bash
pip install -q -r requirements.txt
```

### Step 2: Probe the France Travail Excel structure

The data.gouv.fr resource URL redirects. Resolve and download once to a
local file, then inspect:

```bash
cd backend
source .venv/bin/activate
python <<'PY'
import requests, pandas as pd, pathlib
h = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
     "Accept-Language":"en-US,en;q=0.9,fr;q=0.8",
     "Referer":"https://www.data.gouv.fr/"}
url = "https://statistiques.francetravail.org/indem/teleindemalloc"
r = requests.get(url, headers=h, allow_redirects=True, timeout=120)
print("final URL:", r.url, "ct:", r.headers.get("Content-Type"), "bytes:", len(r.content))
out = pathlib.Path("data/raw/france_travail_indemnisation.xlsx")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(r.content)
xls = pd.ExcelFile(out)
print("sheets:", xls.sheet_names)
for s in xls.sheet_names[:5]:
    df = xls.parse(s, nrows=5)
    print(f"--- {s}: {df.shape} ---")
    print(df.head())
PY
```

Use the printout to identify the sheet that contains the **monthly national
total of allocataires** (likely a sheet named like "Allocataires" or
"France entière"). Note the header row offset (sometimes data starts at
row 5+).

### Step 3: Rewrite `fetch_unedic_allocataires`

Replace the function with one that:
1. Resolves the dataset's Excel resource via the data.gouv.fr API (still
   the canonical pointer; use dataset id `561fa8bbc751df54a1cdbb48` directly
   — no search needed).
2. Downloads the redirected Excel file with `DEFAULT_HEADERS`.
3. Reads the relevant sheet with `pd.read_excel(..., engine="openpyxl",
   sheet_name=<NAME>, header=<ROW>)` using the offsets found in Step 2.
4. Returns a flat DataFrame with columns `date`, `value` (or whatever the
   downstream processor expects — check `processors/kpi_*.py` if any uses
   `unedic` data; if none, this is unblocked detail).

```python
import io
import pandas as pd
import requests

from fetchers import DEFAULT_HEADERS, save_raw

DATAGOUV_API = "https://www.data.gouv.fr/api/1"
DATASET_ID = "561fa8bbc751df54a1cdbb48"  # Allocataires de l'assurance chômage

def fetch_unedic_allocataires() -> pd.DataFrame:
    """
    Fetch the monthly France Travail (ex-Unédic) allocataires series.
    The published resource is an XLSX hosted on statistiques.francetravail.org.
    """
    meta = requests.get(
        f"{DATAGOUV_API}/datasets/{DATASET_ID}/", headers=DEFAULT_HEADERS, timeout=30
    )
    meta.raise_for_status()
    resources = meta.json().get("resources", [])
    xlsx_resource = next(
        (r for r in resources
         if (r.get("format") or "").lower() in ("xlsx", "excel")
         and "indem" in (r.get("url") or "").lower()
         and "region" not in (r.get("title") or "").lower()),
        None,
    )
    if not xlsx_resource:
        raise ValueError(
            "No national XLSX resource found for France Travail dataset. "
            f"Available formats: {[r.get('format') for r in resources]}"
        )

    resp = requests.get(xlsx_resource["url"], headers=DEFAULT_HEADERS, timeout=180,
                        allow_redirects=True)
    resp.raise_for_status()
    xls = pd.ExcelFile(io.BytesIO(resp.content), engine="openpyxl")
    # Sheet + header offset confirmed in Step 2 — replace placeholders here:
    df = xls.parse(sheet_name="<SHEET_NAME>", header=<HEADER_ROW>)
    save_raw("france_travail_allocataires", df.to_dict(orient="records"))
    return df
```

### Step 4: Verify

```bash
cd backend
source .venv/bin/activate
python -m fetchers.unedic
```

Expected: non-empty DataFrame, raw file written.

### Step 5: Commit

```bash
git add backend/fetchers/unedic.py backend/requirements.txt
git commit -m "$(cat <<'EOF'
Session 7c — Unédic: switch to France Travail XLSX

Dataset 561fa8bbc751df54a1cdbb48 ('Allocataires de l'assurance chômage')
is now published by France Travail in XLSX form only — the keyword
'unedic' no longer appears in the title. Replace the search-based
resource resolution with a direct dataset-ID lookup, add openpyxl
dependency, and parse the national XLSX sheet.
EOF
)"
```

Update `CLAUDE.md` Runtime discoveries with the dataset ID, sheet name,
and header offset you settled on.

---

## Session 7d — Full pipeline integration test + meta.json polish

### Prerequisites

Sessions 7a, 7b, 7c are merged. `data/raw/insee_idbanks.json` resolves to
27 idBanks. OECD fetchers return non-empty frames. France Travail XLSX
parses.

### Files
- May modify: `backend/run_pipeline.py`,
  `backend/processors/kpi_*.py`, `backend/processors/__init__.py`
  if integration surfaces processor mismatches against the new raw shapes
  (especially `kpi_monthly._resolve_column`, which is *expected* to need
  field-name tuning on first live run per the Session 5 note in CLAUDE.md).
- Add `latest_year` / `latest_month` extraction to `meta.json` (deferred
  from Session 6 per the Runtime discoveries note).

### Step 1: Run the pipeline end to end (no upload)

```bash
cd backend
source .venv/bin/activate
python run_pipeline.py --mode full --no-upload
```

Expected: every step in `meta.json.sources` reports `status: ok` *except*
`kpi_tax_expenditure` (which is `skipped` by design until a PLF
dépenses-fiscales fetcher exists).

### Step 2: Triage failures one at a time

For each `status: error` step:
1. Read the recorded error message.
2. Open the relevant processor / fetcher.
3. Reproduce locally with the cached raw file (`data/raw/<source>_*.json`).
4. Fix in the smallest possible diff (no refactors).
5. Re-run only that step's processor module, then re-run the pipeline.

The two highest-likelihood surprises:
- `kpi_monthly`: `_resolve_column` raises listing actual ODS column names —
  copy the right name into the `*_FIELDS` constant lists.
- COFOG processor: GDP series alignment with new INSEE BDM idBanks.

### Step 3: Add `latest_year` and `latest_month` to `meta.json`

In `run_pipeline.py`, after each output JSON is written, peek at the
`france` array's last `year` / `month` and record it on the per-step
status dict:

```python
def _extract_latest_period(output_path: Path) -> dict:
    """Best-effort: read the output JSON and pull the most recent year/month."""
    try:
        data = json.loads(output_path.read_text())
        france = data.get("france") or data.get("data") or []
        if not france:
            return {}
        last = france[-1]
        out = {}
        if "year" in last:
            out["latest_year"] = last["year"]
        if "month" in last:
            out["latest_month"] = last["month"]
        return out
    except Exception:
        return {}
```

Merge the dict into the step's status entry inside `_run_step`.

### Step 4: Verify the meta.json schema

```bash
python -c "import json; m = json.load(open('data/output/meta.json')); print(json.dumps(m, indent=2))" | head -80
```

Expected: each `sources` entry that produced an output now carries
`latest_year` (and `latest_month` for the monthly KPI).

### Step 5: Commit and close out Session 7

```bash
git add backend/
git commit -m "$(cat <<'EOF'
Session 7d — full integration test + meta.json latest-period extraction

End-to-end pipeline run from a non-blocked IP succeeds for all live
sources; only kpi_tax_expenditure remains skipped pending a PLF fetcher.
meta.json now carries latest_year (and latest_month for the monthly KPI)
per output, closing the schema gap noted in Session 6.
EOF
)"
```

Then update `CLAUDE.md`:
- Set the Session 7 status to ✅ done.
- Append a Runtime discoveries block summarising any processor field-name
  fixes you had to apply.

---

## Open follow-ups (not in this plan)

- **PLF "dépenses fiscales" fetcher** (Session 5 deferral): a dedicated
  session to build `fetchers/plf_depenses_fiscales.py` and unblock
  `kpi_tax_expenditure`.
- **Frontend (Phase 2)** (PRD): Vite + React + Recharts UI consuming the
  R2-published JSON. Out of scope for the data layer.
