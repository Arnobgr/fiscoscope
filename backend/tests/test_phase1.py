"""Roadmap Phase 1: Eurostat JSON-stat decoding and the new Eurostat/OECD processors."""

import json

import pytest

import processors
from fetchers.eurostat import decode_jsonstat


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    """Point processors at temp raw/output dirs; return a writer for raw files."""
    monkeypatch.setattr(processors, "RAW_DATA_DIR", str(tmp_path / "raw"))
    monkeypatch.setattr(processors, "OUTPUT_DATA_DIR", str(tmp_path / "out"))
    (tmp_path / "raw").mkdir()

    def write(source: str, data) -> None:
        (tmp_path / "raw" / f"{source}_2026-01-01.json").write_text(json.dumps(data))

    return write


def jsonstat(dims: dict[str, list[str]], values: dict[tuple, float]) -> dict:
    """Build a JSON-stat 2.0 dataset (row-major flat index) from codes and values."""
    flat = {}
    for key, v in values.items():
        i = 0
        for (dim, codes), code in zip(dims.items(), key):
            i = i * len(codes) + codes.index(code)
        flat[str(i)] = v
    return {
        "id": list(dims),
        "size": [len(c) for c in dims.values()],
        "dimension": {
            d: {"category": {"index": {c: n for n, c in enumerate(codes)}}}
            for d, codes in dims.items()
        },
        "value": flat,
    }


def test_decode_jsonstat_row_major_and_drops_nulls():
    d = {
        "id": ["a", "b"],
        "size": [2, 3],
        "dimension": {
            "a": {"category": {"index": {"x": 0, "y": 1}}},
            "b": {"category": {"index": {"p": 0, "q": 1, "r": 2}}},
        },
        "value": {"0": 1.5, "5": 2.5, "4": None},
    }
    assert decode_jsonstat(d) == {("x", "p"): 1.5, ("y", "r"): 2.5}


def test_admin_overhead_france_peers_and_eu27(raw_dir):
    from processors.kpi_overhead import compute_admin_overhead

    dims = {
        "freq": ["A"], "unit": ["MIO_EUR"], "sector": ["S13"],
        "cofog99": ["TOTAL", "GF01"], "na_item": ["TE", "D1"],
        "geo": ["FR", "DE", "EU27_2020", "US"], "time": ["2023", "2024"],
    }
    values = {}
    for geo, d1 in (("FR", 10.0), ("DE", 6.0), ("EU27_2020", 8.0), ("US", 1.0)):
        for year in ("2023", "2024"):
            values[("A", "MIO_EUR", "S13", "GF01", "D1", geo, year)] = d1
            values[("A", "MIO_EUR", "S13", "TOTAL", "TE", geo, year)] = 200.0
    raw_dir("eurostat_exp", jsonstat(dims, values))

    out = compute_admin_overhead()
    assert out["france"] == [{"year": 2023, "value": 5.0}, {"year": 2024, "value": 5.0}]
    assert set(out["peers"]) == {"DEU", "EU27_AVG"}  # unmapped geo dropped, no OECD_AVG
    assert out["peers"]["DEU"][-1] == {"year": 2024, "value": 3.0}
    assert out["latest"] == {"year": 2024, "value": 5.0, "yoy_change": 0.0}


def test_debt_holders_other_residents_by_difference(raw_dir):
    from processors.kpi_sustainability import debt_holders

    dims = {
        "freq": ["A"], "na_item": ["GD"], "sector2": ["S1_S2", "S2", "S121"],
        "sector": ["S13"], "maturity": ["TOTAL"], "unit": ["PC_GDP"],
        "geo": ["FR"], "time": ["2025"],
    }
    vals = {"S1_S2": 115.6, "S2": 62.8, "S121": 19.1}
    raw_dir("eurostat_debt", jsonstat(dims, {
        ("A", "GD", s2, "S13", "TOTAL", "PC_GDP", "FR", "2025"): v for s2, v in vals.items()
    }))

    fr = debt_holders()["france"]
    assert fr["non_residents"] == [{"year": 2025, "value": 62.8}]
    assert fr["central_bank"] == [{"year": 2025, "value": 19.1}]
    assert fr["other_residents"] == [{"year": 2025, "value": 33.7}]


def _oecd_row(area, year, value, measure, unit):
    return {"REF_AREA": area, "TIME_PERIOD": year, "OBS_VALUE": value,
            "MEASURE": measure, "UNIT_MEASURE": unit}


def test_tax_burden_keeps_oecd_aggregate_under_its_own_key(raw_dir):
    from processors.kpi_tax_burden import compute_tax_burden

    raw_dir("oecd_tax_revenue", [
        _oecd_row("FRA", 2024, 43.5, "TAX_REV", "PT_B1GQ"),
        _oecd_row("GBR", 2024, 34.4, "TAX_REV", "PT_B1GQ"),
        _oecd_row("OECD_REP", 2024, 34.1, "TAX_REV", "PT_B1GQ"),
    ])
    out = compute_tax_burden()
    assert out["france"] == [{"year": 2024, "value": 43.5}]
    assert set(out["peers"]) == {"GBR", "OECD_REP"}


def test_public_employment_filters_measure_and_rejects_duplicates(raw_dir):
    from processors.kpi_public_employment import compute_public_employment

    rows = [
        _oecd_row("FRA", 2023, 20.7, "EMPG", "PT_EMP"),
        _oecd_row("FRA", 2023, 5.6, "EMPG", "PT_POP"),  # other unit, filtered out
        _oecd_row("OECD", 2023, 18.0, "EMPG", "PT_EMP"),
    ]
    raw_dir("oecd_public_employment", rows)
    out = compute_public_employment()
    assert out["france"] == [{"year": 2023, "value": 20.7}]
    assert set(out["peers"]) == {"OECD"}

    raw_dir("oecd_public_employment", rows + [_oecd_row("FRA", 2023, 21.0, "EMPG", "PT_EMP")])
    with pytest.raises(ValueError, match="Several observations"):
        compute_public_employment()
