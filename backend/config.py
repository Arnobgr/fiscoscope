import os

# INSEE BDM series idBanks are NOT hardcoded here.
# They are resolved at pipeline startup by fetchers/insee_idbank_resolver.py,
# which downloads INSEE's official mapping file and writes resolved idBanks to
# data/raw/insee_idbanks.json. All INSEE fetchers load from that file.
#
# Logical series names used throughout the pipeline:
#   wage_bill_apu, social_benefits, fiscal_balance, debt_interest,
#   total_apu_expenditure, gdp_nominal, cpi, population, public_debt_ratio,
#   public_debt_eur
# COFOG (functional) series come from Eurostat — see fetchers/eurostat.py.

# OECD
OECD_COUNTRIES = ["FRA", "DEU", "GBR", "ITA", "ESP", "NLD", "SWE"]
OECD_START_YEAR = 2000

# Start year for annual national-accounts series (INSEE, Eurostat: from 1995)
INSEE_START_YEAR = 1995

# Data paths (relative to backend/)
RAW_DATA_DIR = "data/raw"
OUTPUT_DATA_DIR = "data/output"

# API server (FastAPI — see PRD §8). Read from the environment; in production
# the systemd unit / `uvicorn --env-file` supplies these.
# ALLOWED_ORIGINS: comma-separated list of browser origins allowed by CORS
#   (e.g. "https://fiscoscope.pages.dev"). Empty = no cross-origin reads.
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()
]
# RATE_LIMIT: slowapi limit string applied globally to every endpoint.
RATE_LIMIT = os.environ.get("RATE_LIMIT", "60/minute")

