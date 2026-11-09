"""
KPI: State performance targets met (roadmap 3.1). Every programme of the State
budget publishes indicators with a target (PAP) and a result (RAP).

Outputs:
- kpi_performance.json — headline = official share of targets met per RAP year
  since 2007 (performance_summary, published by the ministry, never
  recomputed here), plus the four published categories and the list of years
  available in detail.
- performance_detail_YYYY.json — one per detail year: every sub-indicator,
  nested mission → programme (mission-level indicators first) → objective →
  indicator, with target, result and attainment, and counts per mission.

Counting rule (roadmap Part 5.3): rows at sub-indicator level, Mission and
Programme rows together, excluding "donnée non retenue" and blank. It
reproduces the published shares within ~1 pt; a drift beyond MAX_GAP_PT on a
year present in both raises, so a schema change can't silently skew the
drill-down counts.
"""

import json
import logging
import re
import unicodedata
from collections import Counter
from pathlib import Path

import processors
from fetchers.performance import STATUS_FIELD
from processors import build_latest, latest_raw, now_iso, write_output

log = logging.getLogger(__name__)

STATUSES = {
    "cible atteinte": "met",
    "amélioration": "improved",
    "absence amélioration": "not_improved",
    "donnée non renseignée": "not_reported",
    "donnée non retenue": "not_retained",
}
COUNTED = ["met", "improved", "not_improved", "not_reported"]
SUMMARY_FIELDS = {
    "met": "cible_atteinte",
    "improved": "amelioration",
    "not_improved": "absence_amelioration",
    "not_reported": "donnees_non_renseignees",
}
MAX_GAP_PT = 1.5
SOURCE_PREFIX = "Ministère de l'Économie et des Finances (data.economie.gouv.fr)"


# --- Normalisation (one schema for every vintage) ----------------------------

def _status(value) -> str | None:
    if value is None or not str(value).strip():
        return None
    key = str(value).strip().lower()
    if key not in STATUSES:
        raise ValueError(f"Unknown attainment category {value!r}: update STATUSES.")
    return STATUSES[key]


def _value(value):
    """Floats of whole numbers become ints; strings are kept as published (e.g. '26 500 000')."""
    if value is None:
        return None
    if isinstance(value, float):
        return int(value) if value.is_integer() else round(value, 4)
    if isinstance(value, int):
        return value
    return str(value).strip() or None


def _first(row: dict, *names):
    """First of several alias column names present in the row (names drift per vintage)."""
    return next((row[n] for n in names if n in row), None)


def _row(r: dict, year: int, target, result, status, comment) -> dict:
    return {
        "year": year,
        "sector": r.get("type_de_secteur"),
        "mission": r.get("mission"),
        "programme_code": _value(r.get("code_programme")),
        "programme": r.get("programme"),
        "objective": r.get("libelle_objectif"),
        "indicator_code": _first(r, "code_externe_indicateur", "code_indicateur"),
        "indicator": r.get("libelle_indicateur"),
        "sub_indicator": r.get("libelle_sous_indicateur"),
        "unit": r.get("unite"),
        "target": _value(target),
        "result": _value(result),
        "status": _status(status),
        "comment": _value(comment),
        # Sort key only (document order), not written out.
        "order": (
            float(r.get("ordre_ind") or 0),
            float(_first(r, "ordre_ssi", "code_interne_sous_indicateur", "code_sous_indicateur") or 0),
        ),
    }


def normalise_detail(rows: list[dict]) -> list[dict]:
    """The 2022–2024 detail dataset: one schema, year in `annee`."""
    return [
        _row(r, int(r["annee"]), r.get("cible"), r.get("execution"),
             r.get("atteinte_de_la_cible"), r.get("commentaire"))
        for r in rows
    ]


