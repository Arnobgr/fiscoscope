# Phase 1 Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Each session below is independent — do **one session per conversation** to keep context tight, matching the 7a–7d cadence. Always start by reading `CLAUDE.md` and this file's relevant section. Always end by updating `CLAUDE.md`'s **Runtime discoveries** and committing.

**Goal:** Close every remaining gap between the current backend (Sessions 1–7, all integration-green as of 2026-05-16) and the PRD's full Phase 1 deliverable: 1995-present data freshness, peer-benchmarked KPIs, the two outcome KPIs that are still empty, the missing tax-expenditure fetcher, and a working scheduled VPS deployment publishing to R2.

**Architecture:** No new abstractions. Each session updates one or two modules in place, keeping the existing fetcher/processor module shape. The pipeline orchestrator (`run_pipeline.py`) gains one new fetch step (PLF) and one optional new processor. Tests remain the existing `__main__` blocks plus the full pipeline at the end — matching project convention. No pytest dependency added.

**Tech Stack:** Existing — `requests==2.33.1`, `pandas==2.3.3`, `boto3==1.43.6`, `python-dotenv==1.2.2`, `openpyxl==3.1.5`. Session 12 also uses `systemd` (host-side) and `aws-cli`/`boto3` for R2 verification.

**Shared assumptions for all sessions:**
- `backend/.venv` already exists with deps installed.
- `fetchers/__init__.py` already exposes `DEFAULT_HEADERS` (Firefox-style UA); reuse it for every `requests.get` call.
- Be polite: never burst more than ~1 request/second to a given host. OECD's 20-req/min limit is honored via `time.sleep(3)` inside `_fetch_oecd_csv`.
- Cache raw responses to `data/raw/` before parsing — never re-fetch in the same session.
- Sessions 8 → 9 → 10 build on each other (8 unblocks the data range that 9–10 read from). Session 11 and Session 12 are independent and can run in either order after 8.
- Frontend (Phase 2 per PRD §11.2) is **explicitly out of scope** for this plan; it gets its own brainstorm + plan once Sessions 8–12 ship. See "Open follow-ups" at the bottom.

---

## Session 8 — Rebase INSEE COFOG/APU series from base-2014 to base-2020

### Background (read this first)

CLAUDE.md's Session 7d Runtime discoveries note flags this as the most urgent gap: four KPIs (`kpi_overhead_rate`, `kpi_friction_ratio`, `kpi_productive_spend`, `kpi_pension_investment`) stop at **2020** because the resolver still points at the discontinued `CNA-2014-DEP-APU` family. INSEE has retired base 2014; the active family is `CNA-2020-DEP-APU` (and `CNA-2020-CSI` for the satellite sector accounts). `gdp_nominal` is already on `CNA-2020-PIB` (Session 7a fix), so this session just brings the other APU and COFOG series in line.

Within the base-2020 vintage, the dimension *vocabulary* is mostly stable from base-2014 (PERIODICITE, SECT-INST, OPERATION, FONCTION, COMPTE, NATURE, UNITE, etc.) but some OPERATION/account codes may have shifted. CLAUDE.md's Session 7a list of "SERIES_SEARCH_RULES surprises" (D6M-not-D62, P5K2-not-P51, FONTOTAL aggregate, fiscal_balance via CNA-2014-CSI/COMPTE=EA, etc.) is the starting hypothesis — confirm or refine each by inspecting the new family in Step 1.

### Files

- Modify: `backend/fetchers/insee_idbank_resolver.py` (constants only — no logic changes)
- Side effect: `backend/data/raw/insee_idbanks.json` rewritten with new idBanks
- Side effect: `backend/data/raw/insee_bdm_*.json` re-fetched

### Step 1: Inventory the new family's dimensions and codes

- [ ] **Inspect what's in `CNA-2020-DEP-APU` and `CNA-2020-CSI`**

```bash
cd backend
source .venv/bin/activate
python <<'PY'
import pandas as pd
df = pd.read_csv('data/raw/insee_idbank_mapping.csv', sep=';', dtype=str, low_memory=False)
for fam in ['CNA-2020-DEP-APU', 'CNA-2020-CSI', 'CNA-2014-DEP-APU', 'CNA-2014-CSI']:
    sub = df[df['famille'] == fam]
    print(f'\n== {fam}: {len(sub)} rows ==')
    if sub.empty:
        continue
    # Show dimension vocabulary on one row, then distinct values per dim
    varset = sub['list_var'].iloc[0]
    print('dims:', varset)
    dims = varset.split('.')
    def dimval(row, dim):
        vars_ = row['list_var'].split('.')
        mods = row['list_mod'].split('.')
        return mods[vars_.index(dim)] if dim in vars_ else None
    for d in dims:
        vals = sub.apply(lambda r, d=d: dimval(r, d), axis=1).dropna().unique()
        print(f'  {d}: {sorted(vals)[:25]}{"..." if len(vals) > 25 else ""}')
PY
```

Expected: `CNA-2020-DEP-APU` exists with at least the dimensions {PERIODICITE, INDICATEUR, SECT-INST, OPERATION, NATURE, FONCTION, ZONE_GEO, UNITE, CORRECTION, BASIND}. Take note of:
- Whether OPERATION still has `D1`, `D6M`, `P5K2`, `OTE` (total expenditure).
- Whether FONCTION still uses `FON01`–`FON10` and accepts `FONTOTAL`.
- Whether `CNA-2020-CSI` has `B9NF` and `D41` with `COMPTE=EA` (for `fiscal_balance` and `debt_interest`).

If `CNA-2020-CSI` is missing or B9NF/D41 are gone, fall back to whatever the family actually exposes and adjust the rule in Step 2 accordingly.

### Step 2: Update `SERIES_SEARCH_RULES` to the base-2020 families

- [ ] **Edit `backend/fetchers/insee_idbank_resolver.py`**

Replace the `famille` value `"CNA-2014-DEP-APU"` with `"CNA-2020-DEP-APU"` everywhere it appears, and `"CNA-2014-CSI"` with `"CNA-2020-CSI"`. Concrete edit (text replacement):

