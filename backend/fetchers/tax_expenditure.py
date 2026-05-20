"""
Fetcher: GTED (Global Tax Expenditures Database) — France tax-expenditure cost
time series. Feeds the Tax Expenditure Cost KPI (PRD §5.8).

France's official full costed list (PLF "Voies et Moyens — Tome II") is PDF-only
(Session 9). GTED republishes the same data in tabular form: a per-provision
revenue-forgone (cost) time series, mirrored on Zenodo as an annual XLSX. We
fetch from Zenodo — the gted.net site is behind a Cloudflare JS challenge that
`requests` cannot pass, but Zenodo is not. The Zenodo *concept* record always
resolves to the newest published version, so no version id is hardcoded.

Licence: CC-BY-4.0. Attribution required — cite Redonda, A., von Haldenwang, C.,
& Aliu, F., Global Tax Expenditures Database (GTED), Tax Expenditures Lab,
concept DOI 10.5281/zenodo.5940165. GTED is a third-party academic compilation
of France's own PLF figures; its provision count and revenue-forgone definition
differ slightly from the official Tome II.
"""

import io
import logging

import pandas as pd
import requests

from fetchers import DEFAULT_HEADERS, save_raw

log = logging.getLogger(__name__)

# GTED Zenodo concept record — /versions/latest always points at the newest
# release, so the per-version record id never needs hardcoding.
ZENODO_CONCEPT_ID = "5940165"
ZENODO_LATEST = f"https://zenodo.org/api/records/{ZENODO_CONCEPT_ID}/versions/latest"
# The costed long table: one row per (country, provision, year) with revenue
# forgone in local currency (EUR for France), USD, % of GDP and % of tax.
REVENUE_SHEET = "RevenueForgone"
COUNTRY = "FRA"
# Columns kept from the sheet — drop the free-text Note and constant Country to
# keep the cache lean; these are everything the KPI processor consumes.
KEEP_COLUMNS = [
    "ProvisionID",
    "Year",
    "RF (LCU)",
    "Projection/Estimate",
    "RF % of GDP",
    "RF % of Tax",
]


def _resolve_latest_xlsx_url() -> str:
    """Resolve the newest GTED XLSX download URL from the Zenodo concept record."""
    meta = requests.get(ZENODO_LATEST, headers=DEFAULT_HEADERS, timeout=60)
    meta.raise_for_status()
    files = meta.json().get("files", [])
    xlsx = next((f for f in files if f["key"].lower().endswith(".xlsx")), None)
    if not xlsx:
        raise ValueError(
            f"No .xlsx in the latest GTED Zenodo record. Files: {[f['key'] for f in files]}"
        )
    return xlsx["links"]["self"]


def fetch_tax_expenditure() -> pd.DataFrame:
    """
    Fetch France's tax-expenditure (revenue-forgone) cost series from GTED.
    Returns the RevenueForgone rows for FRA: one row per (provision, year), the
    cost in EUR ('RF (LCU)') plus % of GDP / % of tax and a projection flag.
    """
    url = _resolve_latest_xlsx_url()
    log.info(f"Downloading GTED database from {url}")
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=300, allow_redirects=True)
    resp.raise_for_status()

    df = pd.read_excel(
        io.BytesIO(resp.content), engine="openpyxl", sheet_name=REVENUE_SHEET
    )
    fra = df[df["Country"] == COUNTRY][KEEP_COLUMNS].reset_index(drop=True)
    if fra.empty:
        raise ValueError(f"No {COUNTRY} rows in GTED {REVENUE_SHEET} sheet.")
    save_raw("tax_expenditure", fra.to_dict(orient="records"))
    return fra


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    df = fetch_tax_expenditure()
    print(
        f"\nGTED France tax expenditure: {len(df)} rows, "
        f"{int(df['Year'].min())}–{int(df['Year'].max())}, "
        f"{df['ProvisionID'].nunique()} provisions"
    )