def normalise_rap(rows: list[dict]) -> list[dict]:
    """A RAP vintage: year read from the atteinte_de_la_cible_YYYY field name."""
    fields = set().union(*(r.keys() for r in rows))
    years = sorted({int(m.group(1)) for f in fields if (m := STATUS_FIELD.match(f))})
    if len(years) != 1:
        raise ValueError(f"Expected one atteinte_de_la_cible_YYYY field, found years {years}")
    y = years[0]
    comment = next((f for f in fields if re.fullmatch(rf"abs_?exec_{y}", f)), None)
    return [
        _row(r, y, r.get(f"{y}_cible"), r.get(f"exec_{y}"),
             r.get(f"atteinte_de_la_cible_{y}"), r.get(comment) if comment else None)
        for r in rows
    ]


# --- Counting ------------------------------------------------------------------

def tally(rows: list[dict]) -> dict:
    """Rows per category, plus not_retained and unassessed (blank)."""
    c = Counter(r["status"] for r in rows)
    return {k: c.get(k, 0) for k in [*COUNTED, "not_retained"]} | {"unassessed": c.get(None, 0)}


def shares(counts: dict) -> dict:
    """% of each counted category over the denominator (not_retained and blank excluded)."""
    n = sum(counts[k] for k in COUNTED)
    return {k: round(100 * counts[k] / n, 1) for k in COUNTED} if n else {}


def check_against_published(by_year: dict[int, list], published: dict[int, dict]) -> None:
    """Raise if a recount differs from the published share by more than MAX_GAP_PT."""
    gaps = []
    for year in sorted(by_year.keys() & published.keys()):
        computed = shares(tally(by_year[year]))
        for key, field in SUMMARY_FIELDS.items():
            official = published[year][field] * 100
            if abs(computed[key] - official) > MAX_GAP_PT:
                gaps.append(f"{year} {key}: computed {computed[key]} vs published {official:.1f}")
    if gaps:
        raise ValueError(
            f"Recounted shares drift more than {MAX_GAP_PT} pt from the published "
            "series — the detail schema or the counting rule has changed: " + "; ".join(gaps)
        )


# --- Drill-down nesting -----------------------------------------------------------

def _sort_key(text: str) -> str:
    """Accent-insensitive alphabetical key ("Écologie" sorts with the E's)."""
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode().casefold()


def _group(rows: list[dict], key) -> dict:
    """Group rows by key, keeping first-appearance order."""
    out: dict = {}
    for r in rows:
        out.setdefault(key(r), []).append(r)
    return out


def build_detail(year: int, rows: list[dict], source: str) -> dict:
    missions = []
    for mission, mrows in sorted(_group(rows, lambda r: r["mission"]).items(), key=lambda kv: _sort_key(kv[0])):
        # Mission-level indicators (no programme) first, then programmes by number.
        mrows = sorted(mrows, key=lambda r: (
            r["sector"] == "Programme", r["programme_code"] if r["sector"] == "Programme" else 0, r["order"],
        ))
        groups = []
        by_prog = _group(mrows, lambda r: (r["programme_code"], r["programme"]) if r["sector"] == "Programme" else (None, None))
        for (code, programme), prows in by_prog.items():
            objectives = []
            for objective, orows in _group(prows, lambda r: r["objective"]).items():
                indicators = [
                    {
                        "code": code_ind,
                        "indicator": label,
                        "rows": [
                            {k: r[k] for k in ("sub_indicator", "unit", "target", "result", "status", "comment")}
                            for r in irows
                        ],
                    }
                    for (code_ind, label), irows in _group(orows, lambda r: (r["indicator_code"], r["indicator"])).items()
                ]
                objectives.append({"objective": objective, "indicators": indicators})
            groups.append({"programme_code": code, "programme": programme, "objectives": objectives})
        missions.append({"mission": mission, "counts": tally(mrows), "groups": groups})
    return {
        "year": year,
        "source": source,
        "last_updated": now_iso(),
        "counts": tally(rows),
        "missions": missions,
    }


# --- Entry point ---------------------------------------------------------------------

def _load(source: str):
    path = latest_raw(source)
    if path is None:
        raise FileNotFoundError(f"No data/raw/{source}_*.json found — run fetch_performance first.")
    return json.loads(path.read_text())