```python
SERIES_SEARCH_RULES = {
    "wage_bill_apu": [
        ("famille", "CNA-2020-DEP-APU"),
        ("OPERATION", "D1"),
        ("SECT-INST", "S13"),
        ("FONCTION", "FONTOTAL"),
        ("PERIODICITE", "A"),
    ],
    "wage_bill_central": [
        ("famille", "CNA-2020-DEP-APU"),
        ("OPERATION", "D1"),
        ("SECT-INST", "S1311"),
        ("FONCTION", "FONTOTAL"),
        ("PERIODICITE", "A"),
    ],
    "public_investment": [
        ("famille", "CNA-2020-DEP-APU"),
        ("OPERATION", "P5K2"),
        ("SECT-INST", "S13"),
        ("FONCTION", "FONTOTAL"),
        ("PERIODICITE", "A"),
    ],
    "social_benefits": [
        ("famille", "CNA-2020-DEP-APU"),
        ("OPERATION", "D6M"),
        ("SECT-INST", "S13"),
        ("FONCTION", "FONTOTAL"),
        ("PERIODICITE", "A"),
    ],
    "total_apu_expenditure": [
        ("famille", "CNA-2020-DEP-APU"),
        ("OPERATION", "OTE"),
        ("SECT-INST", "S13"),
        ("FONCTION", "FONTOTAL"),
        ("PERIODICITE", "A"),
    ],
    "fiscal_balance": [
        ("famille", "CNA-2020-CSI"),
        ("OPERATION", "B9NF"),
        ("SECT-INST", "S13"),
        ("COMPTE", "EA"),
        ("PERIODICITE", "A"),
    ],
    "debt_interest": [
        ("famille", "CNA-2020-CSI"),
        ("OPERATION", "D41"),
        ("SECT-INST", "S13"),
        ("COMPTE", "EA"),
        ("PERIODICITE", "A"),
    ],
    # gdp_nominal, cpi stay on CNA-2020-PIB / IPC-2025 (Session 7a fix — unchanged)
    "gdp_nominal": [ ... existing rule ... ],
    "cpi":         [ ... existing rule ... ],
    # COFOG: same family migration
    "cofog_gf01": [
        ("famille", "CNA-2020-DEP-APU"),
        ("FONCTION", "FON01"),
        ("SECT-INST", "S13"),
        ("OPERATION", "OTE"),
        ("PERIODICITE", "A"),
    ],
    # cofog_gf02 ... cofog_gf10 same shape, only FONCTION changes
}
```

**Critical:** Keep the `OPERATION` filter on the COFOG rules — the existing rules in `insee_idbank_resolver.py` may use a different aggregate code. Use whatever Step 1 surfaces as the "total expenditure across all dimensions of a given function" code (likely `OTE`). If Step 1 shows multiple matches per `(FONCTION, SECT-INST, PERIODICITE)`, add the disambiguator listed there (often `NATURE=VALEUR_ABSOLUE`, `UNITE=EUROS_COURANTS`, `CORRECTION=BRUT`).

### Step 3: Re-resolve idBanks and confirm all 19 land

- [ ] **Run the resolver standalone**

```bash
cd backend
source .venv/bin/activate
python -m fetchers.insee_idbank_resolver
```

Expected: 19 series resolve, no "Ambiguous" / "No series found" errors, `data/raw/insee_idbanks.json` rewritten with new 9-digit idBanks (all different from the prior file). Diff to confirm:

```bash
git diff data/raw/insee_idbanks.json
```

If any series fail: iterate on Step 2 with the disambiguators surfaced by the error message.

### Step 4: Re-fetch BDM and check the year range

- [ ] **Run the BDM fetcher**

```bash
cd backend
source .venv/bin/activate
python -m fetchers.insee_bdm
```

Expected: every series logs ≥ 26 rows (1995–2023 minimum, hopefully through 2024). For each series, the latest year should now be 2023 or 2024 (was 2020 before).

```bash
python <<'PY'
import json, pandas as pd
recs = json.load(open('data/raw/insee_bdm_2026-05-16.json'))
df = pd.DataFrame(recs)
for ib in df['idbank'].unique():
    sub = df[df['idbank']==ib].sort_values('date')
    print(f'{ib}: {sub["date"].iloc[0]} → {sub["date"].iloc[-1]} ({len(sub)} rows)')
PY
```

### Step 5: Re-run the full pipeline; verify `meta.json` latest_year advances

- [ ] **Re-run pipeline (offline upload skipped)**

```bash
cd backend
source .venv/bin/activate
python run_pipeline.py --mode annual --no-upload
python -c "import json; m=json.load(open('data/output/meta.json'));
[print(k, v.get('latest_year')) for k,v in m['sources'].items() if v.get('latest_year')]"
```

Expected: `kpi_overhead_rate`, `kpi_friction_ratio`, `kpi_productive_spend`, `kpi_pension_investment` all advance to `latest_year: 2023` (or 2024 if INSEE has the prior year published). `kpi_sustainability` similarly advances.

### Step 6: Commit

- [ ] **Two commits — code change + raw/output refresh**

```bash
cd /home/arnobgr/french-efficiency-dashboard
git add backend/fetchers/insee_idbank_resolver.py
git commit -m "$(cat <<'EOF'
Session 8 — INSEE: rebase APU/COFOG series to CNA-2020

CNA-2014-DEP-APU is end-of-life; data stopped at 2020 and CLAUDE.md
Session 7d flagged this as the top integration gap. Repoint every APU
aggregate and COFOG function rule to CNA-2020-DEP-APU, and the two
CSI-sourced rules (fiscal_balance, debt_interest) to CNA-2020-CSI.
gdp_nominal/cpi already on the 2020/2025 vintages from Session 7a.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Then update `CLAUDE.md`:
- Append a "Session 8 — base-2020 rebase landed" entry under Runtime discoveries, listing any OPERATION/FONCTION/COMPTE code shifts you had to apply (these belong with the same level of detail as Session 7a's note).
- Commit as a second commit:

```bash
git add CLAUDE.md
git commit -m "CLAUDE.md: record Session 8 runtime discoveries

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

