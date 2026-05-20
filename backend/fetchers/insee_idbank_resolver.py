import io
import json
import logging
import re
import zipfile
from pathlib import Path

import pandas as pd
import requests

from config import RAW_DATA_DIR
from fetchers import DEFAULT_HEADERS

log = logging.getLogger(__name__)

METADATA_URL = "https://www.insee.fr/fr/information/2862759"
ZIP_FILENAME_RE = re.compile(
    r"(/fr/statistiques/fichier/2862759/\d{6}_correspondance_idbank_dimension\.zip)"
)

# Each entry: logical_name -> list of (dimension, value) filters that must ALL match.
# Dimension `famille` is a top-level CSV column; every other dimension is decoded
# positionally from the row's `list_var` / `list_mod` pair.
#
# Key dimensions:
#   PERIODICITE: A=annual, M=monthly, T=quarterly
#   SECT-INST: S13=all APU, S0=economy-wide, etc.
#   OPERATION (CNT-2020-CSI): D1=compensation of employees, OTE=total expenditure,
#                             P5K2=gross capital formation, D62=cash social benefits,
#                             B9NF=net lending/borrowing, D41=interest paid
#   FONCTION (CNA-2014-DEP-APU only): FON01..FON10=COFOG functions
#   COMPTE (CNT-2020-CSI): E=emplois (uses), R=ressources, SO=neither (balance lines)
#
# APU aggregates use CNT-2020-CSI (quarterly, base 2020, freshness through current
# quarter); annual_values() aggregates 4 quarters and drops incomplete years.
# CNA-2020-DEP-APU does not exist in the INSEE mapping (only CNA-2020-PIB and
# CNA-2020-CSI as ratios), so the COFOG functional breakdown (FON01..FON10)
# stays on CNA-2014-DEP-APU (frozen at 2020). Post-2020 COFOG is stitched in
# from OECD GIP 2025 at the processor layer — see processors/cofog.py.
SERIES_SEARCH_RULES = {
    # --- APU aggregate accounts (CNT-2020-CSI, quarterly, base 2020) ---
    "wage_bill_apu": [
        ("famille", "CNT-2020-CSI"),
        ("PERIODICITE", "T"),
        ("SECT-INST", "S13"),
        ("OPERATION", "D1"),
        ("COMPTE", "E"),
    ],
    "public_investment": [
        ("famille", "CNT-2020-CSI"),
        ("PERIODICITE", "T"),
        ("SECT-INST", "S13"),
        ("OPERATION", "P5K2"),
        ("COMPTE", "E"),
    ],
    "social_benefits": [
        ("famille", "CNT-2020-CSI"),
        ("PERIODICITE", "T"),
        ("SECT-INST", "S13"),
        ("OPERATION", "D62"),
        ("COMPTE", "E"),
    ],
    "total_apu_expenditure": [
        ("famille", "CNT-2020-CSI"),
        ("PERIODICITE", "T"),
        ("SECT-INST", "S13"),
        ("OPERATION", "OTE"),
        ("COMPTE", "E"),
    ],
    "fiscal_balance": [
        ("famille", "CNT-2020-CSI"),
        ("PERIODICITE", "T"),
        ("SECT-INST", "S13"),
        ("OPERATION", "B9NF"),
        ("COMPTE", "SO"),
    ],
    "debt_interest": [
        ("famille", "CNT-2020-CSI"),
        ("PERIODICITE", "T"),
        ("SECT-INST", "S13"),
        ("OPERATION", "D41"),
        ("COMPTE", "E"),
    ],
    # --- GDP and prices ---
    "gdp_nominal": [
        ("famille", "CNA-2020-PIB"),
        ("PERIODICITE", "A"),
        ("SECT-INST", "S0"),
        ("OPERATION", "PIB"),
        ("PRIX_REF", "VAL"),
        ("NATURE", "VALEUR_ABSOLUE"),
        ("UNITE", "EUROS_COURANTS"),
    ],
    "cpi": [
        ("famille", "IPC-2025"),
        ("PERIODICITE", "M"),
        ("INDICATEUR", "IPC"),
        ("COICOP2018", "00"),
        ("PRIX_CONSO", "00"),
        ("NATURE", "INDICE"),
        ("MENAGES_IPC", "ENSEMBLE"),
        ("ZONE_GEO", "FE"),
        ("CORRECTION", "BRUT"),
    ],
    # --- COFOG functions: OTE (total expenditure) per FON01..FON10, S13, CNA-2014 ---
    "cofog_gf01": [("famille", "CNA-2014-DEP-APU"), ("PERIODICITE", "A"), ("SECT-INST", "S13"), ("OPERATION", "OTE"), ("FONCTION", "FON01")],
    "cofog_gf02": [("famille", "CNA-2014-DEP-APU"), ("PERIODICITE", "A"), ("SECT-INST", "S13"), ("OPERATION", "OTE"), ("FONCTION", "FON02")],
    "cofog_gf03": [("famille", "CNA-2014-DEP-APU"), ("PERIODICITE", "A"), ("SECT-INST", "S13"), ("OPERATION", "OTE"), ("FONCTION", "FON03")],
    "cofog_gf04": [("famille", "CNA-2014-DEP-APU"), ("PERIODICITE", "A"), ("SECT-INST", "S13"), ("OPERATION", "OTE"), ("FONCTION", "FON04")],
    "cofog_gf05": [("famille", "CNA-2014-DEP-APU"), ("PERIODICITE", "A"), ("SECT-INST", "S13"), ("OPERATION", "OTE"), ("FONCTION", "FON05")],
    "cofog_gf06": [("famille", "CNA-2014-DEP-APU"), ("PERIODICITE", "A"), ("SECT-INST", "S13"), ("OPERATION", "OTE"), ("FONCTION", "FON06")],
    "cofog_gf07": [("famille", "CNA-2014-DEP-APU"), ("PERIODICITE", "A"), ("SECT-INST", "S13"), ("OPERATION", "OTE"), ("FONCTION", "FON07")],
    "cofog_gf08": [("famille", "CNA-2014-DEP-APU"), ("PERIODICITE", "A"), ("SECT-INST", "S13"), ("OPERATION", "OTE"), ("FONCTION", "FON08")],
    "cofog_gf09": [("famille", "CNA-2014-DEP-APU"), ("PERIODICITE", "A"), ("SECT-INST", "S13"), ("OPERATION", "OTE"), ("FONCTION", "FON09")],
    "cofog_gf10": [("famille", "CNA-2014-DEP-APU"), ("PERIODICITE", "A"), ("SECT-INST", "S13"), ("OPERATION", "OTE"), ("FONCTION", "FON10")],
}


