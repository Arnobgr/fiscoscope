import json
from pathlib import Path

import pytest

import processors


@pytest.fixture
def insee_raw(raw_dir):
    """Write a cached INSEE BDM response: insee_raw({logical_name: {date: value}}).

    Builds on the requesting module's own `raw_dir` fixture (temp raw/output dirs).
    """
    def write(series: dict[str, dict[str, float]]) -> None:
        ids = {name: f"{i:09d}" for i, name in enumerate(series)}
        Path(processors.RAW_DATA_DIR, "insee_idbanks.json").write_text(json.dumps(ids))
        raw_dir("insee_bdm", [
            {"idbank": ids[name], "date": date, "value": value}
            for name, points in series.items() for date, value in points.items()
        ])

    return write


def months(year: int, value: float, n: int = 12) -> dict[str, float]:
    """n monthly observations of `value` for `year`, as BDM 'YYYY-MM' dates."""
    return {f"{year}-{m:02d}": value for m in range(1, n + 1)}