## Session 9 — OECD peer wiring for overhead, friction, sustainability

### Background

PRD §1.2 lists "**Peer-benchmarked**" as one of the four core philosophy items, and §5.1's standard schema shows a `peers: {DEU, GBR, ITA, ESP, OECD_AVG, ...}` block. Today every KPI emits `peers: {}` (the Session 4/5 deferral note in CLAUDE.md). With OECD raw data now flowing live (Session 7b), this session wires three KPIs to their peer series. Live inspection of the raw frames (done during plan drafting) confirmed:

- `data/raw/oecd_cofog_*.json`: 4025 rows × 32 cols, **`MEASURE='GE'`** (Government Expenditures) and **`UNIT_MEASURE='PT_B1GQ'`** (% of GDP), `EXPENDITURE` covers `GF01`–`GF10` plus 3-digit sub-codes (`GF0501`, `GF0502`, …), 7 peer countries (DEU, ESP, FRA, GBR, ITA, NLD, SWE), years 2007–2023.
- `data/raw/oecd_fiscal_*.json`: 1764 rows × 32 cols, `TRANSACTION ∈ {D1, D3, D4, D6M, GSF, GSU, KE, P2, UF, _O_CE, _O_PRCO, _T}` (no `B9`), `UNIT_MEASURE='PT_B1GQ'`, years 2007–2024.
- **`OECD_AVG` is not in the raw** — it is computed in-processor as the **simple mean** of the 7 peers per (year, metric). Document this in each KPI's `methodology` field.
- **`B9` (net lending) is missing from the current fiscal raw.** Step 1 below probes the `DSD_GOV_TRANSACTION` structure for the right `TRANSACTION` code (likely `B9` or `B9G` or `_T` minus revenue side) or adds a third OECD dataflow if needed.

This session updates **three processors** (overhead, friction, sustainability) and possibly the OECD fetcher. Outcomes/tax-expenditure peer wiring is deferred to Session 10 / Session 11.

### Files

- May modify: `backend/fetchers/oecd.py` (if Step 1 reveals B9 needs a different filter or a new dataflow)
- Modify: `backend/processors/kpi_overhead.py`, `backend/processors/kpi_friction.py`, `backend/processors/kpi_sustainability.py`
- Modify: `backend/processors/__init__.py` — add a shared `load_oecd_long()` helper (one place, three callers)
- Modify: `backend/config.py` — add `OECD_AVG_KEY = "OECD_AVG"` constant (referenced in three processors)

### Step 1: Probe OECD for the deficit (B9) indicator

- [ ] **Discover what TRANSACTION code OECD uses for net lending and re-run the fiscal fetch if needed**

```bash
cd backend
source .venv/bin/activate
python <<'PY'
import requests
from fetchers import DEFAULT_HEADERS
# DSD definition
url = "https://sdmx.oecd.org/public/rest/dataflow/OECD.GOV.GIP/DF_GOV_TRANSACTION_2025/latest?references=descendants"
r = requests.get(url, headers={**DEFAULT_HEADERS, "Accept":"application/vnd.sdmx.structure+json;version=1.0"}, timeout=60)
data = r.json()
# Find the TRANSACTION codelist
for cl in data["data"].get("codelists", []):
    if "TRANSACTION" in cl["id"]:
        print(cl["id"], '-', len(cl["codes"]), "codes")
        for c in cl["codes"]:
            if c["id"].startswith(("B9", "TR", "NLB")):
                print(" ", c["id"], "—", c.get("name"))
PY
```

Expected: identify the code for "net lending / net borrowing" (likely `B9` or `B9G`). If it's `B9` and is *not* in our current cached raw, the OECD fetcher's filter (`A.{peers}..PT_B1GQ....`) is too narrow — confirm by inspecting the raw's `TRANSACTION` column. If `B9` is in the codelist but missing from raw, the filter is dropping it; refetch with a broader filter (no TRANSACTION restriction; the existing filter already passes empty there).

If the raw is already comprehensive (B9 was just hidden because of the year/peer slice), no fetcher change is needed.

**Decision point:** if `B9` requires a new dataflow (`DF_FISCAL_BALANCE` or similar — unlikely but possible), add a third fetch function `fetch_oecd_deficit()` in `oecd.py` rather than overloading `fetch_oecd_fiscal`. Otherwise skip this paragraph.

### Step 2: Add a shared `load_oecd_long()` helper

- [ ] **Append to `backend/processors/__init__.py`**

```python
import pandas as pd

OECD_PEERS = ["DEU", "ESP", "FRA", "GBR", "ITA", "NLD", "SWE"]
OECD_AVG_KEY = "OECD_AVG"

def load_oecd_long(source: str) -> pd.DataFrame:
    """
    Read the most recent data/raw/{source}_*.json into a long-format DataFrame
    keyed by (REF_AREA, TIME_PERIOD) with selected columns only.
    Returns columns: country, year, value, transaction, expenditure, unit.
    `transaction` is None for COFOG data; `expenditure` is None for fiscal.
    """
    import json
    path = latest_raw(source)
    if path is None:
        raise FileNotFoundError(f"No data/raw/{source}_*.json found")
    df = pd.DataFrame(json.loads(path.read_text()))
    cols = {
        "REF_AREA": "country",
        "TIME_PERIOD": "year",
        "OBS_VALUE": "value",
        "UNIT_MEASURE": "unit",
    }
    optional = {"TRANSACTION": "transaction", "EXPENDITURE": "expenditure"}
    for c, alias in optional.items():
        if c in df.columns:
            cols[c] = alias
    out = df[list(cols)].rename(columns=cols)
    out["year"] = out["year"].astype(int)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    return out.dropna(subset=["value"])


def peer_series(df: pd.DataFrame, value_col: str = "value") -> dict:
    """
    Turn a long DataFrame with columns (country, year, value) into the
    {country_code: [{year, value}, ...]} dict expected by §5.1's `peers` block,
    plus an OECD_AVG entry computed as the simple per-year mean across peers.
    France is included if present (callers usually drop it before passing in).
    """
    out = {}
    for country, sub in df.groupby("country"):
        rows = sub.sort_values("year")[["year", value_col]].to_dict(orient="records")
        out[country] = [{"year": int(r["year"]), "value": round(float(r[value_col]), 2)} for r in rows]
    # OECD_AVG: per-year mean across all peers in df
    avg = df.groupby("year")[value_col].mean().reset_index().sort_values("year")
    out[OECD_AVG_KEY] = [{"year": int(r.year), "value": round(float(getattr(r, value_col)), 2)} for r in avg.itertuples()]
    return out
```

