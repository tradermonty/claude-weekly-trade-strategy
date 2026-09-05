"""Fail-closed tests for verify_plan checks #18 (coverage) and #19 (AND groups).

These guard the two ways a broken downstream contract used to pass review:

  #18  An earlier version only asked whether `unevaluated` was empty, so a
       plan_state reporting 12 of 21 legs evaluated with an empty list passed.
  #19  An earlier version tagged AND legs but never stored or checked a group
       verdict, so a scenario whose partner leg was dropped looked satisfiable
       by the surviving leg alone.

Both are exercised through the real verify_plan entry point.
"""
import copy
import importlib.util
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "vp", ROOT / ".claude/skills/daily-action-plan/scripts/verify_plan.py")
vp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vp)

_bspec = importlib.util.spec_from_file_location(
    "bps", ROOT / ".claude/skills/daily-action-plan/scripts/build_plan_state.py")
bps = importlib.util.module_from_spec(_bspec)
_bspec.loader.exec_module(bps)


def _plan_state():
    """A minimal post-market plan_state with one OR leg and one AND pair."""
    scen = {
        "bear": {"probability": 28, "satisfaction_rule": "any", "min_legs": 1,
                 "triggers": ["VIX 17超を終値ベースで2日連続"]},
        "tail_risk": {
            "probability": 10, "satisfaction_rule": "all", "min_legs": 0,
            "triggers": ["SPX 7,436.32 を終値で割れ かつ VIX 23超を終値ベースで2日連続"],
        },
    }
    market = {
        "vix": {"price": 14.43, "prev_close": 14.51},
        "sp500": {"price": 7711.76, "prev_close": 7730.99},
    }
    breadth = {"breadth_200ma": 63.47, "breadth_8ma": 72.17, "uptrend_ratio": 19.72}
    tds = bps._compute_trigger_distance(
        scen, market, breadth, "post-market", date(2026, 8, 31))

    and_groups = bps._collect_and_groups(tds)
    for g in and_groups:
        for d in tds:
            for e in d["trigger_distances"]:
                if e.get("and_group") == g["group"]:
                    e["and_satisfied"] = g["satisfied"]

    return {
        "meta": {"timing": "post-market", "date": "2026-08-31",
                 "market_status": "OPEN", "is_official_close": True},
        "analysis": {
            "trigger_distances": tds,
            "trigger_coverage": {
                "source_leg_total": sum(d["source_leg_count"] for d in tds),
                "evaluated_leg_total": sum(d["evaluated_leg_count"] for d in tds),
                "per_scenario": {
                    d["scenario"]: {"source": d["source_leg_count"],
                                    "evaluated": d["evaluated_leg_count"]}
                    for d in tds
                },
                "unevaluated": {},
                "manual_only": [],
                "and_groups": and_groups,
                "scenario_rules": {
                    d["scenario"]: {
                        "rule": d["satisfaction_rule"],
                        "min_legs": d["min_legs"],
                        "leg_count": len(d["trigger_distances"]),
                        "met_leg_count": d["met_leg_count"],
                        "undecided_leg_count": d["undecided_leg_count"],
                        "satisfied": d["scenario_satisfied"],
                    }
                    for d in tds
                },
            },
        },
    }


def _run(ps):
    """Return {check_number: passed} for checks 18, 19 and 20."""
    result = vp.verify(ps, {}, {})
    return {
        c["num"]: c["status"] == "PASS"
        for c in result.checks if c["num"] in (18, 19, 20)
    }


def _run21(ps):
    """Return whether check #21 (source-text audit) passed."""
    result = vp.verify(ps, {}, {})
    return {c["num"]: c["status"] == "PASS" for c in result.checks}[21]


def test_baseline_passes():
    assert _run(_plan_state()) == {18: True, 19: True, 20: True}


def test_count_mismatch_fails_even_with_empty_unevaluated_list():
    ps = _plan_state()
    ps["analysis"]["trigger_coverage"]["evaluated_leg_total"] -= 1
    assert _run(ps)[18] is False


def test_per_scenario_shortfall_is_not_masked_by_a_surplus():
    ps = _plan_state()
    per = ps["analysis"]["trigger_coverage"]["per_scenario"]
    per["bear"]["evaluated"] += 1
    per["tail_risk"]["evaluated"] -= 1
    assert _run(ps)[18] is False


def test_manual_only_declaration_is_accepted():
    """The escape hatch: an unevaluable leg passes only when declared."""
    ps = _plan_state()
    cov = ps["analysis"]["trigger_coverage"]
    leg = "銅 HG 6.1615 終値割れ"
    # Mirror what the builder does when a branch cannot claim a leg: the
    # scenario's source count includes it, the evaluated count does not.
    for blk in ps["analysis"]["trigger_distances"]:
        if blk["scenario"] == "bear":
            blk["source_leg_count"] += 1
            blk["unevaluated_legs"] = [leg]
    cov["source_leg_total"] += 1
    cov["per_scenario"]["bear"]["source"] += 1
    cov["unevaluated"] = {"bear": [leg]}

    cov["manual_only"] = []
    assert _run(ps)[18] is False, "undeclared unevaluable leg must fail"

    cov["manual_only"] = [leg]
    assert _run(ps)[18] is True, "declared leg is accepted"


