"""Roadmap 3.1: State performance indicators — per-vintage normalisation, counting rule, drift guard."""

import json

import pytest

import processors
from processors.kpi_performance import (
    check_against_published,
    compute_performance,
    normalise_detail,
    normalise_rap,
    shares,
    tally,
)


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    """Point processors at temp raw/output dirs; return a writer for raw files."""
    monkeypatch.setattr(processors, "RAW_DATA_DIR", str(tmp_path / "raw"))
    monkeypatch.setattr(processors, "OUTPUT_DATA_DIR", str(tmp_path / "out"))
    (tmp_path / "raw").mkdir()

    def write(source: str, data, day: str = "2026-01-01") -> None:
        (tmp_path / "raw" / f"{source}_{day}.json").write_text(json.dumps(data))

    return write


def detail_row(year, status, mission="Justice", sector="Programme", programme=166, **kw):
    """A row shaped like the 2022–2024 detail dataset (floats, `annee`, `commentaire`)."""
    return {
        "annee": float(year), "type_de_secteur": sector, "mission": mission,
        "code_programme": float(programme) if sector == "Programme" else None,
        "programme": "Justice judiciaire" if sector == "Programme" else None,
        "code_externe_objectif": "P166-1", "libelle_objectif": "Rendre une justice de qualité",
        "ordre_ind": 10.0, "code_externe_indicateur": "P166-1-1",
        "libelle_indicateur": "Délai moyen de traitement", "code_interne_sous_indicateur": 1.0,
        "libelle_sous_indicateur": "Cours d'appel", "unite": "mois",
        "cible": 12.0, "execution": 13.5, "atteinte_de_la_cible": status, "commentaire": None,
        **kw,
    }


def rap_2025_row(status, **kw):
    """A row shaped like `performance-de-la-depense-rap-2025` (year-stamped string columns)."""
    return {
        "type_de_secteur": "Programme", "mission": "Écologie, développement et mobilité durables",
        "code_programme": 113, "programme": "Paysages, eau et biodiversité",
        "code_externe_objectif": "P113-1", "libelle_objectif": "Préserver la biodiversité",
        "ordre_ind": 100, "code_externe_indicateur": "P113-1-1", "libelle_indicateur": "Surface protégée",
        "ordre_ssi": 160, "libelle_sous_indicateur": "Aires marines", "unite": "%",
        "exec_2024": "30", "absexec_2024": None, "2025_cible": "32", "abs_2025_cible": None,
        "exec_2025": None, "abs_exec_2025": "Non déterminé", "atteinte_de_la_cible_2025": status,
        "2026_cible": "33",
        **kw,
    }


def test_normalise_detail_maps_columns_and_whole_floats():
    [r] = normalise_detail([detail_row(2024, "Cible atteinte", commentaire="Provisoire")])
    assert r["year"] == 2024 and r["programme_code"] == 166
    assert (r["target"], r["result"], r["status"], r["comment"]) == (12, 13.5, "met", "Provisoire")
    assert r["indicator_code"] == "P166-1-1"


def test_normalise_rap_reads_year_from_field_names():
    [r] = normalise_rap([rap_2025_row("donnée non renseignée")])
    assert r["year"] == 2025
    assert (r["target"], r["result"], r["status"]) == ("32", None, "not_reported")
    assert r["comment"] == "Non déterminé"  # abs_exec_2025 = why the result is missing


def test_normalise_rap_accepts_the_rap_2024_column_names():
    # `performance-de-la-depense` (RAP 2024) uses code_indicateur / code_sous_indicateur
    # and has no abs* columns.
    row = {
        "type_de_secteur": "Mission", "mission": "Justice", "code_programme": None, "programme": None,
        "code_objectif": "MJ-1", "libelle_objectif": "O", "code_indicateur": "MJ-1-1",
        "libelle_indicateur": "I", "code_sous_indicateur": 3, "libelle_sous_indicateur": "S",
        "unite": "%", "2024_cible": "50", "exec_2024": "48", "atteinte_de_la_cible_2024": "amélioration",
        "2025_cible": "52",
    }
    [r] = normalise_rap([row])
    assert (r["year"], r["indicator_code"], r["status"], r["comment"]) == (2024, "MJ-1-1", "improved", None)


def test_normalise_rap_rejects_ambiguous_vintage():
    with pytest.raises(ValueError, match="one atteinte_de_la_cible_YYYY"):
        normalise_rap([rap_2025_row("cible atteinte", atteinte_de_la_cible_2024="cible atteinte")])


