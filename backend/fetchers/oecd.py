import logging
import time
from io import StringIO

import pandas as pd
import requests

from config import INSEE_START_YEAR, OECD_COUNTRIES, OECD_START_YEAR
from fetchers import DEFAULT_HEADERS, save_raw

log = logging.getLogger(__name__)
OECD_BASE = "https://sdmx.oecd.org/public/rest/data"

# Dataset IDs reference the 2025 Government at a Glance edition — update when 2027 ships.
FISCAL_DATASET = "OECD.GOV.GIP,DSD_GOV_TRANSACTION@DF_GOV_TRANSACTION_2025"

# Life expectancy (OECD Health Statistics). The DSD_HEALTH_STAT structure has 13
# dimensions in this order:
#   REF_AREA . FREQ . MEASURE . UNIT_MEASURE . AGE . SEX . SOCIO_ECON_STATUS .
#   DEATH_CAUSE . CALC_METHODOLOGY . GESTATION_THRESHOLD . HEALTH_STATUS .
#   DISEASE . CANCER_SITE
# Key below pins France / annual / life-expectancy / years / at-birth / total
# and wildcards the 7 trailing dimensions (→ 12 dots total).
LIFE_EXPECTANCY_DATASET = "OECD.ELS.HD,DSD_HEALTH_STAT@DF_LE"
LIFE_EXPECTANCY_KEY = "FRA.A.LFEXP.Y.Y0._T......."

# The 2025-edition transaction DSD exposes 8 key dimensions in this order:
#   FREQ . REF_AREA . MEASURE . UNIT_MEASURE . SECTOR . TRANSACTION . EDITION . CATEGORY
# Filter must therefore contain 7 dots. UNIT_MEASURE=PT_B1GQ selects "% of GDP"
# (B1GQ is the SDMX code for GDP at market prices); the legacy PT_GDP code is gone.
UNIT_PCT_GDP = "PT_B1GQ"

# Public finance main indicators (Government at a Glance 2025), DSD_GOV — 7 dims:
#   FREQ . REF_AREA . MEASURE . UNIT_MEASURE . SECTOR . EDITION . CATEGORY  (→ 6 dots)
# MEASURE carries the indicator: GNLB = general-government net lending/borrowing
# (the deficit), GGDM = Maastricht gross debt. Both at PT_B1GQ (% of GDP), S13.
# Session B note: the plan's assumed dataflows were wrong for % of GDP —
# DSD_GOV_FIN_INSTR exposes only "% of total debt"/USD-PPP, and SDD.NAD TABLE12
# is a 135 MB unfiltered pull. DSD_GOV yields both peer series cleanly from one
# GIP dataflow, consistent with the existing transaction fetcher. GGDM
# (Maastricht) matches France's own INSEE Maastricht-debt series; GGD (SNA gross
# debt) runs ~12pp higher and would not be level-comparable.
PUBLIC_FINANCE_DATASET = "OECD.GOV.GIP,DSD_GOV@DF_GOV_PF_2025"
DEFICIT_KEY = f"A.{'+'.join(OECD_COUNTRIES)}.GNLB.{UNIT_PCT_GDP}.S13.."
DEBT_KEY = f"A.{'+'.join(OECD_COUNTRIES)}.GGDM.{UNIT_PCT_GDP}.S13.."

# Revenue Statistics (roadmap S5), DSD_REV_COMP_OECD — 7 dims, REF_AREA first:
#   REF_AREA . MEASURE . SECTOR . STANDARD_REVENUE . CTRY_SPECIFIC_REVENUE . UNIT_MEASURE . FREQ
# TAX_REV / S13 / _T / _T / PT_B1GQ = total tax revenue, general government, % of GDP.
# OECD_REP is the OECD's own aggregate ("OECD average"), not a mean computed here.
TAX_REVENUE_DATASET = "OECD.CTP.TPS,DSD_REV_COMP_OECD@DF_RSOECD"
TAX_REVENUE_KEY = f"{'+'.join(OECD_COUNTRIES)}+OECD_REP.TAX_REV.S13._T._T.{UNIT_PCT_GDP}.A"
TAX_REVENUE_START_YEAR = 1965

# Government at a Glance 2025 — public employment (roadmap S6), DSD_GOV — 7 dims
# (FREQ . REF_AREA . MEASURE . UNIT_MEASURE . SECTOR . EDITION . CATEGORY). Only
# FREQ and REF_AREA are pinned; the dataflow also carries representation
# indicators, so the processor keeps MEASURE=EMPG, UNIT_MEASURE=PT_EMP (share of
# total employment). It publishes no OECD aggregate (checked 2026-11-08).
PUBLIC_EMPLOYMENT_DATASET = "OECD.GOV.GIP,DSD_GOV@DF_GOV_EMPPS_REP_2025"
PUBLIC_EMPLOYMENT_KEY = f"A.{'+'.join(OECD_COUNTRIES)}......"