- [ ] **Verify the helpers run clean against current raw**

```bash
cd backend
source .venv/bin/activate
python -c "
from processors import load_oecd_long, peer_series
df = load_oecd_long('oecd_cofog')
print('cofog rows:', len(df), 'countries:', sorted(df['country'].unique()))
# Filter to one function and check peer_series shape
sub = df[df['expenditure'] == 'GF01'][['country','year','value']]
ps = peer_series(sub)
print('GF01 peer keys:', list(ps.keys()))
print('OECD_AVG sample:', ps['OECD_AVG'][:3])
"
```

### Step 3: Wire `kpi_sustainability.peers` (B9/GDP)

- [ ] **Edit `backend/processors/kpi_sustainability.py`**

After the existing France section, before `write_output(...)`, insert:

```python
from processors import OECD_PEERS, peer_series, load_oecd_long

oecd = load_oecd_long("oecd_fiscal")
# Step 1's discovery should have confirmed the TRANSACTION code for net lending.
# If it's "B9" the filter is below; adjust to the actual code observed.
deficit = oecd[(oecd["transaction"] == "B9") & (oecd["country"] != "FRA")]
payload["peers"] = peer_series(deficit[["country", "year", "value"]])
```

If Step 1 found B9 in a different dataflow, swap the `load_oecd_long("oecd_fiscal")` source name accordingly.

- [ ] **Verify**

```bash
cd backend
source .venv/bin/activate
python -m processors.kpi_sustainability
python -c "import json; d=json.load(open('data/output/kpi_sustainability.json'));
print('peer keys:', list(d['peers'].keys()));
print('DEU sample:', d['peers'].get('DEU', [])[:3])"
```

Expected: 6 country codes + `OECD_AVG`, each with 17+ year-value points.

### Step 4: Wire `kpi_productive_spend.peers` and `kpi_overhead_rate.peers`

- [ ] **Edit `backend/processors/kpi_allocation.py` (`compute_productive_spend`)**

```python
from processors import OECD_PEERS, peer_series, load_oecd_long
from config import COFOG_PRODUCTIVE  # already imported

cofog = load_oecd_long("oecd_cofog")
# Per-country productive_pct = (GF04+GF05+GF06) / sum(GF01..GF10), all as % of GDP.
# Since both numerator and denominator share GDP denominator, ratio is valid.
top10 = cofog[cofog["expenditure"].str.match(r"GF0[1-9]$|GF10$")]
totals = top10.groupby(["country", "year"])["value"].sum().rename("total").reset_index()
productive = top10[top10["expenditure"].isin(["GF04", "GF05", "GF06"])]
prod_sum = productive.groupby(["country", "year"])["value"].sum().rename("prod").reset_index()
merged = totals.merge(prod_sum, on=["country", "year"])
merged["value"] = merged["prod"] / merged["total"] * 100
merged = merged[merged["country"] != "FRA"]
payload["peers"] = peer_series(merged[["country", "year", "value"]])
```

- [ ] **Edit `backend/processors/kpi_overhead.py` (`compute_overhead_rate`)**

```python
from processors import OECD_PEERS, peer_series, load_oecd_long

fiscal = load_oecd_long("oecd_fiscal")
# overhead_pct = D1 / _T (total expenditure), both as % of GDP — ratio is the same as in
# % of total expenditure space, so this is the apples-to-apples peer comparison
# (modulo the OECD's own S13 sectoring vs. INSEE's APU; documented in methodology).
d1 = fiscal[fiscal["transaction"] == "D1"][["country", "year", "value"]].rename(columns={"value": "d1"})
total = fiscal[fiscal["transaction"] == "_T"][["country", "year", "value"]].rename(columns={"value": "total"})
merged = d1.merge(total, on=["country", "year"])
merged["value"] = merged["d1"] / merged["total"] * 100
merged = merged[merged["country"] != "FRA"]
payload["peers"] = peer_series(merged[["country", "year", "value"]])
```

In both files, update the `methodology` field text to note:
> Peer values from OECD Government at a Glance 2025; OECD_AVG is the unweighted mean of {DEU, ESP, GBR, ITA, NLD, SWE}. Peer series starts 2007 (OECD data limit).

- [ ] **Verify both processors**

```bash
cd backend
source .venv/bin/activate
python -m processors.kpi_allocation
python -m processors.kpi_overhead
python -c "
import json
for kpi in ['kpi_productive_spend', 'kpi_overhead_rate']:
    d = json.load(open(f'data/output/{kpi}.json'))
    print(kpi, 'peer keys:', list(d['peers'].keys()))
"
```

### Step 5: Wire `kpi_friction_ratio.peers`

- [ ] **Edit `backend/processors/kpi_friction.py`**

Friction's peer proxy: administrative spend (GF01+GF02+GF03) as % of total APU expenditure. Same construction as productive-spend peer, with a different numerator:

```python
from processors import peer_series, load_oecd_long

cofog = load_oecd_long("oecd_cofog")
top10 = cofog[cofog["expenditure"].str.match(r"GF0[1-9]$|GF10$")]
totals = top10.groupby(["country", "year"])["value"].sum().rename("total").reset_index()
admin = top10[top10["expenditure"].isin(["GF01", "GF02", "GF03"])]
admin_sum = admin.groupby(["country", "year"])["value"].sum().rename("admin").reset_index()
merged = totals.merge(admin_sum, on=["country", "year"])
merged["value"] = merged["admin"] / merged["total"] * 100
merged = merged[merged["country"] != "FRA"]
payload["peers"] = peer_series(merged[["country", "year", "value"]])
```

