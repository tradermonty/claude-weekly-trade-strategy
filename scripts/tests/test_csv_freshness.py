"""Issue #17: publication success must not stand in for a current session."""
import importlib.util
import json
import sys
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from trading.core.feed_freshness import completed_session, expected_session, feed_freshness


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fb = load("freshness_fetch", ".claude/skills/breadth-chart-analyst/scripts/fetch_breadth_csv.py")
bps = load("freshness_build", ".claude/skills/daily-action-plan/scripts/build_plan_state.py")
vp = load("freshness_verify", ".claude/skills/daily-action-plan/scripts/verify_plan.py")
FIXTURE = ROOT / "scripts/tests/fixtures/plan_state/2026-09-14-weekly-strategy.md"


@pytest.mark.parametrize("day,timing,want", [
    ("2026-11-16", "pre-market", "2026-11-13"),
    ("2026-11-16", "post-market", "2026-11-16"),
    ("2026-11-14", "post-market", "2026-11-13"),
    ("2026-11-15", "pre-market", "2026-11-13"),
    ("2026-09-07", "post-market", "2026-09-04"),  # Labor Day
    ("2026-09-08", "pre-market", "2026-09-04"),
    ("2026-04-03", "post-market", "2026-04-02"),  # Good Friday
    ("2026-11-27", "post-market", "2026-11-27"),  # early close
])
def test_expected_session(day, timing, want):
    assert expected_session(date.fromisoformat(day), timing).isoformat() == want


@pytest.mark.parametrize("instant,want", [
    ("2026-07-06T19:59:00+00:00", "2026-07-02"),  # July 3 observed holiday
    ("2026-07-06T20:00:00+00:00", "2026-07-06"),  # DST close
    ("2026-11-16T20:59:00+00:00", "2026-11-13"),
    ("2026-11-16T21:00:00+00:00", "2026-11-16"),
    ("2026-11-27T17:59:00+00:00", "2026-11-25"),
    ("2026-11-27T18:00:00+00:00", "2026-11-27"),
])
def test_fetch_clock_handles_dst_and_early_close(instant, want):
    assert completed_session(datetime.fromisoformat(instant)).isoformat() == want


def observations(up_date="2026-09-10", prior="2026-09-09"):
    b = [fb.BreadthData("2026-09-10", 7800, .48, .60, .52, .40, "down"),
         fb.BreadthData("2026-09-11", 7800, .48, .60, .52, .40, "down")]
    u = [fb.UptrendData(prior, .12, .15, -.01, "down"),
         fb.UptrendData(up_date, .12, .15, -.01, "down")]
    return b, u


def analysis(up_date="2026-09-10", prior="2026-09-09"):
    b, u = observations(up_date, prior)
    return fb.analyze(b, u, [], expected=date(2026, 9, 11))


def build(result, timing="post-market", day=date(2026, 9, 11)):
    # Keep all non-CSV warning groups false, isolating 2-of-3 CSV semantics.
    market = {"quotes": {
        "^GSPC": {"price": 8000, "previousClose": 8000},
        "^DJI": {"price": 55000, "previousClose": 55000},
        "^RUT": {"price": 3000, "previousClose": 3000},
        "^VIX": {"price": 15, "previousClose": 15},
        "CLUSD": {"price": 90, "previousClose": 90},
        "TLT": {"price": 90, "previousClose": 90},
    }, "treasury": {"year10": 4.5, "year30": 5.0,
                    "_prev": {"year10": 4.5, "year30": 5.0}}}
    return bps.build_plan_state(timing, market, asdict(result), str(FIXTURE), today=day)


def bear(plan):
    return next(d for d in plan["analysis"]["trigger_distances"] if d["scenario"] == "bear")


def csv_group(block):
    return next(g for g in block["trigger_groups"] if "CSV" in g["label"])


def check23(plan):
    return next(c for c in vp.verify(plan, {}, {}).checks if c["num"] == 23)


