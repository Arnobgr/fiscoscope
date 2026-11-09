"""
Fetcher: State performance indicators (PAP/RAP) from data.economie.gouv.fr —
roadmap 3.1. One raw source per dataset:

- performance_summary: the official share of targets met / improved / not
  improved / not reported, one row per RAP year since 2007 (fixed id).
- performance_detail: every sub-indicator 2022–2024 with target, result and
  attainment, one schema with an `annee` column (fixed id).
- performance_rap_YYYY: one dataset per later RAP vintage. Their ids are
  unpredictable (`performance-de-la-depense` is the RAP 2024,
  `performance-de-la-depense-rap-2025`…) and their columns year-stamped, so
  they are discovered via the catalog search and their year is read from the
  `atteinte_de_la_cible_YYYY` field name, never from the id. Years already in
  performance_detail are skipped (same rows).
"""

import logging
import re

import requests

from fetchers import DEFAULT_HEADERS, fetch_ods_records, save_raw

log = logging.getLogger(__name__)

BASE = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets"
SUMMARY_ID = "performance-atteinte-de-la-cible-generale-du-budget-de-l-etat-depuis-2007"
DETAIL_ID = (
    "performance-execution-et-atteinte-de-la-cible-du-budget-de-l-etat-"
    "jusqu-au-niveau-sous-indicateur"
)
STATUS_FIELD = re.compile(r"^atteinte_de_la_cible_(\d{4})$")


def _export_json(dataset_id: str) -> list:
    """Whole dataset in one request (the records endpoint pages 100 rows at a time)."""
    response = requests.get(
        f"{BASE}/{dataset_id}/exports/json", headers=DEFAULT_HEADERS, timeout=120
    )
    response.raise_for_status()
    return response.json()


def discover_rap_vintages() -> dict[int, str]:
    """{RAP year: dataset_id} for every catalog dataset with an atteinte_de_la_cible_YYYY field."""
    response = requests.get(
        BASE,
        params={"where": 'search("performance")', "limit": 100},
        headers=DEFAULT_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    vintages: dict[int, str] = {}
    for dataset in response.json()["results"]:
        for field in dataset.get("fields", []):
            match = STATUS_FIELD.match(field["name"])
            if not match:
                continue
            year = int(match.group(1))
            if year in vintages:
                raise ValueError(
                    f"Two datasets claim RAP {year}: {vintages[year]} and "
                    f"{dataset['dataset_id']} — pick one before fetching."
                )
            vintages[year] = dataset["dataset_id"]
    if not vintages:
        raise RuntimeError(
            "No RAP performance vintage found in the catalog (no dataset with an "
            "atteinte_de_la_cible_YYYY field): the portal has changed, check it."
        )
    return vintages


def fetch_performance() -> None:
    """Fetch the summary, the 2022–2024 detail and every later RAP vintage; save each raw."""
    summary = fetch_ods_records(BASE, SUMMARY_ID)
    save_raw("performance_summary", summary)

    detail = _export_json(DETAIL_ID)
    save_raw("performance_detail", detail)
    covered = {int(r["annee"]) for r in detail if r.get("annee")}

    for year, dataset_id in sorted(discover_rap_vintages().items()):
        if year in covered:
            log.info(f"RAP {year} ({dataset_id}) already in {DETAIL_ID}: skipped")
            continue
        log.info(f"Fetching RAP {year}: {dataset_id}")
        save_raw(
            f"performance_rap_{year}",
            {"dataset_id": dataset_id, "records": _export_json(dataset_id)},
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    fetch_performance()