def download_mapping(force_refresh: bool = False) -> pd.DataFrame:
    """
    Resolve the latest mapping ZIP from INSEE's metadata page, download it,
    and extract the CSV. Cached at data/raw/insee_idbank_mapping.{zip,csv}.
    Re-downloads if cache is older than 30 days or force_refresh=True.
    """
    cache_csv = Path(RAW_DATA_DIR) / "insee_idbank_mapping.csv"
    cache_zip = Path(RAW_DATA_DIR) / "insee_idbank_mapping.zip"

    if not force_refresh and cache_csv.exists():
        age_days = (pd.Timestamp.now() - pd.Timestamp(cache_csv.stat().st_mtime, unit="s")).days
        if age_days < 30:
            log.info(f"Using cached idBank mapping ({age_days}d old)")
            return _parse_mapping_csv(cache_csv)

    log.info("Resolving latest INSEE idBank mapping ZIP...")
    headers = {**DEFAULT_HEADERS, "Referer": METADATA_URL}
    meta = requests.get(METADATA_URL, headers=headers, timeout=60)
    meta.raise_for_status()
    matches = sorted(set(ZIP_FILENAME_RE.findall(meta.text)))
    if not matches:
        raise RuntimeError(
            f"No mapping ZIP link found on {METADATA_URL}. "
            "INSEE may have restructured the page; inspect the HTML manually."
        )
    zip_path_url = "https://www.insee.fr" + matches[-1]
    log.info(f"Downloading {zip_path_url}")

    cache_zip.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(zip_path_url, headers=headers, timeout=180)
    resp.raise_for_status()
    cache_zip.write_bytes(resp.content)

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
        cache_csv.write_bytes(zf.read(csv_name))
    log.info(f"Extracted {csv_name} -> {cache_csv} ({cache_csv.stat().st_size / 1024 / 1024:.1f} MB)")

    return _parse_mapping_csv(cache_csv)