def test_current_breadth_stale_uptrend_is_independent_and_preserves_groups():
    result = analysis()
    assert result.freshness["breadth"]["fresh"] is True
    assert result.freshness["uptrend"]["state"] == "stale"
    human = fb.format_human(result)
    assert "観測日 2026-09-10 / 期待取引日 2026-09-11 / stale" in human
    assert "依存条件は未判定" in human
    plan = build(result)
    block = bear(plan)
    up = next(e for e in block["trigger_distances"] if e["indicator"] == "Uptrend Ratio")
    raw = next(e for e in block["trigger_distances"] if e["indicator"] == "Breadth Raw (200MA basis)")
    assert up["current"] == 12  # retained as reference, never as attainment
    assert up["condition_met"] is None and up["met_close"] is None
    assert "未判定" in up["progress"] and "2026-09-10" in up["progress"]
    assert raw["condition_met"] is True
    assert csv_group(block)["satisfied"] is None
    assert block["scenario_satisfied"] is False
    assert check23(plan)["status"] == "PASS"
    checks = {c["num"]: c for c in vp.verify(plan, {}, {}).checks}
    assert checks[17]["status"] == "PASS", checks[17]
    assert checks[19]["status"] == "PASS", checks[19]
    assert checks[20]["status"] == "PASS", checks[20]
    assert "2026-09-10" in plan["breadth"]["freshness_summary"][1]
    assert json.loads(json.dumps(plan))["breadth"]["freshness"]["uptrend"]["state"] == "stale"


def test_successful_publication_recovers_single_session_group():
    plan = build(analysis("2026-09-11", "2026-09-10"))
    assert csv_group(bear(plan))["satisfied"] is True
    assert bear(plan)["scenario_satisfied"] is True
    assert check23(plan)["status"] == "PASS"


@pytest.mark.parametrize("timing,day", [
    ("post-market", date(2026, 9, 12)),
    ("pre-market", date(2026, 9, 14)),
])
def test_weekend_carry_forward_remains_current(timing, day):
    plan = build(analysis("2026-09-11", "2026-09-10"), timing, day)
    assert plan["breadth"]["freshness"]["uptrend"]["fresh"]
    assert csv_group(bear(plan))["satisfied"] is True


def test_later_report_recomputes_producer_freshness():
    result = analysis("2026-09-11", "2026-09-10")
    assert result.freshness["uptrend"]["fresh"]
    plan = build(result, day=date(2026, 9, 14))
    assert plan["breadth"]["freshness"]["uptrend"]["state"] == "stale"
    assert csv_group(bear(plan))["satisfied"] is None


@pytest.mark.parametrize("prior,met", [
    ("2026-09-10", True), ("2026-09-09", None),
    ("2026-09-11", None), (None, None),
])
def test_consecutive_sessions_cannot_bridge_gap_or_duplicate(prior, met):
    breadth = {"uptrend_ratio": 12, "uptrend_ratio_prev": 12,
               "freshness": {"uptrend": feed_freshness("2026-09-11", prior, date(2026, 9, 11))}}
    scenarios = {"bear": {"triggers": ["Uptrend Ratio 15% 割れをCSV 2データ点連続"],
                          "satisfaction_rule": "all"}}
    block = bps._compute_trigger_distance(scenarios, {}, breadth, "post-market", date(2026, 9, 11))[0]
    leg = block["trigger_distances"][0]
    assert leg["required_days"] == 2
    assert leg["condition_met"] is met
    assert block["scenario_satisfied"] is (met is True)


@pytest.mark.parametrize("observed,state", [
    ("", "missing"), ("bad-date", "invalid_date"),
    ("2026-09-12", "invalid_session"), ("2026-09-14", "future"),
    ("2026-09-10", "stale"),
])
def test_color_cannot_fire_on_unavailable_session(observed, state):
    f = feed_freshness(observed, None, date(2026, 9, 11))
    assert f["state"] == state
    data = {"uptrend_ratio": 12, "uptrend_color": "GREEN", "freshness": {"uptrend": f}}
    scenarios = {"bull": {"triggers": ["Uptrend Ratio が GREEN へ転換"], "satisfaction_rule": "all"}}
    block = bps._compute_trigger_distance(scenarios, {}, data, "pre-market", date(2026, 9, 14))[0]
    assert block["trigger_distances"][0]["condition_met"] is None
    assert block["scenario_satisfied"] is False