def _rap_years() -> list[int]:
    names = (p.name for p in Path(processors.RAW_DATA_DIR).glob("performance_rap_*.json"))
    return sorted({int(m.group(1)) for n in names if (m := re.match(r"performance_rap_(\d{4})_", n))})


def compute_performance() -> dict:
    """Compute kpi_performance.json and one performance_detail_YYYY.json per detail year."""
    published = {int(r["rap"]): r for r in _load("performance_summary")}

    by_year: dict[int, list] = {}
    sources: dict[int, str] = {}
    for r in normalise_detail(_load("performance_detail")):
        by_year.setdefault(r["year"], []).append(r)
    for year in by_year:
        sources[year] = (
            f"{SOURCE_PREFIX} — « Performance : exécution et atteinte de la cible du "
            "budget de l'État jusqu'au niveau sous-indicateur »"
        )
    for year in _rap_years():
        if year in by_year:  # the 2022–2024 detail dataset wins for its own years
            continue
        raw = _load(f"performance_rap_{year}")
        by_year[year] = normalise_rap(raw["records"])
        sources[year] = f"{SOURCE_PREFIX} — rapport annuel de performance {year} (« {raw['dataset_id']} »)"

    check_against_published(by_year, published)

    years = sorted(published)
    france = [{"year": y, "value": round(published[y]["cible_atteinte"] * 100, 2)} for y in years]
    categories = {
        key: [{"year": y, "value": round(published[y][field] * 100, 2)} for y in years]
        for key, field in SUMMARY_FIELDS.items()
    }
    detail_years = sorted(by_year)

    payload = {
        "kpi_id": "performance",
        "kpi_name": "State performance targets met",
        "description": (
            "Share of the State budget's performance sub-indicators whose target "
            "was met, per annual performance report (RAP), as published by the "
            "Ministry of Finance."
        ),
        "unit": "percent",
        "source": (
            f"{SOURCE_PREFIX} — « Performance : atteinte de la cible générale du "
            "budget de l'État depuis 2007 » ; détail par indicateur : rapports "
            "annuels de performance (RAP)"
        ),
        "methodology": (
            "Chaque programme du budget de l'État est assorti d'objectifs et "
            "d'indicateurs de performance : une cible est fixée dans le projet "
            "annuel de performance (PAP) et le résultat est publié dans le rapport "
            "annuel de performance (RAP) annexé à la loi relative aux résultats de "
            "la gestion. La série est celle publiée par le ministère : part des "
            "indicateurs, comptés au niveau des sous-indicateurs, mission et "
            "programme confondus, dont la cible est atteinte. Les trois autres "
            "catégories sont : cible non atteinte mais résultat en amélioration, "
            "cible non atteinte sans amélioration, et résultat non renseigné ; les "
            "indicateurs « non retenus » sont exclus du total. Une série s'arrête à "
            "la dernière année publiée par le ministère : Fiscoscope ne la complète "
            "pas. Limites : les cibles sont fixées, et parfois révisées, par "
            "l'administration elle-même ; la liste des indicateurs change chaque "
            "année (environ 2 000 sous-indicateurs), la série n'est donc pas à "
            "périmètre constant, et une hausse ne signifie pas à elle seule une "
            "meilleure performance. Le détail par indicateur "
            f"({detail_years[0]}–{detail_years[-1]}) provient des données "
            "publiées par sous-indicateur ; recomptées selon la même règle, les "
            "parts qu'il donne s'écartent de moins de 1,5 point de la série "
            "publiée. Une partie des indicateurs de mission reprend un indicateur "
            "de programme : ils sont comptés deux fois, comme dans la série "
            "officielle."
        ),
        "last_updated": now_iso(),
        "france": france,
        "categories": categories,
        "detail_years": detail_years,
        "latest": build_latest(france),
    }
    write_output("kpi_performance.json", payload)
    for year in detail_years:
        # Compact: ~560 KB instead of ~1.1 MB indented, and the API does not gzip.
        write_output(f"performance_detail_{year}.json", build_detail(year, by_year[year], sources[year]), compact=True)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = compute_performance()
    print(f"Performance: {len(r['france'])} years; latest {r['latest']}; detail {r['detail_years']}")