def test_missing_coverage_block_fails():
    ps = _plan_state()
    ps["analysis"].pop("trigger_coverage")
    assert _run(ps)[18] is False


def test_and_group_verdict_must_match_its_legs():
    ps = _plan_state()
    for g in ps["analysis"]["trigger_coverage"]["and_groups"]:
        g["satisfied"] = True  # legs are unmet
    assert _run(ps)[19] is False


def test_and_group_with_a_dropped_partner_fails():
    ps = _plan_state()
    for blk in ps["analysis"]["trigger_distances"]:
        if blk["scenario"] == "tail_risk":
            blk["trigger_distances"] = blk["trigger_distances"][:1]
    assert _run(ps)[19] is False


def test_and_group_without_a_stored_verdict_fails():
    ps = _plan_state()
    ps["analysis"]["trigger_coverage"]["and_groups"] = []
    assert _run(ps)[19] is False


def test_partially_met_and_group_is_reported_as_not_satisfied():
    ps = _plan_state()
    groups = ps["analysis"]["trigger_coverage"]["and_groups"]
    assert groups, "fixture should contain an AND group"
    assert groups[0]["satisfied"] is False
    for blk in ps["analysis"]["trigger_distances"]:
        for e in blk["trigger_distances"]:
            if e.get("and_group"):
                assert e["and_satisfied"] is False


def test_per_scenario_block_cannot_be_deleted_to_skip_the_check():
    """Iterating the stored block meant deleting it skipped the check."""
    ps = _plan_state()
    for blk in ps["analysis"]["trigger_distances"]:
        if blk["scenario"] == "bear":
            blk["source_leg_count"] += 1  # a leg is now unaccounted for
    ps["analysis"]["trigger_coverage"].pop("per_scenario")
    assert _run(ps)[18] is False


def test_per_scenario_counts_must_match_the_legs():
    ps = _plan_state()
    ps["analysis"]["trigger_coverage"]["per_scenario"]["bear"]["evaluated"] = 99
    assert _run(ps)[18] is False


def test_and_group_satisfied_key_cannot_be_omitted():
    """Deleting the key used to pass whenever the recomputed verdict was False."""
    ps = _plan_state()
    for g in ps["analysis"]["trigger_coverage"]["and_groups"]:
        g.pop("satisfied")
    assert _run(ps)[19] is False


def test_leg_and_satisfied_value_must_match_the_group():
    """Presence was checked but not the value, so a leg could claim True."""
    ps = _plan_state()
    assert ps["analysis"]["trigger_coverage"]["and_groups"][0]["satisfied"] is False
    for blk in ps["analysis"]["trigger_distances"]:
        for e in blk["trigger_distances"]:
            if e.get("and_group"):
                e["and_satisfied"] = True
    assert _run(ps)[19] is False


def test_and_group_met_count_must_match_the_legs():
    ps = _plan_state()
    ps["analysis"]["trigger_coverage"]["and_groups"][0]["met_count"] = 2
    assert _run(ps)[19] is False


# --- #20 scenario satisfaction rules --------------------------------------

def test_scenario_rules_block_is_required():
    ps = _plan_state()
    ps["analysis"]["trigger_coverage"].pop("scenario_rules")
    assert _run(ps)[20] is False


def test_scenario_verdict_must_match_its_rule():
    ps = _plan_state()
    rules = ps["analysis"]["trigger_coverage"]["scenario_rules"]
    assert rules["tail_risk"]["satisfied"] is False
    rules["tail_risk"]["satisfied"] = True
    assert _run(ps)[20] is False


def test_an_all_rule_is_not_satisfied_by_one_leg():
    """The core defect: 5 legs with and_group None read as OR."""
    ps = _plan_state()
    rules = ps["analysis"]["trigger_coverage"]["scenario_rules"]
    rules["tail_risk"]["rule"] = "all"
    # one leg met, one not
    for blk in ps["analysis"]["trigger_distances"]:
        if blk["scenario"] == "tail_risk":
            blk["trigger_distances"][0]["condition_met"] = True
            blk["trigger_distances"][1]["condition_met"] = False
    rules["tail_risk"]["met_leg_count"] = 1
    rules["tail_risk"]["satisfied"] = True   # claiming it fired
    assert _run(ps)[20] is False


def test_scenario_rules_must_cover_every_scenario():
    ps = _plan_state()
    ps["analysis"]["trigger_coverage"]["scenario_rules"].pop("bear")
    assert _run(ps)[20] is False


