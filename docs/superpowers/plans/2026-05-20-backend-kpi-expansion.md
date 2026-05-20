# Backend KPI Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do **one session per conversation** to keep context tight, matching the 7a–10 cadence. Always start by reading `CLAUDE.md` and this file's relevant section. Always end by updating `CLAUDE.md`'s **Runtime discoveries** and committing.

**Goal:** Close the four backend data/KPI gaps the user prioritized — peer benchmarking, a tax-expenditure data-source spike, the sustainability debt-to-GDP series, and new KPIs from the currently-orphaned Urssaf / France Travail / on-hand data — without touching deployment.

**Architecture:** No new abstractions beyond two shared OECD helpers. Each session updates one or two fetchers/processors in place, keeping the existing module shape (`fetchers/*.py` cache to `data/raw/`, `processors/*.py` read raw and write `data/output/*.json`). The peer helpers added in Session A are reused by Session B. Two sessions (C, D-spike) are **investigations** — their first deliverable is a findings note, with build tasks gated behind a decision point.

**Tech Stack:** Existing only — `requests==2.33.1`, `pandas==2.3.3`, `boto3==1.43.6`, `python-dotenv==1.2.2`, `openpyxl==3.1.5`. No new dependency unless Session C's spike recommends a PDF library (decided there, not here).

