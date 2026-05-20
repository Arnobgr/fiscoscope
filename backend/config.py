import os

# INSEE BDM series idBanks are NOT hardcoded here.
# They are resolved at pipeline startup by fetchers/insee_idbank_resolver.py,
# which downloads INSEE's official mapping file and writes resolved idBanks to
# data/raw/insee_idbanks.json. All INSEE fetchers load from that file.
#
# Logical series names used throughout the pipeline:
#   wage_bill_apu, public_investment, social_benefits, fiscal_balance,
#   debt_interest, total_apu_expenditure, gdp_nominal, cpi,
#   cofog_gf01 through cofog_gf10

# OECD
OECD_COUNTRIES = ["FRA", "DEU", "GBR", "ITA", "ESP", "NLD", "SWE"]
OECD_START_YEAR = 2000

# INSEE start year for COFOG (available from 1995)
INSEE_START_YEAR = 1995

# Data paths (relative to backend/)
RAW_DATA_DIR = "data/raw"
OUTPUT_DATA_DIR = "data/output"

# Cloudflare R2 (loaded from environment via .env)
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "")  # e.g. https://pub-xxx.r2.dev

# COFOG bucket classification (logical names matching keys in insee_idbanks.json)
COFOG_PRODUCTIVE = ["cofog_gf04", "cofog_gf05", "cofog_gf06"]
COFOG_REDISTRIBUTIVE = ["cofog_gf07", "cofog_gf08", "cofog_gf09", "cofog_gf10"]
COFOG_ADMINISTRATIVE = ["cofog_gf01", "cofog_gf02", "cofog_gf03"]

# GF09 (Education) spans both productive and redistributive buckets.
# The pipeline uses its dominant component rule: classified as redistributive,
# but flagged in output metadata as an approximation.
