"""Roadmap 2.4: context facts behind each KPI card's sentence."""

from processors import build_context


def series(values: dict[int, float]) -> list[dict]:
    return [{"year": y, "value": v} for y, v in values.items()]


def test_history_reported_only_when_it_reaches_back_five_years():
    # 2024 is the highest since 2019 (2020–2023 lower): 5 years back → kept
    assert build_context(series({2019: 5.0, 2020: 3.0, 2021: 3.0, 2022: 3.0, 2023: 3.0, 2024: 4.0}))["history"] == {
        "direction": "high", "since": 2019, "record": False,
    }
    # highest since 2020: only 4 years back → dropped
    assert "history" not in build_context(series({2020: 5.0, 2021: 3.0, 2022: 3.0, 2023: 3.0, 2024: 4.0}))


def test_history_tie_counts_as_reached():
    # 2024 equals 2023 after rounding: "lowest since 2023", not a record
    ctx = build_context(series({**{y: 9.0 for y in range(2010, 2023)}, 2023: 1.0, 2024: 1.0}))
    assert "history" not in ctx


def test_record_needs_ten_years_and_reports_first_year():
    ten = {y: float(y - 2000) for y in range(2001, 2011)}  # rising, 10 points
    assert build_context(series(ten))["history"] == {"direction": "high", "since": 2001, "record": True}
    nine = {y: float(y - 2000) for y in range(2002, 2011)}
    assert "history" not in build_context(series(nine))


def test_negative_series_lowest_means_largest_deficit():
    ctx = build_context(series({**{y: -3.0 for y in range(2000, 2024)}, 2024: -6.0}))
    assert ctx["history"] == {"direction": "low", "since": 2000, "record": True}


def test_peers_extreme_in_latest_common_year_averages_ignored():
    france = series({2023: 3.0, 2024: 5.0, 2025: 6.0})
    peers = {
        "DEU": series({2023: 1.0, 2024: 2.0}),
        "ITA": series({2023: 4.0, 2024: 3.0}),
        "EU27_AVG": series({2024: 99.0}),  # aggregate: higher, but never counted
    }
    assert build_context(france, peers)["peers"] == {"year": 2024, "position": "highest", "of": 3}


def test_peers_only_strict_extremes():
    france = series({2024: 3.0})
    assert "peers" not in build_context(france, {"DEU": series({2024: 3.0}), "ITA": series({2024: 1.0})})
    assert "peers" not in build_context(france, {"DEU": series({2024: 4.0}), "ITA": series({2024: 1.0})})
    assert build_context(france, {"DEU": series({2024: 4.0}), "ITA": series({2024: 5.0})})["peers"]["position"] == "lowest"


def test_change_10y():
    ctx = build_context(series({2014: 45.41, 2020: 1.0, 2024: 43.46}))
    assert ctx["change_10y"] == {"from_year": 2014, "change": -1.95}
    assert "change_10y" not in build_context(series({2015: 1.0, 2024: 2.0}))


def test_empty_series():
    assert build_context([]) == {}
