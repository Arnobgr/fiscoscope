"""Fiscoscope read-only API — serves the pipeline's output JSON over HTTP.

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

app = FastAPI(title="Fiscoscope API", docs_url=None, redoc_url=None)
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
    """Validate `name`, then read OUTPUT_DIR/<name>.json or raise 404."""
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