def _parse_mapping_csv(path: Path) -> pd.DataFrame:
    """Try common separators; INSEE has used both ';' and ','."""
    for sep in [";", ","]:
        try:
            df = pd.read_csv(path, sep=sep, dtype=str, low_memory=False)
            if df.shape[1] > 3:
                log.info(f"Parsed mapping with sep='{sep}': {len(df)} rows, {df.shape[1]} columns")
                log.info(f"Columns: {list(df.columns)}")
                return df
        except Exception:
            continue
    raise ValueError("Could not parse INSEE idBank mapping file — check separator and encoding")


def resolve_idbanks(df: pd.DataFrame) -> dict:
    """
    Apply SERIES_SEARCH_RULES to the new positional mapping (list_var/list_mod).
    Returns a dict of logical_name -> idBank string.
    Raises a detailed RuntimeError for any series that cannot be resolved or is ambiguous.
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    required = {"famille", "idbank", "list_mod", "list_var"}
    if not required.issubset(df.columns):
        raise ValueError(
            f"Mapping CSV missing required columns. Got: {list(df.columns)}, "
            f"expected superset of: {sorted(required)}"
        )

    df["_vars"] = df["list_var"].str.split(".")
    df["_mods"] = df["list_mod"].str.split(".")

    def row_dim(row, dim):
        try:
            return row["_mods"][row["_vars"].index(dim)]
        except (ValueError, IndexError):
            return None

    resolved = {}
    errors = []

    for name, filters in SERIES_SEARCH_RULES.items():
        mask = pd.Series(True, index=df.index)
        for dim, val in filters:
            if dim == "famille":
                mask &= df["famille"].str.strip() == val
            else:
                col = f"_dim_{dim}"
                if col not in df.columns:
                    df[col] = df.apply(lambda r, d=dim: row_dim(r, d), axis=1)
                mask &= df[col] == val

        matches = df[mask]
        if len(matches) == 0:
            errors.append(f"[{name}] No series found for filters: {filters}")
        elif len(matches) > 1:
            idbanks = matches["idbank"].head(5).tolist()
            errors.append(
                f"[{name}] Ambiguous: {len(matches)} matches for filters {filters}. "
                f"Candidate idBanks: {idbanks}. Add more filters to disambiguate."
            )
        else:
            resolved[name] = str(matches.iloc[0]["idbank"]).strip()
            log.info(f"Resolved [{name}] -> {resolved[name]}")

    if errors:
        raise RuntimeError(
            f"idBank resolution failed for {len(errors)} series:\n"
            + "\n".join(errors)
        )
    return resolved


def run_idbank_resolver(force_refresh: bool = False) -> dict:
    """
    Main entry point. Downloads mapping, resolves idBanks, writes to
    data/raw/insee_idbanks.json, and returns the resolved dict.
    """
    df = download_mapping(force_refresh=force_refresh)
    resolved = resolve_idbanks(df)

    output_path = Path(RAW_DATA_DIR) / "insee_idbanks.json"
    output_path.write_text(json.dumps(resolved, indent=2, ensure_ascii=False))
    log.info(f"Wrote {len(resolved)} resolved idBanks to {output_path}")

    return resolved


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = run_idbank_resolver(force_refresh=False)
    print(f"\nResolved {len(result)} idBanks:")
    for k, v in result.items():
        print(f"  {k}: {v}")