def test_unknown_rule_name_fails():
    ps = _plan_state()
    ps["analysis"]["trigger_coverage"]["scenario_rules"]["bear"]["rule"] = "majority"
    assert _run(ps)[20] is False


# --- breadth-50 missing value ---------------------------------------------

def test_missing_breadth50_stays_none_and_never_becomes_zero():
    """A blank CSV cell must not read as "Breadth-50 below 50%" being met."""
    fspec = importlib.util.spec_from_file_location(
        "fb", ROOT / ".claude/skills/breadth-chart-analyst/scripts/fetch_breadth_csv.py")
    fb = importlib.util.module_from_spec(fspec)
    fspec.loader.exec_module(fb)
    bd = fb.BreadthData(date="2026-08-28", sp500_price=769.35, breadth_raw=0.71,
                        breadth_200ma=0.6347, breadth_8ma=0.7217,
                        breadth_50_raw=None, trend="1")
    ud = fb.UptrendData(date="2026-08-29", ratio=0.1972, ma_10=0.2468,
                        slope=-0.0132, trend="down")
    assert fb.analyze([bd], [ud], []).breadth_50_raw is None


def test_missing_breadth50_leaves_the_leg_unevaluated():
    scen = {"bear": {"probability": 28, "triggers": ["Breadth-50 生値 50% 割れ"]}}
    blk = bps._compute_trigger_distance(
        scen, {"vix": {"price": 14.43}},
        {"uptrend_ratio": 19.72, "cross_diff": 8.7, "breadth_50_raw": None},
        "post-market", date(2026, 8, 31))[0]
    assert blk["evaluated_leg_count"] == 0
    assert blk["unevaluated_legs"] == ["Breadth-50 生値 50% 割れ"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS: {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {fn.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


# --- #21: the source-text audit -------------------------------------------
# Checks 18-20 count legs in the parser's output. A scenario the parser could
# not read reports 0 of 0 and passes all three, which is how a whole scenario
# could disappear between the article and the plan without any gate objecting.


def test_check_21_is_missing_audit_fails_closed():
    ps = _plan_state()
    ps["analysis"]["trigger_coverage"].pop("source_audit", None)
    assert _run21(ps) is False, "an absent audit must not pass"


def test_check_21_passes_with_a_clean_audit():
    ps = _plan_state()
    ps["analysis"]["trigger_coverage"]["source_audit"] = {
        "applicable": True, "raw_scenario_count": 4,
        "raw_with_trigger_block": 4, "parsed_scenario_count": 4, "gaps": [],
    }
    assert _run21(ps) is True


def test_check_21_fails_when_a_scenario_was_dropped():
    ps = _plan_state()
    ps["analysis"]["trigger_coverage"]["source_audit"] = {
        "applicable": True, "raw_scenario_count": 4,
        "raw_with_trigger_block": 4, "parsed_scenario_count": 4,
        "gaps": [{"heading": "シナリオ 2 (Risk-On)",
                  "reason": "conditions written in the article, 0 legs parsed"}],
    }
    assert _run21(ps) is False


def test_check_21_reports_zero_of_zero_coverage_as_a_failure():
    """The exact shape of the blind spot: coverage 0/0 with a live scenario."""
    ps = _plan_state()
    cov = ps["analysis"]["trigger_coverage"]
    for d in ps["analysis"]["trigger_distances"]:
        d["trigger_distances"] = []
        d["source_leg_count"] = 0
        d["evaluated_leg_count"] = 0
        d["unevaluated_legs"] = []
        d["met_leg_count"] = 0
        d["undecided_leg_count"] = 0
        d["scenario_satisfied"] = False
    cov["source_leg_total"] = 0
    cov["evaluated_leg_total"] = 0
    cov["and_groups"] = []
    cov["per_scenario"] = {k: {"source": 0, "evaluated": 0} for k in cov["per_scenario"]}
    for r in cov["scenario_rules"].values():
        r.update({"leg_count": 0, "met_leg_count": 0,
                  "undecided_leg_count": 0, "satisfied": False})
    cov["source_audit"] = {
        "applicable": True, "raw_scenario_count": 4, "raw_with_trigger_block": 4,
        "parsed_scenario_count": 4,
        "gaps": [{"heading": "シナリオ 1 (Base)", "reason": "0 legs parsed"}],
    }
    checks = _run(ps)
    assert checks[18] is True, "coverage arithmetic is satisfied by 0 == 0"
    assert _run21(ps) is False, "the audit is what catches it"


def test_check_21_skips_a_format_it_was_not_written_for():
    ps = _plan_state()
    ps["analysis"]["trigger_coverage"]["source_audit"] = {
        "applicable": False, "reason": "no Japanese scenario headings found",
        "raw_scenario_count": 0, "parsed_scenario_count": 3, "gaps": [],
    }
    assert _run21(ps) is True