def test_unknown_category_fails_loudly():
    with pytest.raises(ValueError, match="Unknown attainment category"):
        normalise_detail([detail_row(2024, "cible presque atteinte")])


def test_counting_rule_excludes_not_retained_and_blank():
    rows = normalise_detail([
        detail_row(2024, s) for s in
        ["cible atteinte", "cible atteinte", "amélioration", "absence amélioration",
         "donnée non renseignée", "donnée non retenue", None, ""]
    ])
    counts = tally(rows)
    assert counts == {"met": 2, "improved": 1, "not_improved": 1, "not_reported": 1,
                      "not_retained": 1, "unassessed": 2}
    assert shares(counts) == {"met": 40.0, "improved": 20.0, "not_improved": 20.0, "not_reported": 20.0}


def test_drift_guard_tolerates_1_5_pt_and_raises_beyond():
    rows = normalise_detail([detail_row(2024, "cible atteinte")] * 2 + [detail_row(2024, "amélioration")] * 2)
    near = {"cible_atteinte": 0.51, "amelioration": 0.49, "absence_amelioration": 0.0, "donnees_non_renseignees": 0.0}
    check_against_published({2024: rows}, {2024: near})  # 1 pt off: fine
    far = near | {"cible_atteinte": 0.52, "amelioration": 0.48}
    with pytest.raises(ValueError, match="drift"):
        check_against_published({2024: rows}, {2024: far})


def test_compute_performance_end_to_end(raw_dir):
    raw_dir("performance_summary", [
        {"rap": 2023.0, "cible_atteinte": 0.5, "amelioration": 0.25, "absence_amelioration": 0.25, "donnees_non_renseignees": 0.0},
        {"rap": 2024.0, "cible_atteinte": 0.5, "amelioration": 0.0, "absence_amelioration": 0.5, "donnees_non_renseignees": 0.0},
    ])
    raw_dir("performance_detail", [
        detail_row(2024, "cible atteinte"),
        detail_row(2024, "absence amélioration", ordre_ind=5.0, libelle_indicateur="Taux de cassation"),
        detail_row(2024, "donnée non retenue"),
        detail_row(2024, "cible atteinte", sector="Mission"),
        detail_row(2024, "absence amélioration", mission="Écologie, développement et mobilité durables", programme=113),
    ])
    raw_dir("performance_rap_2025", {"dataset_id": "performance-de-la-depense-rap-2025",
                                     "records": [rap_2025_row("cible atteinte"), rap_2025_row(None)]})
    # A RAP 2024 raw must be ignored: the detail dataset already covers 2024.
    stale = rap_2025_row(None)
    stale["atteinte_de_la_cible_2024"] = stale.pop("atteinte_de_la_cible_2025")
    raw_dir("performance_rap_2024", {"dataset_id": "x", "records": [stale]})

    out = compute_performance()
    assert out["france"] == [{"year": 2023, "value": 50.0}, {"year": 2024, "value": 50.0}]
    assert out["categories"]["not_improved"][-1] == {"year": 2024, "value": 50.0}
    assert out["detail_years"] == [2024, 2025]
    assert out["latest"] == {"year": 2024, "value": 50.0, "yoy_change": 0.0}
    assert "peers" not in out

    out_dir = processors.Path(processors.OUTPUT_DATA_DIR)
    d24 = json.loads((out_dir / "performance_detail_2024.json").read_text())
    assert d24["counts"]["met"] == 2 and d24["counts"]["not_retained"] == 1
    # Missions sorted accent-insensitively: "Écologie" before "Justice".
    assert [m["mission"] for m in d24["missions"]] == ["Écologie, développement et mobilité durables", "Justice"]
    justice = d24["missions"][1]
    assert justice["counts"] == {"met": 2, "improved": 0, "not_improved": 1, "not_reported": 0,
                                 "not_retained": 1, "unassessed": 0}
    # Mission-level indicators first, then the programme; indicators in document order.
    assert [g["programme_code"] for g in justice["groups"]] == [None, 166]
    prog = justice["groups"][1]["objectives"][0]["indicators"]
    assert [i["indicator"] for i in prog] == ["Taux de cassation", "Délai moyen de traitement"]
    assert prog[1]["rows"][0] == {"sub_indicator": "Cours d'appel", "unit": "mois", "target": 12,
                                  "result": 13.5, "status": "met", "comment": None}

    d25 = json.loads((out_dir / "performance_detail_2025.json").read_text())
    assert d25["counts"]["met"] == 1 and d25["counts"]["unassessed"] == 1
    assert "performance-de-la-depense-rap-2025" in d25["source"]
