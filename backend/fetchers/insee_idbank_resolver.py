import json
import logging
from pathlib import Path

import pandas as pd
import requests

from config import RAW_DATA_DIR
from fetchers import DEFAULT_HEADERS

log = logging.getLogger(__name__)

MAPPING_URL = "https://www.insee.fr/fr/statistiques/fichier/2862759/correspondance_idbank_dimension.csv"

# Each entry: logical_name -> list of (column, value) filters that must ALL match.
# Column names follow the INSEE mapping file header — verified at runtime.
# Key ESA 2010 dimension codes:
#   OPERATION: D1=compensation of employees, P51=gross fixed capital formation,
#              D62=social benefits in cash, B9=net lending/borrowing, D41=interest
#   SECT_INST: S13=all APU, S1311=central govt, S1313=local govt, S1314=social security
#   FREQ: A=annual, M=monthly
SERIES_SEARCH_RULES = {
    # --- APU aggregate accounts ---
    "wage_bill_apu": [
        ("OPERATION", "D1"),
        ("SECT_INST", "S13"),
        ("FREQ", "A"),
    ],
    "wage_bill_central": [
        ("OPERATION", "D1"),
        ("SECT_INST", "S1311"),
        ("FREQ", "A"),
    ],
    "public_investment": [
        ("OPERATION", "P51"),
        ("SECT_INST", "S13"),
        ("FREQ", "A"),
    ],
    "social_benefits": [
        ("OPERATION", "D62"),
        ("SECT_INST", "S13"),
        ("FREQ", "A"),
    ],
    "fiscal_balance": [
        ("OPERATION", "B9"),
        ("SECT_INST", "S13"),
        ("FREQ", "A"),
    ],
    "debt_interest": [
        ("OPERATION", "D41"),
        ("SECT_INST", "S13"),
        ("FREQ", "A"),
    ],
    "total_apu_expenditure": [
        ("OPERATION", "TE"),
        ("SECT_INST", "S13"),
        ("FREQ", "A"),
    ],
    # --- GDP and prices ---
    "gdp_nominal": [
        ("OPERATION", "PIB"),
        ("FREQ", "A"),
    ],
    "cpi": [
        ("OPERATION", "IPC"),
        ("FREQ", "M"),
    ],
    # --- COFOG functions (APU total, annual, current prices) ---
    "cofog_gf01": [("COFOG", "GF01"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf02": [("COFOG", "GF02"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf03": [("COFOG", "GF03"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf04": [("COFOG", "GF04"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf05": [("COFOG", "GF05"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf06": [("COFOG", "GF06"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf07": [("COFOG", "GF07"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf08": [("COFOG", "GF08"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf09": [("COFOG", "GF09"), ("SECT_INST", "S13"), ("FREQ", "A")],
    "cofog_gf10": [("COFOG", "GF10"), ("SECT_INST", "S13"), ("FREQ", "A")],
}


def download_mapping(force_refresh: bool = False) -> pd.DataFrame:
    """
    Download the INSEE BDM idBank mapping file and return as a DataFrame.
    Cached locally as data/raw/insee_idbank_mapping.csv.
    Re-downloads if the file is older than 30 days or force_refresh=True.
    """
    cache_path = Path(RAW_DATA_DIR) / "insee_idbank_mapping.csv"

    if not force_refresh and cache_path.exists():
        age_days = (pd.Timestamp.now() - pd.Timestamp(cache_path.stat().st_mtime, unit="s")).days
        if age_days < 30:
            log.info(f"Using cached idBank mapping ({age_days}d old)")
            return _parse_mapping_csv(cache_path)

    log.info("Downloading INSEE idBank mapping file...")
    headers = {**DEFAULT_HEADERS, "Referer": "https://www.insee.fr/"}
    response = requests.get(MAPPING_URL, headers=headers, timeout=120)
    response.raise_for_status()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(response.content)
    log.info(f"Saved idBank mapping to {cache_path} ({len(response.content) / 1024:.0f} KB)")

    return _parse_mapping_csv(cache_path)


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
    Apply SERIES_SEARCH_RULES to the mapping DataFrame.
    Returns a dict of logical_name -> idBank string.
    Raises a detailed RuntimeError for any series that cannot be resolved or is ambiguous.
    """
    # Normalise column names to uppercase for robust matching
    df = df.copy()
    df.columns = [c.strip().upper() for c in df.columns]

    # Identify the idBank column (may be 'IDBANK' or similar)
    idbank_col = next(
        (c for c in df.columns if "IDBANK" in c.upper()),
        df.columns[0],
    )

    resolved = {}
    errors = []

    for name, filters in SERIES_SEARCH_RULES.items():
        mask = pd.Series([True] * len(df), index=df.index)
        skip = False

        for col, val in filters:
            col_upper = col.upper()
            if col_upper not in df.columns:
                errors.append(
                    f"[{name}] Column '{col}' not found in mapping. "
                    f"Available columns: {list(df.columns)}"
                )
                skip = True
                break
            mask &= df[col_upper].str.upper().str.strip() == val.upper().strip()

        if skip:
            continue

        matches = df[mask]

        if len(matches) == 0:
            errors.append(
                f"[{name}] No series found for filters: {filters}. "
                f"Check dimension codes against mapping file columns."
            )
        elif len(matches) > 1:
            # Narrow by preferring rows where UNITE contains "milliard" (billions EUR)
            unite_col = next((c for c in df.columns if "UNITE" in c), None)
            if unite_col:
                narrow = matches[
                    matches[unite_col].str.lower().str.contains("milliard", na=False)
                ]
                if len(narrow) == 1:
                    matches = narrow
                else:
                    idbanks = matches[idbank_col].tolist()
                    errors.append(
                        f"[{name}] Ambiguous: {len(matches)} series match filters {filters}. "
                        f"Candidate idBanks: {idbanks[:5]}. Refine filters in SERIES_SEARCH_RULES."
                    )
                    continue
            else:
                idbanks = matches[idbank_col].tolist()
                errors.append(
                    f"[{name}] Ambiguous: {len(matches)} series match filters {filters}. "
                    f"Candidate idBanks: {idbanks[:5]}. Refine filters in SERIES_SEARCH_RULES."
                )
                continue

        resolved[name] = str(matches.iloc[0][idbank_col]).strip()
        log.info(f"Resolved [{name}] -> {resolved[name]}")

    if errors:
        error_msg = "\n".join(errors)
        raise RuntimeError(
            f"idBank resolution failed for {len(errors)} series:\n{error_msg}\n\n"
            f"ACTION REQUIRED: Inspect data/raw/insee_idbank_mapping.csv, "
            f"find the correct column names and dimension codes, "
            f"and update SERIES_SEARCH_RULES in this file."
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
    result = run_idbank_resolver(force_refresh=True)
    print(f"\nResolved {len(result)} idBanks:")
    for k, v in result.items():
        print(f"  {k}: {v}")