Update the methodology field with the same OECD note as in Step 4, and explicitly note that the OECD-derived friction proxy is the administrative-COFOG share — narrower than the France-side definition (which includes derived debt-interest pieces) and therefore not strictly comparable in level, only in trend.

### Step 6: Re-run full pipeline + commit

- [ ] **Re-run pipeline; spot-check meta + each peer block**

```bash
cd backend
source .venv/bin/activate
python run_pipeline.py --mode annual --no-upload
python -c "
import json
for kpi in ['kpi_overhead_rate','kpi_friction_ratio','kpi_productive_spend','kpi_sustainability']:
    d = json.load(open(f'data/output/{kpi}.json'))
    print(f'{kpi}: peers={list(d[\"peers\"].keys())}, OECD_AVG_first={d[\"peers\"].get(\"OECD_AVG\",[None])[0] if d[\"peers\"].get(\"OECD_AVG\") else None}')
"
```

- [ ] **Commit (one for the helper, one per processor, one for CLAUDE.md)**

Mirror the 7a/7b/7c precedent — one commit per substantive change keeps git history bisectable. Bundle the helper with `kpi_sustainability` if you want fewer commits.

Sample commit messages:
- `Session 9a — processors: add load_oecd_long + peer_series helpers`
- `Session 9b — kpi_sustainability: wire OECD deficit peers`
- `Session 9c — kpi_overhead + kpi_allocation: wire OECD peers`
- `Session 9d — kpi_friction: wire OECD admin-COFOG peer proxy`
- `CLAUDE.md: record Session 9 runtime discoveries`

In the CLAUDE.md entry, document:
- The exact `TRANSACTION` code used for B9 (whatever Step 1 found).
- The fact that `OECD_AVG` is unweighted across 6 peers (FRA excluded from its own peer average).
- Year coverage of each peer series (OECD's 2007 floor is below PRD's 1995 wish but is an upstream limit; explicitly flag).
- Any per-country gaps (NLD often has missing years for some COFOG sub-functions).

---

## Session 10 — `kpi_outcomes`: health (life expectancy) + education (PISA)

### Background

PRD §5.9 specifies two outcome KPIs, both still empty placeholders (`france: []`, `peers: {}`):
- **Health:** Assurance Maladie spend per capita **vs. life expectancy**, France and peers, indexed to OECD avg = 100.
- **Education:** spend per pupil **vs. PISA scores**, France and peers, with **triennial PISA interpolated linearly** between survey years and marked `"interpolated": true` (PRD §5 note).

Sources: OECD Data Explorer. The 2025 Government at a Glance edition's COFOG dataflow gives us GF07 (Health) and GF09 (Education) spend already. The *outcome* side needs two new OECD dataflows:
- **Life expectancy at birth** — likely `OECD.ELS.HD,DSD_HEALTH_STAT@DF_LE` or `DF_LE_BIRTH`. Confirm via the catalog probe in Step 1.
- **PISA scores** (reading, math, science) — likely `OECD.EDU.IMEP,DSD_PISA@DF_PISA`. Confirm in Step 1.

Per capita spend requires population data — also OECD (`DSD_DP_LIVE`) or use INSEE BDM `gdp_nominal` divided by per-capita GDP from OECD. **Simpler approach** consistent with the PRD's framing: skip per-capita normalization and report **spend as % of GDP** (already in the OECD COFOG raw) **vs. life-expectancy in years** / **PISA score**. The indexed-to-100 transform happens in the processor.

### Files

- Modify: `backend/fetchers/oecd.py` — add `fetch_oecd_life_expectancy()` and `fetch_oecd_pisa()`
- Modify: `backend/processors/kpi_outcomes.py` — replace the placeholder body with the real computation
- Modify: `backend/run_pipeline.py` — register the two new fetchers in `run_annual()`
- May modify: `backend/processors/__init__.py` — if a `linear_interpolate(series, target_years)` helper is worth extracting

### Step 1: Discover the two dataflow IDs

- [ ] **Find life expectancy and PISA dataflows in the OECD catalog**

```bash
cd backend
source .venv/bin/activate
python <<'PY'
import requests
from fetchers import DEFAULT_HEADERS
# Catalog search via the dataflow listing
for q in ["DF_HEALTH_STAT", "DF_LE", "DF_PISA"]:
    url = f"https://sdmx.oecd.org/public/rest/dataflow/all/{q}/latest"
    r = requests.get(url, headers={**DEFAULT_HEADERS, "Accept":"application/vnd.sdmx.structure+json;version=1.0"}, timeout=60)
    print(q, '->', r.status_code, r.url)
PY
```

If neither query hits, fall back to the OECD's web UI (https://data-explorer.oecd.org) — search "Life expectancy at birth" and "PISA", read the dataflow ID off the URL.

Expected: confirm IDs (record them in CLAUDE.md). Note their key dimensions (likely `FREQ.REF_AREA.MEASURE.SEX.AGE…` for life expectancy and `FREQ.REF_AREA.SUBJECT.GENDER…` for PISA).

### Step 2: Add the two fetchers

- [ ] **Append to `backend/fetchers/oecd.py`**

Mirror the existing `fetch_oecd_cofog` shape. Take the dataflow ID and the key filter from Step 1. Cache as `data/raw/oecd_life_expectancy_{date}.json` and `data/raw/oecd_pisa_{date}.json`. Respect the 3-second inter-call sleep.

- [ ] **Verify each runs standalone**

```bash
cd backend
source .venv/bin/activate
python -c "from fetchers.oecd import fetch_oecd_life_expectancy as f; df=f(); print('LE:', df.shape, df.head(3))"
python -c "from fetchers.oecd import fetch_oecd_pisa as f; df=f(); print('PISA:', df.shape, df.head(3))"
```