def test_empty_uptrend_keeps_breadth_usable():
    b, _ = observations()
    result = fb.analyze(b, [], [], expected=date(2026, 9, 11))
    assert result.uptrend_ratio is None
    assert "missing" in fb.format_human(result)
    block = bear(build(result))
    assert csv_group(block)["met_legs"] == 1
    assert csv_group(block)["satisfied"] is None
    assert any(e["indicator"] == "Uptrend Ratio" and e["condition_met"] is None for e in block["trigger_distances"])


def test_unsorted_and_duplicate_rows_do_not_manufacture_history():
    b, u = observations("2026-09-11", "2026-09-09")
    result = fb.analyze(b[::-1], [u[1], u[0], u[1]], [], expected=date(2026, 9, 11))
    assert result.uptrend_date == "2026-09-11"
    assert result.prev_uptrend_date == "2026-09-09"
    assert result.freshness["uptrend"]["consecutive"] is False


def test_verifier_rejects_tampered_stale_attainment_and_metadata():
    plan = build(analysis())
    up = next(e for e in bear(plan)["trigger_distances"] if e["indicator"] == "Uptrend Ratio")
    up["condition_met"] = True
    assert check23(plan)["status"] == "FAIL"
    plan = build(analysis())
    plan["breadth"]["freshness"]["uptrend"]["fresh"] = True
    assert check23(plan)["status"] == "FAIL"


def test_holiday_session_pair_counts_as_consecutive():
    state = feed_freshness("2026-09-08", "2026-09-04", date(2026, 9, 8))
    assert state["fresh"] and state["consecutive"]
    # A Monday holiday report can carry Friday's completed session unchanged.
    assert feed_freshness("2026-09-04", "2026-09-03",
                          expected_session(date(2026, 9, 7), "post-market"))["fresh"]


def test_partial_csv_row_preserves_last_valid_date():
    b, u = observations()
    u.append(fb.UptrendData("2026-09-11", None, None, None, "up"))
    result = fb.analyze(b, u, [], expected=date(2026, 9, 11))
    assert result.uptrend_date == "2026-09-10"
    assert result.freshness["uptrend"]["state"] == "stale"
    assert bear(build(result))["scenario_satisfied"] is False


@pytest.mark.parametrize("previous,color,want", [
    ("2026-09-10", "GREEN", True),
    ("2026-09-10", "RED", False),
    ("2026-09-09", "GREEN", None),
    ("2026-09-10", "UNKNOWN", None),
])
def test_color_requires_matching_prior_session_and_valid_color(previous, color, want):
    data = {"uptrend_color": "GREEN", "uptrend_color_prev": color,
            "freshness": {"uptrend": feed_freshness("2026-09-11", previous, date(2026, 9, 11))}}
    scenarios = {"bull": {"triggers": ["Uptrend Ratio GREEN をCSV 2データ点連続"],
                          "satisfaction_rule": "all"}}
    leg = bps._compute_trigger_distance(scenarios, {}, data, "post-market", date(2026, 9, 11))[0]["trigger_distances"][0]
    assert leg["condition_met"] is want
    assert ("2/2日" in leg["progress"]) is (want is True)


def test_two_current_breadth_legs_can_satisfy_group_without_uptrend():
    result = analysis()
    result.breadth_50_raw = 20  # both independent breadth legs now hold
    block = bear(build(result))
    assert csv_group(block)["met_legs"] == 2
    assert csv_group(block)["undecided_legs"] == 1
    assert csv_group(block)["satisfied"] is True
    assert block["scenario_satisfied"] is True


def test_legacy_json_without_dates_cannot_satisfy_uptrend():
    result = analysis()
    result.uptrend_date = ""
    result.breadth_date = ""
    plan = build(result)
    assert plan["breadth"]["freshness"]["uptrend"]["state"] == "missing"
    assert csv_group(bear(plan))["satisfied"] is None
    assert bear(plan)["scenario_satisfied"] is False