# OECD rate limit is 20 requests/minute — pause between calls.
RATE_LIMIT_SLEEP = 3


def _fetch_oecd_csv(dataset: str, filter_expr: str, start_year: int) -> pd.DataFrame:
    """Fetch a single OECD SDMX dataset slice as CSV, respecting the rate limit."""
    url = f"{OECD_BASE}/{dataset}/{filter_expr}"
    params = {"startPeriod": str(start_year), "format": "csvfilewithlabels"}
    log.info(f"Fetching OECD dataset {dataset} (filter: {filter_expr})")
    response = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=60)
    response.raise_for_status()
    time.sleep(RATE_LIMIT_SLEEP)
    return pd.read_csv(StringIO(response.text))


def fetch_oecd_fiscal(countries: list[str] = None, start_year: int = OECD_START_YEAR) -> pd.DataFrame:
    """Fetch fiscal balance, revenue and expenditure indicators for the peer countries."""
    countries = countries or OECD_COUNTRIES
    filter_expr = f"A.{'+'.join(countries)}..{UNIT_PCT_GDP}...."
    df = _fetch_oecd_csv(FISCAL_DATASET, filter_expr, start_year)
    save_raw("oecd_fiscal", df.to_dict(orient="records"))
    return df


def fetch_oecd_deficit(start_year: int = OECD_START_YEAR) -> pd.DataFrame:
    """Fetch general-government net lending/borrowing (% of GDP) for the peer set."""
    df = _fetch_oecd_csv(PUBLIC_FINANCE_DATASET, DEFICIT_KEY, start_year)
    save_raw("oecd_deficit", df.to_dict(orient="records"))
    return df


def fetch_oecd_debt(start_year: int = OECD_START_YEAR) -> pd.DataFrame:
    """Fetch general-government Maastricht gross debt (% of GDP) for the peer set."""
    df = _fetch_oecd_csv(PUBLIC_FINANCE_DATASET, DEBT_KEY, start_year)
    save_raw("oecd_debt", df.to_dict(orient="records"))
    return df


def fetch_oecd_life_expectancy(start_year: int = INSEE_START_YEAR) -> pd.DataFrame:
    """
    Fetch France life expectancy at birth (total population), annual, in years.
    Defaults to INSEE_START_YEAR (1995) to span the same range as the
    INSEE-sourced health-spend series it is compared against.
    """
    df = _fetch_oecd_csv(LIFE_EXPECTANCY_DATASET, LIFE_EXPECTANCY_KEY, start_year)
    save_raw("oecd_life_expectancy", df.to_dict(orient="records"))
    return df


def fetch_oecd_tax_revenue() -> pd.DataFrame:
    """Fetch total tax revenue (% of GDP), peers + OECD aggregate, since 1965."""
    df = _fetch_oecd_csv(TAX_REVENUE_DATASET, TAX_REVENUE_KEY, TAX_REVENUE_START_YEAR)
    save_raw("oecd_tax_revenue", df.to_dict(orient="records"))
    return df


def fetch_oecd_public_employment() -> pd.DataFrame:
    """Fetch public employment and representation indicators (GaaG 2025) for the peer set."""
    df = _fetch_oecd_csv(PUBLIC_EMPLOYMENT_DATASET, PUBLIC_EMPLOYMENT_KEY, OECD_START_YEAR)
    save_raw("oecd_public_employment", df.to_dict(orient="records"))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    fiscal = fetch_oecd_fiscal()
    print(f"\nOECD fiscal: {len(fiscal)} rows, {fiscal.shape[1]} columns")
    deficit = fetch_oecd_deficit()
    print(f"OECD deficit: {len(deficit)} rows, {deficit.shape[1]} columns")
    debt = fetch_oecd_debt()
    print(f"OECD debt: {len(debt)} rows, {debt.shape[1]} columns")
    le = fetch_oecd_life_expectancy()
    print(f"OECD life expectancy: {len(le)} rows, {le.shape[1]} columns")
    tax = fetch_oecd_tax_revenue()
    print(f"OECD tax revenue: {len(tax)} rows, {tax.shape[1]} columns")
    emp = fetch_oecd_public_employment()
    print(f"OECD public employment: {len(emp)} rows, {emp.shape[1]} columns")