### Step 3: Rewrite `compute_outcomes` to produce the two payload blocks

- [ ] **Replace `backend/processors/kpi_outcomes.py::compute_outcomes()` body**

Sketch (concrete TRANSACTION/SUBJECT codes filled in from Step 1):

```python
from processors import load_oecd_long, peer_series, write_output, now_iso

def _interpolate_triennial(years_with_values: list[tuple[int, float]], target_years: list[int]) -> list[dict]:
    """
    Linearly interpolate between PISA survey years.
    Returns [{"year": Y, "value": V, "interpolated": True|False}, ...]
    for every year in target_years that falls inside the survey range.
    """
    pts = sorted(years_with_values)
    out = []
    for y in target_years:
        # exact hit?
        exact = next((v for ys, v in pts if ys == y), None)
        if exact is not None:
            out.append({"year": y, "value": round(float(exact), 2), "interpolated": False})
            continue
        # find bracketing survey years
        before = [(ys, v) for ys, v in pts if ys < y]
        after = [(ys, v) for ys, v in pts if ys > y]
        if not before or not after:
            continue  # extrapolation not done (PRD says "between" survey years)
        (y0, v0), (y1, v1) = before[-1], after[0]
        v = v0 + (v1 - v0) * (y - y0) / (y1 - y0)
        out.append({"year": y, "value": round(float(v), 2), "interpolated": True})
    return out


def compute_outcomes() -> dict:
    cofog = load_oecd_long("oecd_cofog")
    le = load_oecd_long("oecd_life_expectancy")
    pisa = load_oecd_long("oecd_pisa")

    # ---- Health block ----
    health_spend = cofog[cofog["expenditure"] == "GF07"][["country", "year", "value"]]
    # life expectancy: filter to total population (Step 1's SEX=_T, AGE=Y0 etc.)
    life = le.copy()  # adjust filters per Step 1's discovery
    health_block = _build_outcome_block(health_spend, life, value_label="life_expectancy_years")

    # ---- Education block ----
    edu_spend = cofog[cofog["expenditure"] == "GF09"][["country", "year", "value"]]
    # PISA: SUBJECT=COMBINED or take mean of reading/math/science per country/year
    pisa_combined = pisa.copy()  # adjust per Step 1's discovery
    target_years = sorted(edu_spend["year"].unique())
    pisa_interp = {
        country: _interpolate_triennial(
            list(zip(sub["year"], sub["value"])), target_years
        )
        for country, sub in pisa_combined.groupby("country")
    }
    education_block = _build_outcome_block(edu_spend, pisa_combined, value_label="pisa_score", interpolated_overlay=pisa_interp)

    payload = {
        "kpi_id": "outcomes",
        "kpi_name": "Spend vs. Outcome",
        "description": "Public spend on Health and Education set against the OECD's outcome measures (life expectancy at birth; PISA average score). PISA is triennial and linearly interpolated between survey years; interpolated points carry interpolated=true.",
        "unit": "mixed",
        "source": "OECD GIP 2025 (COFOG, % of GDP) + OECD Health Statistics + OECD PISA",
        "methodology": "...",
        "last_updated": now_iso(),
        "health": health_block,
        "education": education_block,
    }
    write_output("kpi_outcomes.json", payload)
    return payload
```

`_build_outcome_block` is a small helper you write in the same file — it just emits `{"france": [{year, spend_pct_gdp, <value_label>}], "peers": peer_series(...)}`. Keep it local to `kpi_outcomes.py`; don't generalize yet.

### Step 4: Register the new fetchers in `run_pipeline.py`

- [ ] **Edit `backend/run_pipeline.py::run_annual()`**

Add right after `_run_step("oecd_fiscal", fetch_oecd_fiscal, sources)`:

```python
_run_step("oecd_life_expectancy", fetch_oecd_life_expectancy, sources)
_run_step("oecd_pisa", fetch_oecd_pisa, sources)
```

And add the corresponding imports at the top.

### Step 5: Verify end-to-end and commit

- [ ] **Run pipeline, inspect output**

```bash
cd backend
source .venv/bin/activate
python run_pipeline.py --mode annual --no-upload
python -c "
import json
d = json.load(open('data/output/kpi_outcomes.json'))
print('health france pts:', len(d['health']['france']))
print('education france pts:', len(d['education']['france']))
print('interpolated PISA pts (FRA, first 5):',
    [p for p in d['education']['france'] if p.get('interpolated')][:5])
"
```

Expected: France series populated for both blocks; interpolated PISA values present for non-survey years.

- [ ] **Commit + CLAUDE.md update**

Three commits: `Session 10a — oecd: add life-expectancy + PISA fetchers`, `Session 10b — kpi_outcomes: real computation with PISA interpolation`, `CLAUDE.md: record Session 10 runtime discoveries`.

CLAUDE.md entry should list:
- The two dataflow IDs (with their dimension orders, like the Session 7b note).
- The PISA SUBJECT code(s) used and how "combined" was constructed.
- The life-expectancy filter (SEX/AGE codes).
- The interpolation rule (linear between bracketing survey years, no extrapolation outside).

---

## Session 11 — PLF "dépenses fiscales" fetcher (unblock `kpi_tax_expenditure`)

> **RESOLVED (Session 9, 2026-05-20): NOT BUILT — no costed tabular data exists.**
> Step 1's catalog probe was executed and hit the "skip" branch: only an
> uncosted 468-row list and an 8-row top-IR snapshot are published; the full
> chiffrage is PDF-only. `kpi_tax_expenditure` stays `skipped`. The two
> fallback paths (option 2: parse the Tome II PDF; option 3: headline aggregate
> only) are documented in detail in CLAUDE.md's Session 9 Runtime-discoveries
> entry. Do not re-attempt a tabular fetcher — it does not exist upstream.

### Background

