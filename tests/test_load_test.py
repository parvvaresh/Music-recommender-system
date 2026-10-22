import math

import pytest

from perf.load_test import Scenario, check_thresholds, percentile, summarize, to_markdown


def test_percentile_interpolates():
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(values, 0) == 10.0
    assert percentile(values, 50) == 30.0
    assert percentile(values, 100) == 50.0
    assert percentile(values, 95) == pytest.approx(48.0)


def test_percentile_edge_cases():
    assert math.isnan(percentile([], 50))
    assert percentile([7.0], 95) == 7.0


def test_summarize():
    s = summarize([30.0, 10.0, 20.0, 40.0], errors=1, duration_s=2.0)
    assert s["requests"] == 4
    assert s["rps"] == 2.0
    assert s["p50_ms"] == 25.0
    assert s["error_rate"] == 0.25
    assert s["max_ms"] == 40.0


def test_check_thresholds():
    ok = summarize([10.0] * 100, errors=0, duration_s=1.0)
    assert check_thresholds(ok, max_p95_ms=50, max_error_rate=0.01, min_rps=50) == []

    bad = summarize([10.0] * 90 + [500.0] * 10, errors=5, duration_s=10.0)
    failures = check_thresholds(bad, max_p95_ms=50, max_error_rate=0.01, min_rps=50)
    assert len(failures) == 3

    empty = summarize([], errors=0, duration_s=1.0)
    assert check_thresholds(empty, None, 0.01, None) == ["no requests completed"]


def test_scenario_mix_is_deterministic_and_covers_all_endpoints():
    a = Scenario(100, ["Gentleman", "Darya"], seed=1)
    b = Scenario(100, ["Gentleman", "Darya"], seed=1)
    reqs = [a.next_request() for _ in range(200)]
    assert reqs == [b.next_request() for _ in range(200)]
    assert {name for name, _, _ in reqs} == {"search", "recommend_by_id", "recommend_by_title"}


def test_markdown_contains_overall_row():
    s = summarize([10.0, 20.0], errors=0, duration_s=1.0)
    report = {
        "config": {"url": "http://x", "duration_s": 1, "concurrency": 2, "warmup_s": 0},
        "overall": s,
        "endpoints": {"search": s},
    }
    md = to_markdown(report)
    assert "| **overall** | 2 | 2.0 | 15.0 |" in md
    assert "p95 (ms)" in md
