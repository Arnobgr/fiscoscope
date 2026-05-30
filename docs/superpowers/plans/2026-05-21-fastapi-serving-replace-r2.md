# FastAPI Serving (replace R2 upload) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Cloudflare R2 upload step with a small always-on FastAPI app on the VPS that serves the pipeline's `data/output/*.json` over read-only HTTP, consumed by a Cloudflare Pages frontend.

**Architecture:** The cron pipeline is unchanged — it still writes `data/output/*.json`. A new `backend/api.py` (FastAPI + uvicorn) serves those files read-only via `/api/meta`, `/api/kpis`, `/api/kpi/{name}`, plus `/healthz`. Abuse is bounded by `slowapi` rate limiting (in-app) and an OS firewall (deploy-time, out of scope here); a CORS allowlist restricts browser cross-origin reads to the frontend origin. HTTPS is terminated externally via an `<ip>.sslip.io` Let's Encrypt cert (deploy-time, out of scope). The R2 publisher, its `run_pipeline.py` wiring, the R2 config vars, and the `boto3` dependency are removed.

**Tech Stack:** Python 3.12, FastAPI, uvicorn[standard], slowapi (rate limiting), pytest + httpx (tests). The data layer is plain JSON files on disk — no SQLite, no object storage.

**Scope of this pass (user-confirmed):** API code + retire R2 + docs only. Deployment artifacts (Caddyfile/systemd/ufw/sslip.io) are explicitly **out of scope** — the user deploys with their existing sslip.io method.

**Decisions locked in earlier discussion (do not relitigate):**
- JSON-direct (FastAPI reads the ~80 KB output files), not SQLite.
- "Only the frontend can call the API" is **not** a goal — it's impossible for a public SPA + public API, and unnecessary because the data is public. CORS is for *enabling* the frontend (cosmetic as a control); rate limiting + firewall do the real abuse protection.
- sslip.io + firewall + rate limiting is the deploy model. No custom domain.

---

## File Structure

| File | Responsibility | Change |
|------|----------------|--------|
| `backend/api.py` | FastAPI read-only server over `data/output/*.json` | **Create** |
| `backend/tests/test_api.py` | API endpoint tests (TestClient) | **Create** |
| `backend/config.py` | Constants + env config | **Modify** — drop R2 vars, add `ALLOWED_ORIGINS`, `RATE_LIMIT` |
| `backend/run_pipeline.py` | Pipeline orchestrator | **Modify** — remove R2 import, `--no-upload` flag, upload block |
| `backend/publishers/r2_upload.py` | Old R2 publisher | **Delete** (and the `publishers/` dir if it ends up empty) |
| `backend/requirements.txt` | Runtime deps | **Modify** — remove `boto3`, add `fastapi`, `uvicorn[standard]`, `slowapi` |
| `backend/requirements-dev.txt` | Test deps | **Create** — `pytest`, `httpx` |
| `PRD.md` | Spec | **Modify** — §2.1 diagram, §2.2, §6.1 step, §7.1 config block, §8 (R2→API), §9 checklist + frontend, constraint #6 |
| `CLAUDE.md` | Session memory | **Modify** — overview bullet, repo layout, run instructions, Session-6 note, new Session-E note |

---

## Task 1: Retire the R2 publisher and rewire the orchestrator

Done first so nothing imports R2 config vars before Task 2 removes them, and each commit leaves the repo runnable.

**Files:**
- Delete: `backend/publishers/r2_upload.py`
- Modify: `backend/run_pipeline.py` (lines 50, 156-160, 171-177, and the comment at 20)

- [ ] **Step 1: Delete the R2 publisher and prune the package if empty**

```bash
cd backend
rm publishers/r2_upload.py
ls -A publishers/
# If the only remaining file is __init__.py (and it is empty), remove the package:
[ "$(ls -A publishers/ | grep -v '^__init__.py$')" = "" ] && \
  [ ! -s publishers/__init__.py ] && rm -rf publishers/ && echo "removed empty publishers/"
```