PRD §3.6 and §5.8 spec the Tax Expenditure Cost KPI: total cost of niches fiscales / total tax revenues × 100. Currently `compute_tax_expenditure()` in `kpi_outcomes.py` raises `NotImplementedError` (Session 5 deferral). The data is published annually by Bercy in the PLF's **"Voies et moyens — Tome II"** annex (released ~September–October each year), available via data.gouv.fr or data.economie.gouv.fr.

**Risk (flagged in Session 7d):** PLRG datasets went PDF-only between Sessions 6 and 7. The Voies-et-moyens annex *may* have the same fate. Step 1 below probes for tabular availability and decides whether to proceed or skip.

### Files

- Create: `backend/fetchers/plf_depenses_fiscales.py`
- Modify: `backend/processors/kpi_outcomes.py` — implement `compute_tax_expenditure()` (currently raises)
- Modify: `backend/run_pipeline.py` — register the new fetcher (already calls `compute_tax_expenditure`)

### Step 1: Discover the dataset and its format

- [ ] **Search data.economie.gouv.fr and data.gouv.fr catalogs**

```bash
cd backend
source .venv/bin/activate
python <<'PY'
import requests
from fetchers import DEFAULT_HEADERS
# data.economie.gouv.fr
for base, q in [
    ("https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets", "depenses fiscales"),
    ("https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets", "voies et moyens"),
    ("https://www.data.gouv.fr/api/1/datasets", "depenses fiscales"),
    ("https://www.data.gouv.fr/api/1/datasets", "voies et moyens tome II"),
]:
    if "data.gouv" in base:
        r = requests.get(base, params={"q": q, "page_size": 8}, headers=DEFAULT_HEADERS, timeout=30)
        items = r.json().get("data", [])
        print(f'\n== data.gouv.fr / {q!r} ({len(items)} hits)')
        for d in items:
            res_fmts = sorted(set((r.get("format") or "").lower() for r in d.get("resources",[])))
            print(f'  - {d.get("slug","")[:60]} | fmts={res_fmts}')
    else:
        r = requests.get(base, params={"where": f'title like "{q}"', "limit": 8}, headers=DEFAULT_HEADERS, timeout=30)
        items = r.json().get("results", [])
        print(f'\n== data.economie / {q!r} ({len(items)} hits)')
        for d in items:
            print(f'  - {d.get("dataset_id","")[:60]}')
PY
```

**Decision point:**
- If a CSV/Excel resource exists with annual cost-by-tax-expenditure: proceed to Step 2.
- If only PDF or aggregate snapshots: **stop the session, raise `NotImplementedError` in the fetcher with a precise note (matching the PLRG pattern from Session 7d), update CLAUDE.md, and call it a day**. No partial implementation.

### Step 2: Write the fetcher

- [ ] **Create `backend/fetchers/plf_depenses_fiscales.py`**

Pattern: same as `fetchers/france_travail.py` (data.gouv.fr resource resolution + download). Cache the raw under `data/raw/plf_depenses_fiscales_*.json`. Return a `DataFrame` with at minimum: `tax_expenditure_id`, `name`, `year`, `cost_eur_millions`, `beneficiary_count` (if present).

Expected columns vary year-to-year — keep the fetcher loose (return the raw normalized records), do the column selection in the processor.

- [ ] **Verify standalone**

```bash
cd backend
source .venv/bin/activate
python -m fetchers.plf_depenses_fiscales
```

### Step 3: Implement `compute_tax_expenditure()`

- [ ] **Replace the `NotImplementedError` body in `backend/processors/kpi_outcomes.py`**

