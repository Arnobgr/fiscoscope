"""Roadmap 2.1: € per inhabitant in constant euros (INSEE population and CPI)."""

import json

import pandas as pd
import pytest

import processors
from conftest import months
from processors import cpi_annual, per_capita_block


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    """Point processors at temp raw/output dirs; return a writer for raw files."""
    monkeypatch.setattr(processors, "RAW_DATA_DIR", str(tmp_path / "raw"))
    monkeypatch.setattr(processors, "OUTPUT_DATA_DIR", str(tmp_path / "out"))
    (tmp_path / "raw").mkdir()

    def write(source: str, data) -> None:
        (tmp_path / "raw" / f"{source}_2026-01-01.json").write_text(json.dumps(data))

    return write


def frame(points: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame({"date": list(points), "value": list(points.values())})


def test_cpi_annual_averages_complete_years_only():
    cpi = frame({**months(2024, 80.0), **months(2025, 110.0, 11), "2025-12": 90.0,
                 **months(2026, 120.0, 9)})
    assert cpi_annual(cpi) == {2024: 80.0, 2025: pytest.approx(108.333, abs=1e-3)}
    with pytest.raises(ValueError, match="YYYY-MM"):
        cpi_annual(frame({"2024": 80.0}))


def test_per_capita_block_divides_by_population_and_rebases_to_latest_cpi_year(raw_dir, insee_raw):
    insee_raw({
        "population": {"2024": 50.0, "2025": 100.0},
        "cpi": {**months(2024, 80.0), **months(2025, 100.0), **months(2026, 103.0, 9)},
    })
    block = per_capita_block({"x": {2023: 1.0, 2024: 4000.0, 2025: 5000.0, 2026: 1.0}})
    assert block["base_year"] == 2025  # 2026 has only 9 months
    # 2024: 4000 / 50 × 100 / 80 = 100 € of 2025; 2023 (no population) and 2026 (no full CPI) dropped
    assert block["series"]["x"] == [{"year": 2024, "value": 100}, {"year": 2025, "value": 50}]


def test_deficit_subsector_per_capita_from_eurostat_millions(raw_dir, insee_raw):
    from processors.kpi_sustainability import compute_deficit_subsector
    from test_phase1 import jsonstat

    insee_raw({"population": {"2025": 2_000_000.0}, "cpi": months(2025, 100.0)})
    dims = {
        "freq": ["A"], "unit": ["MIO_EUR", "PC_GDP"], "sector": ["S13", "S1311", "S1313", "S1314"],
        "na_item": ["B9"], "geo": ["FR"], "time": ["2025"],
    }
    values = {}
    for sector, eur in (("S13", -10.0), ("S1311", -8.0), ("S1313", -1.0), ("S1314", -1.0)):
        values[("A", "MIO_EUR", sector, "B9", "FR", "2025")] = eur
        values[("A", "PC_GDP", sector, "B9", "FR", "2025")] = eur / 10
    raw_dir("eurostat_main", jsonstat(dims, values))

    pc = compute_deficit_subsector()["per_capita"]
    assert pc["base_year"] == 2025
    # −8 M€ / 2 M inhabitants = −4 €
    assert pc["series"]["central"] == [{"year": 2025, "value": -4}]
    assert pc["series"]["total"] == [{"year": 2025, "value": -5}]