- [ ] **Step 2: Remove the R2 import from `run_pipeline.py`**

Delete this line (currently line 50):

```python
from publishers.r2_upload import upload_all_outputs
```

- [ ] **Step 3: Remove the `--no-upload` argparse flag**

Delete this block (currently lines 156-160):

```python
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip the R2 upload step (for local dry runs).",
    )
```

- [ ] **Step 4: Remove the upload block in `main()`**

Replace this block (currently lines 171-177):

```python
    if args.no_upload:
        log.info("Skipping R2 upload (--no-upload)")
    else:
        try:
            upload_all_outputs()
        except Exception:
            log.exception("R2 upload failed")

    log.info("Pipeline complete")
```

with just:

```python
    log.info("Pipeline complete")
```

- [ ] **Step 5: Update the dotenv comment (keep `load_dotenv`)**

`load_dotenv` is retained so a local `.env` can supply API settings for dev; only the comment is now inaccurate. Replace (currently lines 20-21):

```python
# Load .env before importing config so R2 credentials are picked up.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
```

with:

```python
# Load .env (if present) before importing config, so any env-driven settings
# (e.g. API ALLOWED_ORIGINS / RATE_LIMIT) are available during local runs.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
```

- [ ] **Step 6: Verify the orchestrator still parses and imports cleanly**

Run: `cd backend && python run_pipeline.py --help`
Expected: usage text listing only `--mode {monthly,annual,full}` — **no** `--no-upload`. Exit code 0. (This imports every fetcher/processor and `config`, confirming nothing references the deleted publisher.)

- [ ] **Step 7: Commit**

```bash
cd /home/arnobgr/french-efficiency-dashboard
git add -A
git commit -m "refactor: remove R2 publisher and upload wiring from pipeline"
```

---

## Task 2: Swap R2 config for API config

**Files:**
- Modify: `backend/config.py` (lines 24-29)

- [ ] **Step 1: Replace the R2 config block with API config**

Replace (currently lines 24-29):

```python
# Cloudflare R2 (loaded from environment via .env)
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "")  # e.g. https://pub-xxx.r2.dev
```

with:

```python
# API server (FastAPI — see PRD §8). Read from the environment; in production
# the systemd unit / `uvicorn --env-file` supplies these.
# ALLOWED_ORIGINS: comma-separated list of browser origins allowed by CORS
#   (e.g. "https://fiscoscope.pages.dev"). Empty = no cross-origin reads.
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()
]
# RATE_LIMIT: slowapi limit string applied globally to every endpoint.
RATE_LIMIT = os.environ.get("RATE_LIMIT", "60/minute")
```