Aggregate cost per year. Total tax revenue denominator comes from INSEE BDM — pull from `series["total_apu_expenditure"]`'s sibling: the resolver doesn't currently expose total tax revenue. **Two options**:
- (a) Add a `total_tax_revenue` rule to `SERIES_SEARCH_RULES` (Session 8's family — likely OPERATION=D2+D5+D61 aggregate, or a directly-published total).
- (b) Approximate via OECD `DSD_GOV_TRANSACTION` revenue indicator if Step 1 of Session 9 surfaced it.

Pick (a) if the INSEE family exposes a clean total; (b) otherwise. Document the choice in the methodology field.

Output structure per PRD §5.8: `count`, `total_cost_eur_billions`, `ratio_to_revenue_pct`, year-on-year `latest` block, no peers (peer dépenses fiscales are not collected uniformly).

- [ ] **Verify**

```bash
cd backend
source .venv/bin/activate
python -m processors.kpi_outcomes
python -c "import json; d=json.load(open('data/output/kpi_tax_expenditure.json')); print(d.get('france',[])[-3:])"
```

### Step 4: Wire the fetcher into `run_pipeline.py` and commit

- [ ] **Edit `backend/run_pipeline.py::run_annual()`**

Insert `_run_step("plf_depenses_fiscales", fetch_plf_depenses_fiscales, sources)` between the OECD fetches and the existing `_run_step("kpi_tax_expenditure", ...)` (so the processor reads from the freshly-cached raw).

- [ ] **Re-run full pipeline; confirm `kpi_tax_expenditure` flips from `skipped` to `ok`**

```bash
cd backend
source .venv/bin/activate
python run_pipeline.py --mode annual --no-upload
python -c "import json; print(json.load(open('data/output/meta.json'))['sources']['kpi_tax_expenditure'])"
```

- [ ] **Commit** — three commits matching prior cadence (fetcher, processor, CLAUDE.md).

CLAUDE.md entry should list the resolved dataset ID, resource URL pattern, and the chosen revenue denominator (a or b above).

---

## Session 12 — VPS deployment: cron + R2 upload verification

### Background

PRD §2.4 specifies systemd timers (monthly 1st @ 06:00; annual Feb 1 @ 06:00) running on a Hetzner VPS, with the pipeline uploading to a Cloudflare R2 bucket consumed by the (future) frontend. Today: R2 upload code is implemented in `backend/publishers/r2_upload.py` but **never verified live** (every prior run used `--no-upload`). No timer units exist. This session ships the deployment.

The PRD also implies a **second annual run in June** for the PLF / "Voies et moyens" annex (typically published ~September–October — the June timer is a backstop; align it to the actual publication when known). Confirm timer slots with the user before installing.

### Files

- Create (on VPS, **not committed**): `/etc/systemd/system/fisoscope-monthly.{service,timer}`
- Create (on VPS, **not committed**): `/etc/systemd/system/fisoscope-annual.{service,timer}`
- Create: `backend/.env` on the VPS (filled with R2 credentials — never committed)
- Create: `docs/deployment.md` — a short runbook covering the systemd install, R2 setup, and how to inspect logs (this *is* committed)
- May modify: `backend/publishers/r2_upload.py` — add a dry-run / list-only mode if helpful for the first upload (optional)

### Step 1: Verify R2 credentials end-to-end from the VPS

- [ ] **From the VPS shell, populate `.env` and run a single-file upload smoke test**

```bash
ssh <vps>  # done by the human operator
cd ~/french-efficiency-dashboard/backend
cp ../.env.example .env  # then edit with the four R2 vars
source .venv/bin/activate
python -c "
from publishers.r2_upload import get_r2_client
from config import R2_BUCKET_NAME
c = get_r2_client()
resp = c.list_objects_v2(Bucket=R2_BUCKET_NAME, MaxKeys=5)
print('list ok:', resp.get('KeyCount'), 'objects')
"
```

Expected: `list ok: 0 objects` (empty bucket on first run) or a non-zero count. Any boto3 exception here is a credentials/bucket-name problem — fix before proceeding.

### Step 2: Run the pipeline with upload enabled and inspect the bucket

- [ ] **Full live run (drops `--no-upload`)**

```bash
cd backend
source .venv/bin/activate
python run_pipeline.py --mode full
```

Expected log line per file: `Uploaded {kpi_xxx.json}`. After the run, confirm all 9 JSON outputs (the 8 from Session 10/11 + `meta.json`) appear in R2:

```bash
python -c "
from publishers.r2_upload import get_r2_client
from config import R2_BUCKET_NAME
c = get_r2_client()
for o in c.list_objects_v2(Bucket=R2_BUCKET_NAME).get('Contents', []):
    print(o['Key'], o['Size'], o['LastModified'])
"
```

Open one file through the R2 public URL (`$R2_PUBLIC_URL/meta.json`) in a browser — it must parse as JSON.

### Step 3: Install systemd units

- [ ] **Write the four unit files on the VPS**

`/etc/systemd/system/fisoscope-monthly.service`:

```ini
[Unit]
Description=fisc-o-scope monthly pipeline
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=fisoscope
WorkingDirectory=/home/fisoscope/french-efficiency-dashboard/backend
EnvironmentFile=/home/fisoscope/french-efficiency-dashboard/.env
ExecStart=/home/fisoscope/french-efficiency-dashboard/backend/.venv/bin/python run_pipeline.py --mode monthly
StandardOutput=journal
StandardError=journal
```

`/etc/systemd/system/fisoscope-monthly.timer`:

```ini
[Unit]
Description=Run fisc-o-scope monthly pipeline on the 1st of each month
Requires=fisoscope-monthly.service

[Timer]
OnCalendar=*-*-01 06:00:00
Persistent=true
RandomizedDelaySec=900

[Install]
WantedBy=timers.target
```

The two annual units mirror this with `--mode annual` and `OnCalendar=*-02-01 06:00:00` (plus a second `fisoscope-plf.timer` at `*-10-15 06:00:00` if the PLF annex publication date is known by then — otherwise skip).

- [ ] **Enable and check the timers**

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fisoscope-monthly.timer fisoscope-annual.timer
systemctl list-timers --all | grep fisoscope
```

Expected: both timers listed with non-zero `NEXT` and `LEFT` fields.

### Step 4: Trigger one timed run manually and read the journal

- [ ] **Manual trigger to confirm the systemd plumbing works**

```bash
sudo systemctl start fisoscope-monthly.service
journalctl -u fisoscope-monthly.service -n 100 --no-pager
```

Expected: full pipeline run log, ending with `Pipeline complete` and `Uploaded meta.json`. Any failure here points to env-file path, working directory, or python interpreter path — fix in the `.service` file.

### Step 5: Commit the runbook

- [ ] **Write `docs/deployment.md`**

Include: VPS user setup, `.env` template (without secrets), the four unit files verbatim, `systemctl enable` commands, log inspection commands (`journalctl -u fisoscope-monthly -f`), R2 public URL location, rollback procedure (`sudo systemctl disable --now fisoscope-*.timer`).

- [ ] **Commit + CLAUDE.md update**

```bash
git add docs/deployment.md
git commit -m "Session 12 — deployment runbook + systemd timer units

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

CLAUDE.md entry: note the live R2 bucket name, the public URL host, and the timer schedules. Flag any deviations from PRD §2.4 (e.g., the PLF timer if added).

---

## Open follow-ups (separate plans needed)

- **Frontend (PRD Phase 2 — §11.2).** Vite + React + Recharts SPA on Cloudflare Pages, reading `meta.json` and the eight KPI JSONs from R2. This is a fundamentally different subsystem (different language, tooling, deployment target) and needs its own brainstorm + plan. Suggested next move: invoke `superpowers:brainstorming` for the frontend, then `superpowers:writing-plans` to produce `docs/superpowers/plans/YYYY-MM-DD-frontend-phase-2.md`. Do not start frontend work until Session 12 is green — otherwise the dashboard will show stale data and broken charts.

- **OECD year-coverage floor (2007 vs. PRD's 1995).** The OECD Government at a Glance 2025 fiscal/COFOG dataflows start at 2007. France-side INSEE series do go back to 1995; the dashboard will be 1995→present for France-only series and 2007→present for any peer-overlaid chart. This is an upstream limit, not a fix — just document it in the frontend's chart axes.

- **Sub-monthly PLF refresh schedule.** If the PLF "Voies et moyens" annex publication date varies year-to-year, replace Session 12's hardcoded `*-10-15` timer with a polling job (daily for one month) or a manual trigger. Defer until at least one annual cycle of observation.
