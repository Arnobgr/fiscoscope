"""fisc-o-scope pipeline entry point — see PRD §6.

Modes:
  monthly  — budget execution + Urssaf + Unédic, then the monthly KPI.
  annual   — INSEE idBank resolver, all INSEE/OECD/PLRG fetches, then every
             annual KPI processor.
  full     — annual then monthly. Used for initial setup.

Each fetcher and processor runs inside _run_step, which records its outcome
in the meta.json sources block but never aborts the pipeline — one source
outage should not block the others. Known gaps documented in CLAUDE.md
(e.g. compute_tax_expenditure raising NotImplementedError) surface as
status: skipped.
"""

from pathlib import Path

from dotenv import load_dotenv

# Load .env before importing config so R2 credentials are picked up.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import argparse
import json
import logging
from datetime import datetime, timezone

from config import OUTPUT_DATA_DIR
from fetchers.budget_execution import fetch_monthly_execution, fetch_plrg_execution
from fetchers.insee_bdm import fetch_all_insee_series
from fetchers.insee_idbank_resolver import run_idbank_resolver
from fetchers.oecd import fetch_oecd_cofog, fetch_oecd_fiscal
from fetchers.unedic import fetch_unedic_allocataires
from fetchers.urssaf import fetch_urssaf_wage_bill
from processors.kpi_allocation import compute_pension_investment, compute_productive_spend
from processors.kpi_friction import compute_friction_ratio
from processors.kpi_monthly import compute_monthly_execution
from processors.kpi_outcomes import compute_outcomes, compute_tax_expenditure
from processors.kpi_overhead import compute_overhead_rate
from processors.kpi_sustainability import compute_fiscal_sustainability
from publishers.r2_upload import upload_all_outputs

PIPELINE_VERSION = "1.0.0"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_step(name: str, fn, sources: dict, *args, **kwargs) -> None:
    """Run one fetcher/processor and record its outcome in `sources`."""
    log.info(f"→ {name}")
    try:
        fn(*args, **kwargs)
        sources[name] = {"last_fetched": _now(), "status": "ok"}
    except NotImplementedError as e:
        log.warning(f"{name} skipped: {e}")
        sources[name] = {"last_fetched": _now(), "status": "skipped", "error": str(e)}
    except Exception as e:
        log.exception(f"{name} failed")
        sources[name] = {"last_fetched": _now(), "status": "error", "error": str(e)}


def write_meta(mode: str, sources: dict) -> Path:
    """Write data/output/meta.json — see PRD §9."""
    out_dir = Path(OUTPUT_DATA_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(p.name for p in out_dir.glob("*.json") if p.name != "meta.json")
    meta = {
        "last_run": _now(),
        "pipeline_version": PIPELINE_VERSION,
        "mode": mode,
        "sources": sources,
        "output_files": ["meta.json", *files],
    }
    path = out_dir / "meta.json"
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    log.info(f"Wrote meta.json ({len(files) + 1} output files)")
    return path


def run_monthly(sources: dict) -> None:
    log.info("=== monthly pipeline ===")
    _run_step("budget_execution", fetch_monthly_execution, sources)
    _run_step("urssaf", fetch_urssaf_wage_bill, sources)
    _run_step("unedic", fetch_unedic_allocataires, sources)
    _run_step("kpi_monthly_execution", compute_monthly_execution, sources)


def run_annual(sources: dict) -> None:
    log.info("=== annual pipeline ===")
    # Step 0: resolve INSEE idBanks before any INSEE fetch (see PRD §3.1.1).
    _run_step("insee_idbanks", run_idbank_resolver, sources)
    _run_step("insee_bdm", fetch_all_insee_series, sources)
    _run_step("oecd_cofog", fetch_oecd_cofog, sources)
    _run_step("oecd_fiscal", fetch_oecd_fiscal, sources)
    _run_step(
        "budget_plrg", fetch_plrg_execution, sources, datetime.now().year - 1
    )
    _run_step("kpi_overhead_rate", compute_overhead_rate, sources)
    _run_step("kpi_friction_ratio", compute_friction_ratio, sources)
    _run_step("kpi_productive_spend", compute_productive_spend, sources)
    _run_step("kpi_pension_investment", compute_pension_investment, sources)
    _run_step("kpi_sustainability", compute_fiscal_sustainability, sources)
    _run_step("kpi_outcomes", compute_outcomes, sources)
    _run_step("kpi_tax_expenditure", compute_tax_expenditure, sources)


def main() -> None:
    parser = argparse.ArgumentParser(description="fisc-o-scope pipeline")
    parser.add_argument(
        "--mode", choices=["monthly", "annual", "full"], default="full"
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip the R2 upload step (for local dry runs).",
    )
    args = parser.parse_args()

    sources: dict = {}
    if args.mode in ("annual", "full"):
        run_annual(sources)
    if args.mode in ("monthly", "full"):
        run_monthly(sources)

    write_meta(args.mode, sources)

    if args.no_upload:
        log.info("Skipping R2 upload (--no-upload)")
    else:
        try:
            upload_all_outputs()
        except Exception:
            log.exception("R2 upload failed")

    log.info("Pipeline complete")


if __name__ == "__main__":
    main()