(`import os` at the top of the file stays — it's still used.)

- [ ] **Step 2: Verify config imports and exposes the new names**

Run: `cd backend && python -c "import config; print(config.ALLOWED_ORIGINS, config.RATE_LIMIT)"`
Expected: `[] 60/minute` (no `ALLOWED_ORIGINS` set in the env), exit 0. No `AttributeError`, no leftover `R2_*`.

- [ ] **Step 3: Commit**

```bash
cd /home/arnobgr/french-efficiency-dashboard
git add backend/config.py
git commit -m "refactor: replace R2 config vars with API ALLOWED_ORIGINS/RATE_LIMIT"
```

---

## Task 3: Dependencies

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`

- [ ] **Step 1: Install the new runtime + test deps and capture exact versions**

```bash
cd backend
source .venv/bin/activate
pip uninstall -y boto3
pip install fastapi "uvicorn[standard]" slowapi pytest httpx
python -c "import fastapi, uvicorn, slowapi, pytest, httpx; \
print('fastapi', fastapi.__version__); \
print('uvicorn', uvicorn.__version__); \
print('slowapi', slowapi.__version__); \
print('pytest', pytest.__version__); \
print('httpx', httpx.__version__)"
```

Note the five printed versions — use them verbatim in the next two steps. (Per CLAUDE.md's pinning rule, any version printed by a fresh `pip install` is the current stable and satisfies the ≥1-week rule.)

- [ ] **Step 2: Edit `requirements.txt` — remove boto3, add runtime deps**

Remove this line:

```
boto3==1.43.6
```

Append (substitute the exact versions printed in Step 1; the values below are the expected stable line as of 2026-05 — replace if `pip` resolved differently):

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
slowapi==0.1.9
```

- [ ] **Step 3: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest==8.3.4
httpx==0.28.1
```

(Again: substitute the exact `pytest` / `httpx` versions printed in Step 1 if different.)

- [ ] **Step 4: Verify a clean resolve from the pinned files**

Run: `cd backend && pip install -r requirements-dev.txt`
Expected: "Requirement already satisfied" for every line, no resolver errors, no `boto3` reinstall.

- [ ] **Step 5: Commit**

```bash
cd /home/arnobgr/french-efficiency-dashboard
git add backend/requirements.txt backend/requirements-dev.txt
git commit -m "build: drop boto3, add fastapi/uvicorn/slowapi + pytest/httpx"
```

---

## Task 4: FastAPI serving app (TDD)

**Files:**
- Create: `backend/tests/test_api.py`
- Create: `backend/api.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_api.py`:

```python
import json

import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Point the app at a temp output dir with two sample files."""
    (tmp_path / "meta.json").write_text(
        json.dumps({"mode": "full", "sources": {}, "output_files": []})
    )
    (tmp_path / "kpi_overhead_rate.json").write_text(
        json.dumps({"france": [{"year": 2025, "value": 22.3}]})
    )
    monkeypatch.setattr(api, "OUTPUT_DIR", tmp_path)
    return TestClient(api.app)


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_meta(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    assert r.json()["mode"] == "full"


def test_list_kpis_excludes_meta(client):
    r = client.get("/api/kpis")
    assert r.status_code == 200
    assert r.json() == {"kpis": ["kpi_overhead_rate"]}


def test_get_kpi(client):
    r = client.get("/api/kpi/kpi_overhead_rate")
    assert r.status_code == 200
    assert r.json()["france"][0]["year"] == 2025


def test_get_kpi_missing_returns_404(client):
    r = client.get("/api/kpi/does_not_exist")
    assert r.status_code == 404


def test_get_kpi_invalid_name_returns_404(client):
    # Uppercase fails the ^[a-z0-9_]+$ guard — never touches the filesystem.
    r = client.get("/api/kpi/Bad-Name")
    assert r.status_code == 404


def test_get_kpi_meta_blocked(client):
    # meta is served at /api/meta only, not via the generic KPI route.
    r = client.get("/api/kpi/meta")
    assert r.status_code == 404
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_api.py -v`
Expected: collection error / FAIL — `ModuleNotFoundError: No module named 'api'`.

- [ ] **Step 3: Write the FastAPI app**

Create `backend/api.py`:

```python
"""fiscoscope read-only API — serves the pipeline's output JSON over HTTP.

Replaces the former R2 publisher (see PRD §8). The frontend (Cloudflare Pages)
fetches these endpoints. The data is public, so there is no authentication;
abuse is bounded by slowapi rate limiting (here) plus an OS firewall (deploy).

Run from the backend/ directory:

    ALLOWED_ORIGINS="https://your-frontend.pages.dev" \
        uvicorn api:app --host 127.0.0.1 --port 8000 --proxy-headers
"""

import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from config import ALLOWED_ORIGINS, OUTPUT_DATA_DIR, RATE_LIMIT

# Module-level so tests can monkeypatch it to a temp directory.
OUTPUT_DIR = Path(OUTPUT_DATA_DIR)

# KPI/file names are restricted to this charset; anything else 404s before any
# filesystem access (prevents path traversal via the {name} path param).
_NAME_RE = re.compile(r"^[a-z0-9_]+$")

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])

app = FastAPI(title="fiscoscope API", docs_url=None, redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# Order matters: SlowAPI added first (inner), CORS added last so it is the
# outermost middleware and tags every response — including 429s — with the
# CORS headers the browser needs.
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _load(name: str) -> dict:
    """Read OUTPUT_DIR/<name>.json or raise 404. `name` is already validated."""
    if not _NAME_RE.fullmatch(name):
        raise HTTPException(status_code=404, detail="not found")
    path = OUTPUT_DIR / f"{name}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"{name} not found")
    return json.loads(path.read_text())


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/api/meta")
def get_meta():
    return _load("meta")


@app.get("/api/kpis")
def list_kpis():
    names = sorted(p.stem for p in OUTPUT_DIR.glob("*.json") if p.stem != "meta")
    return {"kpis": names}


@app.get("/api/kpi/{name}")
def get_kpi(name: str):
    if name == "meta":
        raise HTTPException(status_code=404, detail="not found")
    return _load(name)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/arnobgr/french-efficiency-dashboard
git add backend/api.py backend/tests/test_api.py
git commit -m "feat: add FastAPI read-only server for pipeline output JSON"
```

---

## Task 5: Update PRD.md and CLAUDE.md

Documentation must match the new architecture. PRD §6.1/§7.1 contain *illustrative* code blocks that are already out of sync with the real files (they predate Sessions 7–D); only their R2 references are touched here — a full code re-sync is out of scope.

**Files:**
- Modify: `PRD.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: PRD §2.1 — replace the architecture diagram**

Replace the diagram + `### 2.2` block (currently lines 35-72) with:

````markdown
```
┌─────────────────────────────────────────────────────────────┐
│                      VPS (Hetzner)                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Python data pipeline (cron-scheduled)               │  │
│  │  - Fetches raw data from public APIs                 │  │
│  │  - Normalizes and stores raw data locally            │  │
│  │  - Computes KPIs                                     │  │
│  │  - Writes output JSON files to data/output/          │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI app (uvicorn, always-on)                    │  │
│  │  - Serves data/output/*.json read-only over HTTP     │  │
│  │  - CORS-restricted to the frontend origin            │  │
│  │  - Rate-limited (slowapi)                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ HTTPS via <ip>.sslip.io (Let's Encrypt)
                          │ fetch() at page load
                          ▼
┌─────────────────────────────────────────────────────────────┐
│         Cloudflare Pages (frontend — Phase 2)               │
│         Vite + React + Recharts                             │
│         Static site, deployed from GitHub                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Backend API (FastAPI)

The VPS runs a small always-on FastAPI app (served by uvicorn) that exposes the
pipeline's pre-computed `data/output/*.json` over read-only HTTP. The frontend
(Cloudflare Pages) fetches these endpoints. The data is public, so the API needs
no authentication; abuse is bounded by `slowapi` rate limiting and an OS
firewall, and a CORS allowlist restricts browser cross-origin reads to the
frontend origin. HTTPS is provided by a Let's Encrypt certificate on an
`<ip>.sslip.io` hostname — no custom domain required.

Endpoints:
- `GET /healthz` — liveness check
- `GET /api/meta` — pipeline run metadata (`meta.json`)
- `GET /api/kpis` — list of available KPI names
- `GET /api/kpi/{name}` — one KPI's JSON

This replaces the original R2-upload design; the pipeline no longer pushes to
object storage.
````

- [ ] **Step 2: PRD §6.1 — fix the pipeline-step description and illustrative block**

In the numbered list, replace step 5 (currently line 948):

```
5. Calls the R2 uploader to sync all files in `data/output/` to the R2 bucket
```

with:

```
5. Writes all output to `data/output/`, which the always-on FastAPI app (`api.py`) serves over HTTP — there is no upload step
```

Then in the illustrative code block below it, delete the import line (currently 968):

```python
from publishers.r2_upload import upload_all_outputs
```

and delete the two upload calls (currently lines 980 and 999):

```python
    upload_all_outputs(prefix="monthly")
```
```python
    upload_all_outputs(prefix="annual")
```

- [ ] **Step 3: PRD §7.1 — replace the R2 block in the illustrative config**

Replace (currently lines 1054-1060):

```python
# Cloudflare R2 (loaded from environment)
import os
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "")  # e.g. https://pub-xxx.r2.dev
```

with:

```python
# API server (FastAPI), loaded from environment
import os
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()
]
RATE_LIMIT = os.environ.get("RATE_LIMIT", "60/minute")
```

Also, if the `.env.example` block just below it (around lines 1071-1075) lists `R2_*` variables, replace those lines with:

```
ALLOWED_ORIGINS=https://your-frontend.pages.dev
RATE_LIMIT=60/minute
```

- [ ] **Step 4: PRD §8 — replace "R2 Upload" with the API section**

Open PRD §8 (starts at `## 8. R2 Upload`, line ~1080) and replace the entire section — everything from `## 8. R2 Upload` up to (but not including) the next `## 9.` heading — with:

````markdown
## 8. Serving the Output (FastAPI)

### 8.1 `api.py`

A small always-on FastAPI app serves the pipeline's `data/output/*.json` over
read-only HTTP. It is launched separately from the cron pipeline (e.g. a systemd
unit running uvicorn). The data is public; there is no authentication.

```python
# api.py (abridged — see the file for the full source)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from config import ALLOWED_ORIGINS, OUTPUT_DATA_DIR, RATE_LIMIT

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])
app = FastAPI(title="fiscoscope API", docs_url=None, redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                   allow_methods=["GET"], allow_headers=["*"])
```

Endpoints: `GET /healthz`, `GET /api/meta`, `GET /api/kpis`,
`GET /api/kpi/{name}`.

### 8.2 Running it

```bash
cd backend
ALLOWED_ORIGINS="https://your-frontend.pages.dev" \
    uvicorn api:app --host 127.0.0.1 --port 8000 --proxy-headers
```

`--proxy-headers` lets uvicorn read `X-Forwarded-For` from the reverse proxy so
slowapi rate-limits on the real client IP. TLS, the reverse proxy, the
`<ip>.sslip.io` hostname, and the firewall are deployment concerns handled on
the VPS (not in this repo).
````

- [ ] **Step 5: PRD §9 — fix the checklist and frontend notes**

Replace the checklist line (currently ~1205):

```
- [ ] Implement R2 uploader
```

with:

```
- [ ] Implement FastAPI serving app (`api.py`)
```

Replace the frontend data-source line (currently ~1214):

```
- Fetches JSON from R2 `pub-xxx.r2.dev` URLs
```

with:

```
- Fetches JSON from the VPS FastAPI app (e.g. `https://<ip>.sslip.io/api/...`)
```

- [ ] **Step 6: PRD — fix the secrets constraint (#6, ~line 1234)**

Replace:

```
6. **No secrets in code or git.** All R2 credentials are loaded from environment variables via `.env`. The `.env` file must be in `.gitignore`.
```

with:

```
6. **No secrets in code or git.** The pipeline needs no secrets (all data sources are public). The API reads only non-secret settings (`ALLOWED_ORIGINS`, `RATE_LIMIT`) from the environment. `.env` remains in `.gitignore`.
```

- [ ] **Step 7: CLAUDE.md — project overview bullet**

Replace:

```
- No backend API — frontend fetches pre-computed static JSON from R2
```

with:

```
- Backend API: a small FastAPI app on the VPS serves pre-computed static JSON
  over read-only HTTP; the frontend (Cloudflare Pages) fetches it. HTTPS via an
  `<ip>.sslip.io` Let's Encrypt cert (no custom domain).
```

- [ ] **Step 8: CLAUDE.md — repository layout**

In the layout tree, replace the `publishers/` block:

```
│   ├── publishers/
│   │   └── r2_upload.py               # Upload output JSON to Cloudflare R2
```

with an `api.py` entry near `run_pipeline.py` (and drop the `publishers/` block, since the package was removed):

```
│   ├── api.py                         # FastAPI read-only server for data/output/*.json
```

- [ ] **Step 9: CLAUDE.md — "Running the pipeline locally"**

Replace the `.env` copy line:

```bash
cp ../.env.example .env   # fill in R2 credentials
```

with:

```bash
# No secrets needed — all data sources are public. The API reads optional
# ALLOWED_ORIGINS / RATE_LIMIT from the environment.
```

And after the "Full pipeline run" block, add:

````markdown
# Serve the output over HTTP (separate always-on process):
ALLOWED_ORIGINS="https://your-frontend.pages.dev" \
    uvicorn api:app --host 127.0.0.1 --port 8000 --proxy-headers
````

- [ ] **Step 10: CLAUDE.md — fix the stale `--no-upload` mention in the Session 6 note**

In the "Session 6 — orchestrator is fail-soft" bullet, replace:

```
`run_pipeline.py` has a `--no-upload` flag and calls `load_dotenv()` from the repo-root `.env` *before* importing `config`.
```

with:

```
`run_pipeline.py` calls `load_dotenv()` from the repo-root `.env` *before* importing `config`. (The `--no-upload` flag and the R2 publisher were removed in Session E — output is now served by `api.py`, not uploaded.)
```

- [ ] **Step 11: CLAUDE.md — add the Session E runtime-discovery note**

Append a new bullet to the Runtime-discoveries notes (after the Session D block, before "Known gaps"):

```markdown
- **Session E (2026-05-21) — R2 retired; output now served by a FastAPI app.**
  Decision (user): drop the Cloudflare R2 upload entirely and serve the ~80 KB
  `data/output/*.json` directly from a small always-on FastAPI app on the VPS.
  This reverses the PRD's original "no backend API / static JSON from R2" design.
    - **New `backend/api.py`** (FastAPI + uvicorn): read-only endpoints
      `/healthz`, `/api/meta`, `/api/kpis`, `/api/kpi/{name}`, reading
      `OUTPUT_DATA_DIR`. CORS allowlist (`config.ALLOWED_ORIGINS`) + global
      `slowapi` rate limit (`config.RATE_LIMIT`, default `60/minute`). KPI names
      are regex-guarded (`^[a-z0-9_]+$`) against path traversal. `OUTPUT_DIR` is
      module-level so tests monkeypatch it. Tests in `backend/tests/test_api.py`
      (pytest + FastAPI TestClient).
    - **Removed:** `publishers/r2_upload.py` (+ the now-empty `publishers/`),
      its `run_pipeline.py` import / `--no-upload` flag / upload block, the
      `R2_*` vars in `config.py`, and `boto3` from `requirements.txt`. Added
      `fastapi`, `uvicorn[standard]`, `slowapi` (runtime) and a
      `requirements-dev.txt` with `pytest`, `httpx`.
    - **Deploy model (not in this repo):** Cloudflare Pages frontend →
      `<ip>.sslip.io` (Let's Encrypt) → uvicorn, with `ufw` (only 80/443+SSH)
      and rate limiting. "Only the frontend can call the API" is *not* a goal —
      impossible for a public SPA + public API, and unneeded for public data;
      CORS only enables the frontend, rate-limit + firewall bound abuse.
    - The first live deployment + the frontend (Phase 2) remain to be built.
```

- [ ] **Step 12: Verify the docs have no dangling R2 references**

Run: `cd /home/arnobgr/french-efficiency-dashboard && grep -rniE 'r2|boto3|no-upload|no backend api' PRD.md CLAUDE.md`
Expected: any remaining hits are only inside *historical* session notes (e.g. Sessions 6/7 prep describing past work) — not in the live architecture sections (§2, §6 step 5, §7.1, §8, §9, constraints) or the overview/layout/run sections of CLAUDE.md. If a live section still mentions R2, fix it.

- [ ] **Step 13: Commit**

```bash
cd /home/arnobgr/french-efficiency-dashboard
git add PRD.md CLAUDE.md
git commit -m "docs: update PRD and CLAUDE.md for FastAPI serving (replace R2)"
```

---

## Task 6: Full verification

Confirms the whole change holds together: tests pass, the pipeline still runs, and the live server answers real requests over the real `data/output/`.

**Files:** none (verification only).

- [ ] **Step 1: Tests pass**

Run: `cd backend && python -m pytest tests/ -v`
Expected: 7 passed.

- [ ] **Step 2: Orchestrator still imports and parses**

Run: `cd backend && python run_pipeline.py --help`
Expected: usage with only `--mode`, exit 0.

- [ ] **Step 3: Launch the server against the real output dir**

```bash
cd backend
ALLOWED_ORIGINS="https://example.pages.dev" \
    uvicorn api:app --host 127.0.0.1 --port 8000 &
sleep 2
```

- [ ] **Step 4: Hit every endpoint and check the CORS header**

```bash
curl -s -o /dev/null -w "healthz %{http_code}\n" http://127.0.0.1:8000/healthz
curl -s -o /dev/null -w "meta %{http_code}\n"    http://127.0.0.1:8000/api/meta
curl -s http://127.0.0.1:8000/api/kpis
curl -s -o /dev/null -w "overhead %{http_code}\n" http://127.0.0.1:8000/api/kpi/kpi_overhead_rate
curl -s -o /dev/null -w "missing %{http_code}\n"  http://127.0.0.1:8000/api/kpi/nope
# CORS: allowed origin should be echoed back
curl -s -D - -o /dev/null -H "Origin: https://example.pages.dev" \
    http://127.0.0.1:8000/api/meta | grep -i access-control-allow-origin
```

Expected: `healthz 200`, `meta 200`, a JSON `{"kpis":[...]}` listing the 10 KPI files (no `meta`), `overhead 200`, `missing 404`, and an `access-control-allow-origin: https://example.pages.dev` header.

- [ ] **Step 5: Stop the server**

```bash
kill %1 2>/dev/null
```

- [ ] **Step 6 (optional, network-dependent): full pipeline still produces output**

Run: `cd backend && python run_pipeline.py --mode annual`
Expected: completes, `data/output/meta.json` updates, every step `ok`/`skipped` (no `error` from the removed upload path; `budget_plrg` stays `skipped`). Skip if offline — Steps 1-4 already prove the serving path against the existing cached output.

---

## Self-Review

**Spec coverage** (against the confirmed scope — "API + retire R2 + docs"):
- API built (Task 4); JSON-direct, CORS, rate limiting ✓
- R2 retired: publisher deleted, run_pipeline rewired (Task 1), config vars (Task 2), boto3 (Task 3) ✓
- Docs: PRD §2/§6/§7/§8/§9 + constraints, CLAUDE.md overview/layout/run/session notes (Task 5) ✓
- Deployment artifacts deliberately excluded (out of scope) ✓

**Placeholder scan:** dependency versions are resolved by an actual `pip install` + version-print command (Task 3 Step 1) with concrete fallback pins; no "TBD"/"handle edge cases"/"similar to" left. PRD §8 wholesale-replace gives full replacement content. ✓

**Type/name consistency:** `OUTPUT_DIR` (module global, monkeypatched in tests) and `_load`/`_NAME_RE` are defined in `api.py` (Task 4) and referenced consistently in tests and the §8 abridged block. `ALLOWED_ORIGINS` / `RATE_LIMIT` defined in `config.py` (Task 2) and imported by `api.py` (Task 4) under the same names. Endpoint paths (`/healthz`, `/api/meta`, `/api/kpis`, `/api/kpi/{name}`) match across api.py, tests, PRD §2.2/§8, and Task 6 curls. ✓