**Testing convention (read this — it overrides the skill's default TDD):** This project has **no pytest**. Verification is by each module's `if __name__ == "__main__"` block plus the full pipeline run (`python run_pipeline.py --mode annual --no-upload`), matching every prior session (7a–10). Do **not** add pytest. Each task's "verify" steps run the module standalone and assert on printed output / JSON content.

---

## Shared assumptions for all sessions

- Run everything from `backend/` with the venv active: `cd backend && source .venv/bin/activate`.
- `fetchers/__init__.py` exposes `DEFAULT_HEADERS` (Firefox UA); reuse it for every `requests.get`.
- OECD rate limit is 20 req/min; the existing `_fetch_oecd_csv` in `fetchers/oecd.py` already sleeps 3 s between calls — reuse it, don't hand-roll new request code.
- Cache raw responses to `data/raw/` before parsing; never re-fetch within a session.
- `data/raw/` and `data/output/` are gitignored — commits are code + `CLAUDE.md` only.
- Peer set is `config.OECD_COUNTRIES = ["FRA","DEU","GBR","ITA","ESP","NLD","SWE"]`; peers exclude FRA → 6 countries (DEU, GBR, ITA, ESP, NLD, SWE).
- **Peer coverage floor is 2007** (OECD GIP data limit) vs. France's 1995. This is an upstream limit, not a bug — document it, don't fight it.
- Session dependency: **A → B** (B's deficit/debt peer wiring reuses A's `peer_series`/`load_oecd_long`). C and D are independent and can run in any order after A is merged (D's wage-ratio build is fully independent; only its "peer" stretch goal would need A).

---

## Session A — Peer benchmarking for overhead, friction, productive spend

### Background

PRD §1.2 names "peer-benchmarked" as a core pillar and §5.1's schema shows a `peers: {DEU, GBR, …, OECD_AVG}` block, but every KPI currently emits `peers: {}`. The OECD raw needed for three of these KPIs is **already cached** (verified 2026-05-20):

- `data/raw/oecd_cofog_*.json`: columns include `REF_AREA, TIME_PERIOD, OBS_VALUE, MEASURE (GE), UNIT_MEASURE (PT_B1GQ = % of GDP), EXPENDITURE (GF01..GF10 + 3-digit sub-codes)`. 7 countries, years 2007–2023.
- `data/raw/oecd_fiscal_*.json`: columns `REF_AREA, TIME_PERIOD, OBS_VALUE, MEASURE (GE/OUT/PRCO), UNIT_MEASURE (PT_B1GQ), SECTOR, TRANSACTION`. `TRANSACTION ∈ {D1, D3, D4, D6M, GSF, GSU, KE, P2, UF, _O_CE, _O_PRCO, _T}`. 7 countries, years 2007–2024. **No B9 (deficit)** — that's Session B's problem, not this one.

Because both numerator and denominator are expressed as % of GDP, every peer ratio below (a share of total expenditure) is dimensionless and directly comparable to the France-side ratio. `OECD_AVG` is the **unweighted mean across the 6 non-France peers**, computed in-processor.

Pension/investment peers are **out of scope**: OECD's fiscal raw has no gross-fixed-capital-formation (P51) series, and PRD §5.5 names no peer source. Leave its `peers: {}`.

### Files
- Modify: `backend/processors/__init__.py` — add `OECD_PEERS`, `OECD_AVG_KEY`, `load_oecd_long()`, `peer_series()`.
- Modify: `backend/processors/kpi_overhead.py` — wire D1/_T peers.
- Modify: `backend/processors/kpi_friction.py` — wire admin-COFOG peers.
- Modify: `backend/processors/kpi_allocation.py` — wire productive-COFOG peers into `compute_productive_spend`.

### Task A1: Add the shared OECD helpers

**Files:**
- Modify: `backend/processors/__init__.py` (append after `write_output`)

- [ ] **Step 1: Add constants and helpers**

Append to `backend/processors/__init__.py`:

```python
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
```

- [ ] **Step 2: Verify the helpers against cached raw**

Run:
```bash
cd backend && source .venv/bin/activate
python -c "
from processors import load_oecd_long, peer_series, OECD_PEERS
cofog = load_oecd_long('oecd_cofog')
print('cofog cols:', sorted(cofog.columns))
print('countries:', sorted(cofog['country'].unique()))
sub = cofog[cofog['expenditure']=='GF01'][['country','year','value']]
ps = peer_series(sub)
print('peer keys:', sorted(ps.keys()))
print('OECD_AVG[:2]:', ps['OECD_AVG'][:2])
"
```
Expected: `cofog cols` includes `country, year, value, expenditure, measure, unit_measure`; `countries` is the 7 ISO codes; `peer keys` is the 6 peers + `OECD_AVG`; FRA absent from `peer keys`.

- [ ] **Step 3: Commit**

```bash
git add backend/processors/__init__.py
git commit -m "Session A1 — processors: add load_oecd_long + peer_series helpers

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task A2: Wire overhead-rate peers (D1 / total expenditure)

**Files:**
- Modify: `backend/processors/kpi_overhead.py`

- [ ] **Step 1: Verify the fiscal raw exposes D1 and _T under MEASURE=GE**

Run:
```bash
cd backend && source .venv/bin/activate
python -c "
from processors import load_oecd_long
f = load_oecd_long('oecd_fiscal')
ge = f[f['measure']=='GE']
for t in ['D1','_T']:
    sub = ge[ge['transaction']==t]
    print(t, 'countries:', sorted(sub['country'].unique()), 'years:', sub['year'].min(), '-', sub['year'].max())
"
```
Expected: both `D1` and `_T` present for all 7 countries, years ~2007–2024. If `_T` is absent under GE, inspect `sorted(ge['transaction'].unique())` and pick the total-expenditure code (it is `_T` in the cache verified 2026-05-20).

- [ ] **Step 2: Add the peer computation**

In `backend/processors/kpi_overhead.py`, add to the imports:
```python
from processors import load_oecd_long, peer_series
```
Then, inside `compute_overhead_rate()`, replace the line `"peers": {},` in the payload with a computed block built just above the `payload = {` assignment:
```python
    fiscal = load_oecd_long("oecd_fiscal")
    ge = fiscal[fiscal["measure"] == "GE"]
    d1 = ge[ge["transaction"] == "D1"][["country", "year", "value"]].rename(columns={"value": "d1"})
    tot = ge[ge["transaction"] == "_T"][["country", "year", "value"]].rename(columns={"value": "tot"})
    merged = d1.merge(tot, on=["country", "year"])
    merged["value"] = merged["d1"] / merged["tot"] * 100
    peers = peer_series(merged[["country", "year", "value"]])
```
and set `"peers": peers,` in the payload. Update the `methodology` string to append:
```
" Peers: OECD GIP 2025, D1/total-expenditure (both % of GDP) — comparable to the France ratio; OECD_AVG is the unweighted mean of DEU/GBR/ITA/ESP/NLD/SWE; peer series start 2007."
```

- [ ] **Step 3: Verify**

Run:
```bash
cd backend && source .venv/bin/activate
python -m processors.kpi_overhead
python -c "
import json; d=json.load(open('data/output/kpi_overhead_rate.json'))
print('peer keys:', sorted(d['peers']))
print('DEU first 2:', d['peers']['DEU'][:2])
print('OECD_AVG first 2:', d['peers']['OECD_AVG'][:2])
"
```
Expected: 6 peer codes + `OECD_AVG`, each with ~17 points starting 2007; France series unchanged (still 1995–2025).

- [ ] **Step 4: Commit**

```bash
git add backend/processors/kpi_overhead.py
git commit -m "Session A2 — kpi_overhead: wire OECD D1/total-expenditure peers

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task A3: Wire productive-spend and friction peers (COFOG buckets)

**Files:**
- Modify: `backend/processors/kpi_allocation.py` (`compute_productive_spend`)
- Modify: `backend/processors/kpi_friction.py`

- [ ] **Step 1: Add a shared peer-bucket helper to `kpi_allocation.py`**

The productive and friction peers share the same construction (a COFOG bucket as % of summed GF01–GF10). Add this module-level function to `backend/processors/kpi_allocation.py`:
```python
import re

from processors import load_oecd_long, peer_series

_TOP_GF = re.compile(r"^GF(0[1-9]|10)$")


def _cofog_bucket_peers(bucket_codes: list[str]) -> dict:
    """
    Peer block for a COFOG bucket: sum(bucket_codes) / sum(GF01..GF10) × 100,
    per peer country, from cached oecd_cofog (% of GDP cancels in the ratio).
    bucket_codes are OECD GF codes, e.g. ["GF04","GF05","GF06"].
    """
    cofog = load_oecd_long("oecd_cofog")
    top = cofog[(cofog["measure"] == "GE") & cofog["expenditure"].str.match(_TOP_GF)]
    total = top.groupby(["country", "year"])["value"].sum().rename("tot").reset_index()
    num = (
        top[top["expenditure"].isin(bucket_codes)]
        .groupby(["country", "year"])["value"]
        .sum()
        .rename("num")
        .reset_index()
    )
    merged = total.merge(num, on=["country", "year"])
    merged["value"] = merged["num"] / merged["tot"] * 100
    return peer_series(merged[["country", "year", "value"]])
```

- [ ] **Step 2: Use it in `compute_productive_spend`**

In `compute_productive_spend()`, set `"peers": _cofog_bucket_peers(["GF04", "GF05", "GF06"]),` (replacing `"peers": {},`). Append to its `methodology`:
```
" Peers: OECD GIP 2025, productive bucket / total COFOG (both % of GDP); OECD_AVG = unweighted mean of the 6 peers; peer series start 2007."
```

- [ ] **Step 3: Use it in `compute_friction_ratio`**

In `backend/processors/kpi_friction.py`, import the helper:
```python
from processors.kpi_allocation import _cofog_bucket_peers
```
and set `"peers": _cofog_bucket_peers(["GF01", "GF02", "GF03"]),`. Append to its `methodology`:
```
" Peers: OECD GIP 2025, administrative bucket (GF01+GF02+GF03) / total COFOG. NOTE: the France-side denominator is revenue (expenditure + balance) while the peer denominator is total expenditure, so peers are TREND-comparable, not level-comparable. OECD_AVG = unweighted mean of the 6 peers; peer series start 2007."
```

- [ ] **Step 4: Verify both**

Run:
```bash
cd backend && source .venv/bin/activate
python -m processors.kpi_allocation
python -m processors.kpi_friction
python -c "
import json
for k in ['kpi_productive_spend','kpi_friction_ratio']:
    d=json.load(open(f'data/output/{k}.json'))
    print(k, 'peer keys:', sorted(d['peers']), 'FRA in peers?', 'FRA' in d['peers'])
    print('  OECD_AVG first:', d['peers']['OECD_AVG'][:1])
"
```
Expected: both have 6 peers + `OECD_AVG`, `FRA in peers? False`, France series unchanged.

- [ ] **Step 5: Run the full annual pipeline and commit**

```bash
cd backend && source .venv/bin/activate
python run_pipeline.py --mode annual --no-upload 2>&1 | tail -5
cd ..
git add backend/processors/kpi_allocation.py backend/processors/kpi_friction.py
git commit -m "Session A3 — kpi_allocation + kpi_friction: wire OECD COFOG-bucket peers

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

- [ ] **Step 6: Record discoveries in CLAUDE.md and commit**

Append a "Session A — peer benchmarking" entry under Runtime discoveries noting: the three KPIs now carry peers; `OECD_AVG` is the unweighted 6-peer mean; peer floor 2007; pension/investment peers deferred (no OECD P51); friction peers are trend- not level-comparable. Commit:
```bash
git add CLAUDE.md
git commit -m "CLAUDE.md: record Session A peer-benchmarking discoveries

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Session B — Sustainability: France debt-to-GDP + deficit & debt peers

### Background

PRD §5.7 wants the deficit trend (done, France 1995–2024) **plus public-debt-to-GDP for France and peers**, and peer deficit lines. Three data facts (verified 2026-05-20):

1. **France debt** lives in INSEE family `DETTE-TRIM-APU-2020` (quarterly, base 2020). Dimensions: `PERIODICITE.INDICATEUR.SECT-INST.DETTE_MAASTRICHT_INTRUMENTS.NATURE.ZONE_GEO.UNITE.CORRECTION.BASIND.SERIE_ARRETEE`. `INDICATEUR=DETTE_MAASTRICHT`, `SECT-INST=S13`, `DETTE_MAASTRICHT_INTRUMENTS=TOT`, `NATURE=PROPORTION`, `UNITE=POURCENT` gives the **Maastricht debt already as % of GDP** — no division needed. **Debt is a STOCK**, so the annual value is the **year-end (Q4) quarter**, NOT a sum of quarters.
2. **Peer deficit** is NOT in the cached `oecd_fiscal` (no B9). Use OECD dataflow `OECD.SDD.NAD,DSD_NASEC10_IDC@DF_TABLE12_IDC` ("Annual government deficit/surplus, revenue, expenditure").
3. **Peer debt** uses OECD `OECD.GOV.GIP,DSD_GOV_FIN_INSTR@DF_GOV_FIN_INSTR_2025` ("Government debt by financial instrument"). Both peer dataflows need a one-time structure probe (Step 1 of B2/B3) to pin dimension order — the GIP DSDs change between editions.

### Files
- Modify: `backend/fetchers/insee_idbank_resolver.py` — add a `public_debt_ratio` rule.
- Modify: `backend/processors/__init__.py` — add `year_end_value()` (stock aggregation).
- Modify: `backend/fetchers/oecd.py` — add `fetch_oecd_deficit()` and `fetch_oecd_debt()`.
- Modify: `backend/processors/kpi_sustainability.py` — add France debt series + deficit & debt peers.
- Modify: `backend/run_pipeline.py` — register the two new OECD fetchers.

### Task B1: Resolve France's Maastricht debt-to-GDP series

**Files:**
- Modify: `backend/fetchers/insee_idbank_resolver.py`

- [ ] **Step 1: Add the resolver rule**

In `SERIES_SEARCH_RULES` (after `cpi`), add:
```python
    "public_debt_ratio": [
        ("famille", "DETTE-TRIM-APU-2020"),
        ("PERIODICITE", "T"),
        ("INDICATEUR", "DETTE_MAASTRICHT"),
        ("SECT-INST", "S13"),
        ("DETTE_MAASTRICHT_INTRUMENTS", "TOT"),
        ("NATURE", "PROPORTION"),
        ("UNITE", "POURCENT"),
    ],
```

- [ ] **Step 2: Re-resolve and confirm a unique match**

Run:
```bash
cd backend && source .venv/bin/activate
python -m fetchers.insee_idbank_resolver 2>&1 | grep -E "public_debt_ratio|Ambiguous|No series"
```
Expected: one `Resolved [public_debt_ratio] -> NNNNNNNNN` line, no ambiguity error. If ambiguous, add `("CORRECTION", "BRUT")` to the rule.

- [ ] **Step 3: Re-fetch BDM and confirm quarterly debt data**

Run:
```bash
cd backend && source .venv/bin/activate
python -m fetchers.insee_bdm 2>&1 | grep public_debt_ratio
python -c "
from processors import load_insee_series
s = load_insee_series()['public_debt_ratio']
print('rows:', len(s), 'first:', s['date'].iloc[0], 'last:', s['date'].iloc[-1])
print(s.tail(4).to_string())
"
```
Expected: quarterly rows like `2024-Q4`, values ~110–115 (France debt is ~110% of GDP). Confirm Q4 entries exist.

- [ ] **Step 4: Commit**

```bash
cd .. && git add backend/fetchers/insee_idbank_resolver.py
git commit -m "Session B1 — INSEE: resolve Maastricht public-debt-to-GDP (DETTE-TRIM-APU-2020)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task B2: Add a year-end (stock) aggregator

**Files:**
- Modify: `backend/processors/__init__.py`

- [ ] **Step 1: Add `year_end_value()`**

`annual_values()` SUMS quarters — correct for flows, wrong for a debt stock. Append to `backend/processors/__init__.py`:
```python
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
```

- [ ] **Step 2: Verify**

Run:
```bash
cd backend && source .venv/bin/activate
python -c "
from processors import load_insee_series, year_end_value
d = year_end_value(load_insee_series()['public_debt_ratio'])
ys = sorted(d); print('years:', ys[0], '-', ys[-1]); print('2024:', d.get(2024))
"
```
Expected: annual dict, 2024 value ~110–113.

- [ ] **Step 3: Commit**

```bash
cd .. && git add backend/processors/__init__.py
git commit -m "Session B2 — processors: add year_end_value() for stock series

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task B3: Fetch peer deficit and peer debt from OECD

**Files:**
- Modify: `backend/fetchers/oecd.py`

- [ ] **Step 1: Probe both dataflows' dimension order**

Run:
```bash
cd backend && source .venv/bin/activate
python <<'PY'
import requests
from fetchers import DEFAULT_HEADERS
H = {**DEFAULT_HEADERS, "Accept":"application/vnd.sdmx.structure+json;version=1.0"}
probes = {
  "deficit": ("OECD.SDD.NAD", "DSD_NASEC10_IDC"),
  "debt":    ("OECD.GOV.GIP", "DSD_GOV_FIN_INSTR"),
}
for label,(agency,dsd) in probes.items():
    u = f"https://sdmx.oecd.org/public/rest/datastructure/{agency}/{dsd}/latest"
    r = requests.get(u, headers=H, timeout=60)
    print(f"\n{label}: {r.status_code}")
    if r.status_code==200:
        d = r.json()["data"]["dataStructures"][0]
        dims = [x["id"] for x in d["dataStructureComponents"]["dimensionList"]["dimensions"]]
        print("  DIMS:", ".".join(dims))
PY
```
Expected: a dotted dimension list for each. Record both. Identify, from the dimension codelists or a trial data pull, the values that select **general government (S13), % of GDP, net lending/borrowing** (deficit) and **general government, % of GDP, total debt** (debt). The deficit dataflow's measure for net lending is typically `B9`/`NLB`; the debt unit for % of GDP is typically `PT_B1GQ`.

- [ ] **Step 2: Confirm a France data pull for each (find the right key)**

Run (adjust the key per Step 1's dims — this is the discovery step):
```bash
cd backend && source .venv/bin/activate
python <<'PY'
import requests, io, pandas as pd
from fetchers import DEFAULT_HEADERS
base="https://sdmx.oecd.org/public/rest/data"
# Pull a wide France slice and inspect which rows are deficit %GDP / debt %GDP
for label,ds in [("deficit","OECD.SDD.NAD,DSD_NASEC10_IDC@DF_TABLE12_IDC"),
                 ("debt","OECD.GOV.GIP,DSD_GOV_FIN_INSTR@DF_GOV_FIN_INSTR_2025")]:
    r=requests.get(f"{base}/{ds}/",headers=DEFAULT_HEADERS,
                   params={"startPeriod":"2007","format":"csvfilewithlabels","dimensionAtObservation":"AllDimensions"},timeout=90)
    print(f"\n=== {label}: {r.status_code} {len(r.content)}B ===")
    if r.status_code==200:
        df=pd.read_csv(io.StringIO(r.text))
        fra=df[df['REF_AREA']=='FRA']
        for c in df.columns:
            if df[c].dtype==object and 1<df[c].nunique()<20 and c not in ('REF_AREA','STRUCTURE','STRUCTURE_ID','ACTION'):
                print(f"  {c}: {sorted(df[c].dropna().unique())[:12]}")
PY
```
Expected: enough to choose filters that isolate France's net-lending-%-GDP and gross-debt-%-GDP. Note the exact `MEASURE`/`UNIT_MEASURE`/`SECTOR` codes used.

- [ ] **Step 3: Add `fetch_oecd_deficit()` and `fetch_oecd_debt()`**

In `backend/fetchers/oecd.py`, add the two dataset constants and keys discovered above (mirror the existing `LIFE_EXPECTANCY_DATASET` / `LIFE_EXPECTANCY_KEY` pattern — full key string filtering to the 7 `OECD_COUNTRIES`, % of GDP, general government), then:
```python
def fetch_oecd_deficit(start_year: int = OECD_START_YEAR) -> pd.DataFrame:
    """Fetch general-government net lending/borrowing (% of GDP) for the peer set."""
    df = _fetch_oecd_csv(DEFICIT_DATASET, DEFICIT_KEY, start_year)
    save_raw("oecd_deficit", df.to_dict(orient="records"))
    return df


def fetch_oecd_debt(start_year: int = OECD_START_YEAR) -> pd.DataFrame:
    """Fetch general-government gross debt (% of GDP) for the peer set."""
    df = _fetch_oecd_csv(DEBT_DATASET, DEBT_KEY, start_year)
    save_raw("oecd_debt", df.to_dict(orient="records"))
    return df
```
Add both to the `__main__` block's prints.

- [ ] **Step 4: Verify both fetchers return all 7 countries**

Run:
```bash
cd backend && source .venv/bin/activate
python -c "
from fetchers.oecd import fetch_oecd_deficit, fetch_oecd_debt
for f in (fetch_oecd_deficit, fetch_oecd_debt):
    df=f(); print(f.__name__, df.shape, 'countries:', sorted(df['REF_AREA'].unique()))
"
```
Expected: both DataFrames non-empty, 7 countries incl. FRA. If a peer is missing some years, that's fine (OECD gaps happen).

- [ ] **Step 5: Commit**

```bash
cd .. && git add backend/fetchers/oecd.py
git commit -m "Session B3 — oecd: add deficit + gross-debt fetchers for peer sustainability

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task B4: Add France debt + deficit/debt peers to the sustainability KPI

**Files:**
- Modify: `backend/processors/kpi_sustainability.py`
- Modify: `backend/run_pipeline.py`

- [ ] **Step 1: Register the new fetchers in the pipeline**

In `backend/run_pipeline.py`, extend the oecd import:
```python
from fetchers.oecd import (
    fetch_oecd_cofog,
    fetch_oecd_deficit,
    fetch_oecd_debt,
    fetch_oecd_fiscal,
    fetch_oecd_life_expectancy,
)
```
and add, after the `oecd_life_expectancy` step in `run_annual()`:
```python
    _run_step("oecd_deficit", fetch_oecd_deficit, sources)
    _run_step("oecd_debt", fetch_oecd_debt, sources)
```

- [ ] **Step 2: Add the France debt series and both peer blocks**

In `backend/processors/kpi_sustainability.py`, import:
```python
from processors import load_oecd_long, peer_series, year_end_value
```
In `compute_fiscal_sustainability()`, after the existing `france` (deficit) list is built, add:
```python
    debt_ratio = year_end_value(series["public_debt_ratio"])
    debt_france = [
        {"year": y, "value": round(debt_ratio[y], 2)} for y in sorted(debt_ratio)
    ]

    deficit_peers = load_oecd_long("oecd_deficit")  # already filtered to net-lending %GDP by the fetcher key
    debt_peers = load_oecd_long("oecd_debt")        # already filtered to gross-debt %GDP by the fetcher key
    peers = {
        "deficit": peer_series(deficit_peers[["country", "year", "value"]]),
        "debt": peer_series(debt_peers[["country", "year", "value"]]),
    }
```
Replace `"peers": {},` with `"peers": peers,` and add a top-level `"debt": {"france": debt_france},` key to the payload. Update `description`/`methodology` to mention the Maastricht debt-to-GDP series (year-end, base 2020) and that peer deficit/debt are OECD-sourced from 2007.

> **Note for the executor:** if Step B3's fetcher keys could not be narrowed to exactly net-lending-%GDP / gross-debt-%GDP (e.g. the dataflow returns several measures), filter here instead — e.g. `deficit_peers[deficit_peers["measure"]=="B9"]` — using the codes recorded in B3 Step 2. Keep `peer_series` input limited to `country, year, value`.

- [ ] **Step 3: Verify**

Run:
```bash
cd backend && source .venv/bin/activate
python -m processors.kpi_sustainability
python -c "
import json; d=json.load(open('data/output/kpi_sustainability.json'))
print('France deficit pts:', len(d['france']))
print('France debt pts:', len(d['debt']['france']), '— 2024:', [p for p in d['debt']['france'] if p['year']==2024])
print('deficit peer keys:', sorted(d['peers']['deficit']))
print('debt peer keys:', sorted(d['peers']['debt']))
"
```
Expected: France deficit unchanged; France debt populated (2024 ~110–113%); both peer blocks have 6 peers + `OECD_AVG`.

- [ ] **Step 4: Full pipeline run + commits**

```bash
cd backend && source .venv/bin/activate
python run_pipeline.py --mode annual --no-upload 2>&1 | tail -6
cd ..
git add backend/processors/kpi_sustainability.py backend/run_pipeline.py
git commit -m "Session B4 — kpi_sustainability: France debt-to-GDP + deficit/debt peers

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
git add CLAUDE.md  # after writing the Session B discoveries entry
git commit -m "CLAUDE.md: record Session B sustainability/debt discoveries

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```
The CLAUDE.md entry must record: the `DETTE-TRIM-APU-2020` rule and that debt is a year-end stock (`year_end_value`); the two new OECD dataflow IDs with their confirmed keys/measures from B3; that the sustainability payload grew a `debt` block and a two-part `peers` (deficit/debt).

---

## Session C — Tax-expenditure data-source spike (INVESTIGATION)

### Background

Session 9 established that no **costed, multi-year, full-list** dépenses-fiscales table is published in tabular form (only a 468-row uncosted list + an 8-row top-IR snapshot; full chiffrage is PDF-only). This session does **not** assume that's final — it systematically checks the remaining candidate sources and produces a recommendation. **No KPI is built here unless a clean tabular source is found** (decision point at the end).

The deliverable is a findings section appended to `CLAUDE.md` plus, if warranted, a follow-up task list. Keep it timeboxed.

### Files
- Modify: `CLAUDE.md` (findings only; code only if Step 5 says "build").

### Task C1: Probe the candidate sources

- [ ] **Step 1: data.gouv.fr — full catalog sweep for costed tables**

Run:
```bash
cd backend && source .venv/bin/activate
python <<'PY'
import requests
from fetchers import DEFAULT_HEADERS
url="https://www.data.gouv.fr/api/1/datasets/"
for q in ["depenses fiscales chiffrage","evaluation depenses fiscales","tome II voies et moyens",
          "depenses fiscales montant","niches fiscales cout"]:
    r=requests.get(url,params={"q":q,"page_size":15},headers=DEFAULT_HEADERS,timeout=30)
    print(f"\n== {q!r} ==")
    for d in r.json().get("data",[]):
        t=d.get("title","")
        if "fiscale" in t.lower() or "niche" in t.lower():
            fmts=sorted({(x.get("format") or "").lower() for x in d.get("resources",[])})
            print(f"  {d.get('last_modified','')[:10]} {d.get('slug','')[:55]} fmts={fmts}")
PY
```
Record any dataset whose resources are CSV/XLSX/JSON **and** whose fields include a cost/montant column (verify fields via the ODS `/records?limit=1` or data.gouv resource preview as in Session 9).

- [ ] **Step 2: Probe non-Bercy sources**

Check, in order, recording availability + format + whether multi-year costed data is present:
- **performance.gouv.fr / forge.dgfip** — the budget "jaune"/PAP annexes sometimes ship CSV.
- **Eurostat** `gov_10a_taxag` and the tax-expenditure-adjacent tables (Eurostat SDMX: `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/...`). Eurostat does not publish France niches fiscales as such, but confirm.
- **IMF / OECD tax expenditure databases** — the Global Tax Expenditures Database (GTED, `gted.net`) publishes France tax-expenditure cost time series as CSV. **This is the most promising lead** — check whether it has an API or a bulk CSV and whether redistribution is licence-compatible (GTED is CC-BY).
- **Cour des comptes / Assemblée nationale open data** — occasionally republish the costed table.

```bash
cd backend && source .venv/bin/activate
python <<'PY'
import requests
from fetchers import DEFAULT_HEADERS
# GTED bulk data probe (adjust path once the site structure is confirmed in a browser)
for u in ["https://gted.net/wp-content/uploads/","https://www.gted.net/"]:
    try:
        r=requests.get(u,headers=DEFAULT_HEADERS,timeout=30)
        print(u,"->",r.status_code,len(r.content),"B")
    except Exception as e:
        print(u,"ERR",e)
PY
```

- [ ] **Step 3: Decision point — write findings and decide**

Append a "Session C — tax-expenditure source spike" entry to `CLAUDE.md` Runtime discoveries listing every source checked, its format, multi-year-costed availability, and licence. Then choose:

- **(build)** A clean, costed, multi-year, redistribution-OK tabular source was found → add a follow-up task block to **this plan** (new fetcher `fetchers/tax_expenditure.py` + implement `compute_tax_expenditure`, mirroring the France-only KPI pattern: `france: [{year, total_cost_eur_bn, count, ratio_to_revenue_pct}]` with revenue from `total_apu_expenditure + fiscal_balance`). Do not build it inline in the spike — schedule it.
- **(defer)** Only PDF / partial sources exist → keep `kpi_tax_expenditure` skipped, confirm Session 9's option-2 (PDF parse) / option-3 (headline aggregate) notes are still the recommended fallbacks, and stop.

- [ ] **Step 4: Commit the findings**

```bash
cd .. && git add CLAUDE.md
git commit -m "Session C — tax-expenditure data-source spike: findings + decision

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Session D — KPIs from Urssaf, France Travail, and on-hand data

### Background

Two fetched sources and two resolved INSEE series are currently **orphaned** (no processor reads them). This session evaluates which efficiency-relevant KPIs they support and builds the strongest candidate(s). Verified column facts (2026-05-20):

- **Urssaf** (`data/raw/urssaf_*.json`, 116 rows, quarterly from 1998): private-sector wage bill (masse salariale), columns `annee, trimestre, dernier_jour_trim, ms_t_50j_brut, ms_t_60j_brut, ms_t_50j_cvs, ms_t_60j_cvs, …`. `ms_t_60j_cvs` is the seasonally-adjusted quarterly private wage bill in EUR (e.g. ~79.3e9 in 1998Q2). `gt_*`/`ga_*` are quarter-on-quarter / year-on-year growth rates.
- **France Travail** (`data/raw/france_travail_allocataires_*.json`, 240 rows, monthly from 2006): wide allocation table; `Total  (1+2+3)` is the headline national indemnisés count. (Note the double space in the column name.)
- **On-hand INSEE**: `wage_bill_apu` (D1, public wage bill, annual 1995–2025), `debt_interest` (D41, annual), `cpi` (monthly), `gdp_nominal`, `total_apu_expenditure`, `fiscal_balance` — all already resolved/loaded but `debt_interest` and `cpi` have no consumer.

### Candidate KPIs (evaluate in D1, build the winners in D2/D3)

1. **Public/Private Wage Bill Ratio** — `wage_bill_apu` (public D1) / annualized Urssaf private wage bill × 100. Directly realizes PRD §1.2's public/private framing. **Strongest candidate — build it (D2).**
2. **Debt Service Burden** — `debt_interest` (D41) / total government revenue (`total_apu_expenditure + fiscal_balance`) × 100, or / GDP. Uses an orphaned on-hand series; a clean sustainability-efficiency signal. **Build it (D3).**
3. **Unemployment-benefit coverage / cost signal** (France Travail) — indemnisés count is a *level*, not an efficiency ratio; the natural efficiency metric (benefit € per recipient) needs a benefit-spend series France Travail's count doesn't provide. **Document as a candidate, do not build now** (note in CLAUDE.md what extra series it would need — e.g. GF10.5 unemployment sub-function or a France Travail expenditure file).
4. **Real-terms deflation using CPI** — a transformation, not a KPI on its own. **Document as a utility** to apply later if any KPI wants constant-euro framing.

### Files
- Modify: `CLAUDE.md` (D1 findings).
- Create: `backend/processors/kpi_wage_ratio.py` (D2).
- Modify: `backend/processors/kpi_sustainability.py` OR create `backend/processors/kpi_debt_service.py` (D3 — see task).
- Modify: `backend/run_pipeline.py` (register D2/D3 processors).

### Task D1: Evaluate candidates and record the decision

- [ ] **Step 1: Sanity-check the Urssaf annualization and the ratio scale**

Run:
```bash
cd backend && source .venv/bin/activate
python <<'PY'
import json, pandas as pd
from processors import latest_raw, load_insee_series, annual_values
u = pd.DataFrame(json.loads(latest_raw("urssaf").read_text()))
u["annee"]=u["annee"].astype(int)
priv = u.groupby("annee")["ms_t_60j_cvs"].sum()  # 4 quarters → annual private wage bill
pub = annual_values(load_insee_series()["wage_bill_apu"])
for y in [2015, 2020, 2023]:
    if y in priv.index and y in pub:
        print(y, "public D1:", round(pub[y]/1e9,1), "Bn  private:", round(priv[y]/1e9,1),
              "Bn  ratio %:", round(pub[y]/priv[y]*100,1))
PY
```
Expected: a plausible ratio (public wage bill is roughly 40–55% of the private wage bill; sanity-check the order of magnitude — if it's wildly off, the Urssaf column or unit is wrong, re-inspect).

- [ ] **Step 2: Record the decision in CLAUDE.md**

Append a "Session D — orphaned-source KPI evaluation" entry: build #1 (wage ratio) and #2 (debt service); defer #3 (France Travail — needs a benefit-spend series, note which); note #4 (CPI deflation utility) for later. Commit:
```bash
cd .. && git add CLAUDE.md
git commit -m "Session D1 — evaluate Urssaf/France-Travail KPIs, record decisions

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task D2: Build the Public/Private Wage Bill Ratio KPI

**Files:**
- Create: `backend/processors/kpi_wage_ratio.py`
- Modify: `backend/run_pipeline.py`

- [ ] **Step 1: Write the processor**

Create `backend/processors/kpi_wage_ratio.py`:
```python
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
    public = annual_values(load_insee_series()["wage_bill_apu"])
    private = _private_wage_bill_annual()

    france = [
        {"year": y, "value": round(public[y] / private[y] * 100, 2)}
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
            "quarters) × 100. Years with fewer than 4 Urssaf quarters are dropped."
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
```

- [ ] **Step 2: Verify standalone**

Run:
```bash
cd backend && source .venv/bin/activate
python -m processors.kpi_wage_ratio
```
Expected: a non-empty France series (roughly 1998–2024, since Urssaf starts 1998), a plausible `latest` ratio.

- [ ] **Step 3: Register in the pipeline**

In `backend/run_pipeline.py`, import `from processors.kpi_wage_ratio import compute_wage_ratio` and add `_run_step("kpi_wage_ratio", compute_wage_ratio, sources)` to `run_monthly()` (Urssaf is fetched in the monthly run; place the step after `urssaf`). 

> **Dependency note:** the wage ratio needs `wage_bill_apu` from the INSEE raw, which is fetched in `run_annual()`. In `--mode full` annual runs first so the raw is present. For a standalone `--mode monthly` run, `load_insee_series()` reads the last cached INSEE raw — acceptable, but note it in the KPI's log if the INSEE cache is missing (the existing `load_insee_series` raises a clear FileNotFoundError, which the orchestrator records as `error`).

- [ ] **Step 4: Commit**

```bash
cd .. && git add backend/processors/kpi_wage_ratio.py backend/run_pipeline.py
git commit -m "Session D2 — new KPI: Public/Private Wage Bill Ratio (Urssaf + INSEE D1)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

### Task D3: Build the Debt Service Burden KPI

**Files:**
- Create: `backend/processors/kpi_debt_service.py`
- Modify: `backend/run_pipeline.py`

- [ ] **Step 1: Write the processor**

Create `backend/processors/kpi_debt_service.py`:
```python
"""
KPI: Debt Service Burden — interest paid on public debt (INSEE D41_S13) as a
percentage of total government revenue. Puts the orphaned debt-interest series
to use as a sustainability-efficiency signal: how much of each revenue euro is
consumed servicing past borrowing before any service is delivered.
France-only; the PRD names no peer source.
"""

import logging

from processors import (
    annual_values,
    build_latest,
    load_insee_series,
    now_iso,
    write_output,
)

log = logging.getLogger(__name__)


def compute_debt_service() -> dict:
    """Compute the Debt Service Burden and write kpi_debt_service.json."""
    series = load_insee_series()
    interest = annual_values(series["debt_interest"])
    expenditure = annual_values(series["total_apu_expenditure"])
    balance = annual_values(series["fiscal_balance"])

    france = []
    for y in sorted(set(interest) & set(expenditure) & set(balance)):
        revenue = expenditure[y] + balance[y]
        if revenue:
            france.append({"year": y, "value": round(interest[y] / revenue * 100, 2)})

    payload = {
        "kpi_id": "debt_service",
        "kpi_name": "Debt Service Burden",
        "description": (
            "Interest paid on public debt as a percentage of total government "
            "revenue. A rising burden crowds out service delivery."
        ),
        "unit": "percent",
        "source": "INSEE BDM — CNT-2020-CSI (D41_S13, OTE_S13, B9NF_S13)",
        "methodology": (
            "D41_S13 (interest paid, all APU) / total government revenue, where "
            "revenue = total APU expenditure (OTE) + fiscal balance (B9NF). All "
            "from CNT-2020-CSI quarterly accounts summed to annual."
        ),
        "last_updated": now_iso(),
        "france": france,
        "peers": {},
        "latest": build_latest(france),
    }
    write_output("kpi_debt_service.json", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = compute_debt_service()
    print(f"\nDebt service: {len(r['france'])} France points; latest: {r['latest']}")
```

- [ ] **Step 2: Verify standalone**

Run:
```bash
cd backend && source .venv/bin/activate
python -m processors.kpi_debt_service
```
Expected: France series 1995–2024, values in the low single digits to ~5% (interest is a small share of revenue).

- [ ] **Step 3: Register in the pipeline**

In `backend/run_pipeline.py`, import `from processors.kpi_debt_service import compute_debt_service` and add `_run_step("kpi_debt_service", compute_debt_service, sources)` to `run_annual()` after `kpi_sustainability`.

- [ ] **Step 4: Full pipeline run + commits**

```bash
cd backend && source .venv/bin/activate
python run_pipeline.py --mode full --no-upload 2>&1 | tail -8
cd ..
git add backend/processors/kpi_debt_service.py backend/run_pipeline.py
git commit -m "Session D3 — new KPI: Debt Service Burden (INSEE D41 / revenue)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
git add CLAUDE.md  # after writing the Session D build notes
git commit -m "CLAUDE.md: record Session D new-KPI builds + France Travail deferral

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```
The CLAUDE.md entry records: the two new KPI files and their formulas; that `debt_interest` and Urssaf are no longer orphaned; CPI and France Travail remain unused (with the note on what France Travail would need to become a KPI).

---

## Open follow-ups (out of scope for this plan)

- **Deployment (Session 12 of the phase-completion plan)** — systemd timers + live R2 upload. Explicitly deferred by the user.
- **Pension/investment peers** — needs an OECD gross-fixed-capital-formation series not in the current fiscal raw; revisit if peer coverage of §5.5 is wanted.
- **Outcomes education half (PISA)** — non-SDMX source needed (Session 10 note).
- **CPI deflation utility** — build only when a KPI wants constant-euro framing (Session D candidate #4).
- **Urssaf TLS** — `open.urssaf.fr` had an expired certificate on 2026-05-20; if it persists, the wage-ratio KPI will go stale (fail-soft `error` in meta). Watch for renewal; do **not** add `verify=False`.

---

## Self-review

**Spec coverage** (the 4 requested topics):
1. *Integrate peer benchmarking* → Session A (overhead, friction, productive) + Session B4 (sustainability deficit/debt peers). ✅
2. *Investigate tax-expenditure sources* → Session C spike with explicit build/defer decision point. ✅
3. *Build sustainability debt-to-GDP* → Session B1–B4 (France Maastricht debt + peer debt). ✅
4. *Investigate Urssaf/France-Travail/on-hand KPIs* → Session D1 evaluation + D2 (wage ratio) + D3 (debt service); France Travail deferral documented. ✅

**Placeholder scan:** Build tasks (A1–A3, B1–B2, B4, D2, D3) contain complete code. Discovery-dependent tasks (B3 OECD keys, C source probes) contain concrete probe commands and explicit decision branches rather than guessed keys — this is deliberate, since the OECD GIP DSD dimension order is not stable across editions and must be read at execution time (same approach as the prior plan's OECD Step 1).

**Type/name consistency:** `load_oecd_long`/`peer_series`/`OECD_PEERS`/`OECD_AVG_KEY` (A1) are reused verbatim in A2, A3, B4. `year_end_value` (B2) is used in B4. `_cofog_bucket_peers` (A3, in kpi_allocation) is imported by kpi_friction. New KPI ids (`wage_ratio`, `debt_service`) and output filenames are unique and consistent with their `write_output` calls.
