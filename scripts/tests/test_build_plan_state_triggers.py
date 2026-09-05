"""Regression tests for build_plan_state trigger evaluation.

Every High-severity defect found in the 2026-08-31 review was the same shape:
the blog changed a trigger's wording, no branch in `_compute_trigger_distance`
claimed the leg (or the wrong branch did), and every existing gate still passed
— postflight, publish_blog_diff and verify_plan all inspect only the rows that
were emitted, never the legs that went missing.

These tests use the two real blogs as fixtures so a wording change that breaks
the downstream contract fails here instead of reaching Layer 1/2.
"""
import dataclasses
import importlib.util
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "bps", ROOT / ".claude/skills/daily-action-plan/scripts/build_plan_state.py")
bps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bps)

from trading.layer2.tools.strategy_parser import parse_blog  # noqa: E402

# 2026-08-28 close. Values are fixed so the tests do not depend on the network.
MARKET = {
    "vix": {"price": 14.43, "prev_close": 14.51},
    "sp500": {"price": 7711.76, "prev_close": 7730.99},
    "nasdaq": {"price": 29433.43, "prev_close": 29641.56},
    "dow": {"price": 53559.99, "prev_close": 53569.44},
    "russell": {"price": 2972.37, "prev_close": 3014.34},
    "oil": {"price": 83.40, "prev_close": 83.53},
    "copper": {"price": 6.659, "prev_close": 6.69},
    "us10y": {"value": 4.73, "prev_close": 4.67},
    "us30y": {"value": 5.22, "prev_close": 5.19},
    "us2y": {"value": 4.34, "prev_close": 4.20},
    "curve_2s10s": {"value": 39.0, "prev_close": 47.0},
    # 2026-09-07 put the policy-path trigger on the belly of the curve.
    "us5y": {"value": 4.54, "prev_close": 4.52},
}
BREADTH = {
    "breadth_200ma": 63.47, "breadth_8ma": 72.17,
    "uptrend_ratio": 19.72, "cross_diff": 8.70, "breadth_50_raw": 53.69,
    # 2026-09-07 moved the Stress condition onto the raw 200-series reading,
    # because both published averages are EMAs of it.
    "breadth_raw": 68.66,
}
TODAY = date(2026, 8, 31)

# blogs/** is gitignored, so the live articles do not exist on a clean
# checkout. These tracked fixtures carry the scenario/trigger section verbatim.
FIXTURES = ROOT / "scripts/tests/fixtures/plan_state"
BLOGS = [
    FIXTURES / "2026-08-24-weekly-strategy.md",
    FIXTURES / "2026-08-31-weekly-strategy.md",
    FIXTURES / "2026-09-07-weekly-strategy.md",
]


def _scenarios(blog_path):
    spec = parse_blog(blog_path)
    return {
        name: (dataclasses.asdict(sc) if dataclasses.is_dataclass(sc) else dict(vars(sc)))
        for name, sc in spec.scenarios.items()
    }


def _distances(blog_path):
    return bps._compute_trigger_distance(
        _scenarios(blog_path), MARKET, BREADTH, "post-market", TODAY)


def _source_legs(scenario):
    """Re-derive the input legs the way _compute_trigger_distance splits them."""
    legs = []
    for trigger in scenario.get("triggers", []):
        for line in bps._split_trigger_lines(trigger):
            for or_leg in re.split(r"\s+/\s+", line):
                or_leg = or_leg.strip()
                if not or_leg:
                    continue
                legs.extend(
                    s.strip() for s in bps._AND_SEPARATOR.split(or_leg) if s.strip())
    return legs


def _all_entries(blog_path):
    return [e for blk in _distances(blog_path) for e in blk["trigger_distances"]]


# --- coverage -------------------------------------------------------------

def test_every_leg_of_every_real_blog_is_evaluated():
    """No leg may be silently dropped. This is the gate the review lacked."""
    for blog in BLOGS:
        scen = _scenarios(blog)
        for blk in _distances(blog):
            expected = len(_source_legs(scen[blk["scenario"]]))
            assert blk["source_leg_count"] == expected, (
                f"{blog.name}/{blk['scenario']}: source_leg_count "
                f"{blk['source_leg_count']} != {expected}")
            assert not blk["unevaluated_legs"], (
                f"{blog.name}/{blk['scenario']}: unevaluated "
                f"{blk['unevaluated_legs']}")


EXPECTED_LEGS = {
    "2026-08-24-weekly-strategy.md": 21,
    "2026-08-31-weekly-strategy.md": 21,
    "2026-09-07-weekly-strategy.md": 21,
}


def test_fixture_leg_counts_are_pinned():
    """A fixture that quietly loses legs would make the coverage test vacuous."""
    for blog in BLOGS:
        total = sum(len(_source_legs(sc)) for sc in _scenarios(blog).values())
        assert total == EXPECTED_LEGS[blog.name], (
            f"{blog.name}: {total} legs, expected {EXPECTED_LEGS[blog.name]}")


def test_fixture_matches_the_live_blog_when_present():
    """Guards fixture drift. Skipped on a clean checkout where blogs/ is absent.

    Compares the leg TEXT, scenario set and satisfaction rules, not just counts:
    a threshold or wording change keeps the count at 21 while silently making
    the fixture describe a different strategy than the one being published.
    """
    for blog in BLOGS:
        live = ROOT / "blogs" / blog.name
        if not live.exists():
            continue
        live_sc, fix_sc = _scenarios(live), _scenarios(blog)
        assert set(live_sc) == set(fix_sc), (
            f"{blog.name}: scenarios differ - live {sorted(live_sc)} vs "
            f"fixture {sorted(fix_sc)}")
        for name in live_sc:
            assert _source_legs(live_sc[name]) == _source_legs(fix_sc[name]), (
                f"{blog.name}/{name}: trigger text differs - regenerate the "
                f"fixture\n  live   : {_source_legs(live_sc[name])}\n"
                f"  fixture: {_source_legs(fix_sc[name])}")
            for field in ("satisfaction_rule", "min_legs", "probability"):
                assert live_sc[name].get(field) == fix_sc[name].get(field), (
                    f"{blog.name}/{name}: {field} differs - live "
                    f"{live_sc[name].get(field)} vs fixture {fix_sc[name].get(field)}")


def test_scenario_satisfaction_rules_are_parsed_from_the_blog():
    """"すべて満たす" / "2つ以上" / "いずれか1つ" must not all collapse to OR."""
    expected = {"base": ("all", 0), "bull": ("at_least", 2),
                "bear": ("any", 1), "tail_risk": ("all", 0)}
    for blog in BLOGS:
        sc = _scenarios(blog)
        for name, (rule, min_legs) in expected.items():
            assert sc[name]["satisfaction_rule"] == rule, (
                f"{blog.name}/{name}: rule {sc[name]['satisfaction_rule']!r} != {rule!r}")
            assert sc[name]["min_legs"] == min_legs, (
                f"{blog.name}/{name}: min_legs {sc[name]['min_legs']} != {min_legs}")


def test_an_all_scenario_does_not_fire_on_one_leg():
    """The defect this guards: every leg had and_group None, which the consumer
    contract reads as OR, so a 5-leg "すべて満たす" scenario looked fired on one."""
    scen = {"base": {"probability": 40, "satisfaction_rule": "all", "min_legs": 0,
                     "triggers": ["SPX 7,636.4 を終値で維持",
                                  "VIX 17 を終値で上回らない"]}}
    market = dict(MARKET)
    market["vix"] = {"price": 19.0, "prev_close": 18.0}  # this leg fails
    blk = bps._compute_trigger_distance(
        scen, market, BREADTH, "post-market", TODAY)[0]
    assert blk["met_leg_count"] == 1
    assert blk["scenario_satisfied"] is False


def test_at_least_rule_needs_its_minimum():
    scen = {"bull": {"probability": 22, "satisfaction_rule": "at_least", "min_legs": 2,
                     "triggers": ["SPX 7,636.4 を終値で維持",
                                  "NDX 29,116.3 を終値で維持",
                                  "VIX 17 を終値で上回らない"]}}
    market = dict(MARKET)
    market["nasdaq"] = {"price": 28000.0, "prev_close": 28100.0}
    blk = bps._compute_trigger_distance(
        scen, market, BREADTH, "post-market", TODAY)[0]
    assert blk["met_leg_count"] == 2 and blk["scenario_satisfied"] is True
    market["vix"] = {"price": 19.0, "prev_close": 18.0}
    blk2 = bps._compute_trigger_distance(
        scen, market, BREADTH, "post-market", TODAY)[0]
    assert blk2["met_leg_count"] == 1 and blk2["scenario_satisfied"] is False


def test_consecutive_day_leg_is_not_met_on_day_one():
    """condition_met must fold in the time basis, unlike met_close."""
    scen = {"tail_risk": {"probability": 10, "satisfaction_rule": "all", "min_legs": 0,
                          "triggers": ["SPX 7,436.32 を終値で割れ かつ "
                                       "VIX 23超を終値ベースで2日連続"]}}
    market = dict(MARKET)
    market["sp500"] = {"price": 7400.0, "prev_close": 7500.0}
    market["vix"] = {"price": 24.0, "prev_close": 22.0}  # day one only
    blk = bps._compute_trigger_distance(
        scen, market, BREADTH, "post-market", TODAY)[0]
    vix = [e for e in blk["trigger_distances"] if e["indicator"] == "VIX"][0]
    assert vix["met_close"] is True, "the level is breached today"
    assert vix["condition_met"] is False, "but two consecutive days are required"
    assert blk["scenario_satisfied"] is False

    market["vix"] = {"price": 25.0, "prev_close": 24.0}  # day two
    blk2 = bps._compute_trigger_distance(
        scen, market, BREADTH, "post-market", TODAY)[0]
    vix2 = [e for e in blk2["trigger_distances"] if e["indicator"] == "VIX"][0]
    assert vix2["condition_met"] is True
    assert blk2["scenario_satisfied"] is True


def test_premarket_leaves_conditions_undecided():
    """A provisional quote must not settle a closing condition."""
    scen = {"bear": {"probability": 28, "triggers": ["VIX 17超を終値ベースで2日連続"]}}
    market = dict(MARKET)
    market["vix"] = {"price": 25.0, "prev_close": 24.0}
    blk = bps._compute_trigger_distance(
        scen, market, BREADTH, "pre-market", TODAY)[0]
    assert blk["trigger_distances"][0]["condition_met"] is None
    assert blk["undecided_leg_count"] == 1


def test_coverage_records_a_dropped_leg_instead_of_hiding_it():
    """A leg no branch claims must surface in unevaluated_legs, not vanish."""
    scen = {"bear": {"probability": 30, "triggers": ["まったく未知の指標 12.5 割れ"]}}
    blk = bps._compute_trigger_distance(scen, MARKET, BREADTH, "post-market", TODAY)[0]
    assert blk["source_leg_count"] == 1
    assert blk["evaluated_leg_count"] == 0
    assert blk["unevaluated_legs"] == ["まったく未知の指標 12.5 割れ"]


# --- indicator assignment -------------------------------------------------

def test_russell_leg_is_not_claimed_by_the_oil_branch():
    """The 2026-08-31 phantom: "Russell 2,883.0 ... (IWM ≈ $286.86)" became
    "WTI Oil / target 883.0", which read as met every day."""
    scen = {"bear": {"probability": 28,
                     "triggers": ["Russell 2,883.0 終値割れ (IWM ≈ $286.86)"]}}
    entries = bps._compute_trigger_distance(
        scen, MARKET, BREADTH, "post-market", TODAY)[0]["trigger_distances"]
    assert len(entries) == 1
    assert entries[0]["indicator"] == "Russell 2000"
    assert entries[0]["target"] == 2883.0


def test_two_year_leg_does_not_become_a_ten_year_trigger():
    """"2年債 4.50%" used to inherit the preceding indicator name.

    parse_blog splits a "A + B" trigger line before this stage, so the legs
    arrive separately — the same shape the real blog produces.
    """
    scen = {"base": {"probability": 40,
                     "triggers": ["10年債 4.60〜4.806% のレンジ内 (終値)",
                                  "米2年債 4.50% 未満 (終値)"]}}
    entries = bps._compute_trigger_distance(
        scen, MARKET, BREADTH, "post-market", TODAY)[0]["trigger_distances"]
    by_ind = {e["indicator"]: e for e in entries}
    assert "US 2Y Yield" in by_ind, f"got {list(by_ind)}"
    assert by_ind["US 2Y Yield"]["target"] == 4.5
    assert by_ind["US 10Y Yield"]["target"] == 4.806


def test_curve_leg_is_not_read_as_a_ten_year_level():
    scen = {"bear": {"probability": 28, "triggers": ["2s10s が 30bp 割れを終値2日連続"]}}
    entries = bps._compute_trigger_distance(
        scen, MARKET, BREADTH, "post-market", TODAY)[0]["trigger_distances"]
    assert [e["indicator"] for e in entries] == ["2s10s Spread"]
    assert entries[0]["target"] == 30.0


def test_etf_conversion_dollar_sign_does_not_create_an_oil_target():
    """Any leg carrying an ETF conversion must not fall through to oil."""
    for leg in ["SPX 7,636.4 終値割れ (SPY ≈ $761.83)",
                "NDX 29,116.3 終値割れ (QQQ ≈ $708.71)",
                "Dow 52,359.0 終値割れ (DIA ≈ $523.06)"]:
        scen = {"bear": {"probability": 28, "triggers": [leg]}}
        entries = bps._compute_trigger_distance(
            scen, MARKET, BREADTH, "post-market", TODAY)[0]["trigger_distances"]
        assert all(e["indicator"] != "WTI Oil" for e in entries), leg


def test_real_oil_legs_still_resolve():
    scen = {"bear": {"probability": 28, "triggers": ["WTI 88.32 終値上抜け"]}}
    entries = bps._compute_trigger_distance(
        scen, MARKET, BREADTH, "post-market", TODAY)[0]["trigger_distances"]
    assert [e["indicator"] for e in entries] == ["WTI Oil"]
    assert entries[0]["target"] == 88.32


def test_no_entry_has_an_out_of_scale_target():
    """A target far outside its instrument's range means the wrong branch won."""
    bounds = {
        "VIX": (5, 100), "WTI Oil": (10, 200), "Copper": (1, 20),
        "US 2Y Yield": (0, 15), "US 5Y Yield": (0, 15),
        "US 10Y Yield": (0, 15), "US 30Y Yield": (0, 15),
        "2s10s Spread": (-200, 300), "Uptrend Ratio": (0, 100),
        "Breadth 8MA-200MA": (-50, 50), "Breadth-50 Raw": (0, 100),
        "Breadth Raw (200MA basis)": (0, 100),
        "S&P 500": (1000, 20000), "Nasdaq 100": (5000, 60000),
        "Dow Jones": (10000, 100000), "Russell 2000": (500, 10000),
    }
    for blog in BLOGS:
        for e in _all_entries(blog):
            lo, hi = bounds[e["indicator"]]
            assert lo <= e["target"] <= hi, (
                f"{blog.name}: {e['indicator']} target {e['target']} "
                f"out of range from leg {e['trigger'][:50]!r}")


# --- consecutive-day evaluation ------------------------------------------

def test_yield_two_day_trigger_can_see_the_previous_close():
    """Treasury entries used to carry only `value`, so met_prev was always None
    and a "終値2日連続" yield leg could never reach 2/2."""
    scen = {"bull": {"probability": 22,
                     "triggers": ["10年債 4.708% を終値2日連続下回る"]}}
    entry = bps._compute_trigger_distance(
        scen, MARKET, BREADTH, "post-market", TODAY)[0]["trigger_distances"][0]
    assert entry["required_days"] == 2
    assert entry["met_prev"] is True, "8/27 close 4.67 is below 4.708"
    assert entry["met_close"] is False, "8/28 close 4.73 is not"
    assert "前日充足" in entry["progress"]


def test_yield_two_day_trigger_reaches_full_confirmation():
    market = dict(MARKET)
    market["us10y"] = {"value": 4.90, "prev_close": 4.85}
    scen = {"bear": {"probability": 28,
                     "triggers": ["10年債 4.806% を終値2日連続上抜け"]}}
    entry = bps._compute_trigger_distance(
        scen, market, BREADTH, "post-market", TODAY)[0]["trigger_distances"][0]
    assert entry["met_prev"] is True and entry["met_close"] is True
    assert entry["progress"] == "2/2日達成"


# --- AND groups -----------------------------------------------------------

def test_tail_risk_and_legs_share_a_group_and_are_both_present():
    """A two-leg AND must survive as two tagged legs. If one is dropped the
    survivor looks sufficient on its own."""
    blk = [b for b in _distances(BLOGS[1]) if b["scenario"] == "tail_risk"][0]
    legs = blk["trigger_distances"]
    assert len(legs) == 2, [e["trigger"] for e in legs]
    gids = {e["and_group"] for e in legs}
    assert len(gids) == 1 and None not in gids, gids


def test_or_legs_are_not_tagged_as_and():
    blk = [b for b in _distances(BLOGS[1]) if b["scenario"] == "bear"][0]
    assert all(e["and_group"] is None for e in blk["trigger_distances"])


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


# --- consecutive-day conditions -------------------------------------------
# A leg written "終値3日連続" cannot be settled from today's close and the
# previous one. Returning True there fired such a leg on day 2 and contradicted
# the progress text, which already said "2/3日達成（2日分のみ確認可）".


def _verdict(trigger, met_close, met_prev):
    meta = bps._parse_trigger_metadata(trigger)
    entry = {"met_close": met_close, "met_prev": met_prev}
    return meta, bps._condition_fully_met(entry, meta, TODAY, is_official=True)


def test_a_two_day_condition_is_met_on_two_days():
    meta, verdict = _verdict("VIX 17超を終値2日連続", True, True)
    assert meta["required_days"] == 2
    assert verdict is True


def test_a_three_day_condition_is_not_met_on_two_days():
    meta, verdict = _verdict("VIX 17超を終値3日連続", True, True)
    assert meta["required_days"] == 3
    assert verdict is not True, (
        "a 3-day run cannot be confirmed from today + prev close alone"
    )


def test_a_three_day_condition_that_broke_today_is_a_definite_miss():
    _, verdict = _verdict("VIX 17超を終値3日連続", False, True)
    assert verdict is False


def test_progress_text_and_verdict_agree_for_long_runs():
    """The progress string and the verdict must not tell different stories."""
    for days in (2, 3, 4, 5):
        trigger = f"VIX 17超を終値{days}日連続"
        meta = bps._parse_trigger_metadata(trigger)
        entry = {"met_close": True, "met_prev": True, "met_current_quote": True}
        progress = bps._build_progress_string(entry, meta, TODAY, is_official=True)
        verdict = bps._condition_fully_met(entry, meta, TODAY, is_official=True)
        claims_full = progress.startswith(f"{days}/{days}日達成")
        assert claims_full == (verdict is True), (
            f"{days}日連続: progress={progress!r} verdict={verdict!r}"
        )


def test_a_long_run_never_satisfies_a_scenario():
    """An unconfirmable leg must not count towards a scenario or AND group."""
    _, verdict = _verdict("VIX 17超を終値3日連続", True, True)
    assert not (verdict is True)


# --- source-text audit ----------------------------------------------------
# source_leg_total counts legs in the parser's OUTPUT, so a scenario the parser
# cannot read contributes 0 and checks 18-20 pass on 0 of 0. The audit reads the
# article text instead.

_AUDIT_BLOG = """## シナリオ別プラン

### シナリオ 1 (Base): レンジ継続 — 筆者推定 **60%**

**{label1}**: SPX 7,700 を終値で維持 / VIX 17 を終値で上回らない

**アクション (合計 100%)**:
- コア: 30%
- 現金: 70%

### シナリオ 2 (Risk-On): 上放れ — 筆者推定 **40%**

**{label2}**: SPX 7,900 を終値2日連続上抜け / VIX 14 を終値2日連続下回る

**アクション (合計 100%)**:
- コア: 50%
- 現金: 50%
"""


def _audit(label1="トリガー (すべて満たす)", label2="トリガー (いずれか1つ)"):
    text = _AUDIT_BLOG.format(label1=label1, label2=label2)
    spec = parse_blog_text(text)
    return bps._audit_source_triggers(text, spec.scenarios), spec


def parse_blog_text(text):
    """parse_blog takes a path; write the text out so the audit sees the same."""
    import tempfile
    tmpdir = tempfile.mkdtemp()
    path = Path(tmpdir) / "2026-09-07-weekly-strategy.md"
    path.write_text(text, encoding="utf-8")
    return parse_blog(path)


def test_source_audit_passes_when_every_scenario_parsed():
    audit, spec = _audit()
    assert audit["applicable"] is True
    assert audit["raw_scenario_count"] == 2
    assert audit["raw_with_trigger_block"] == 2
    assert audit["gaps"] == [], audit["gaps"]
    assert all(sc.triggers for sc in spec.scenarios.values())


def test_source_audit_flags_a_label_the_parser_cannot_read():
    """An unrecognised label leaves the legs in the article but out of the plan."""
    audit, spec = _audit(label2="判定基準")
    dropped = [name for name, sc in spec.scenarios.items() if not sc.triggers]
    assert dropped, "expected the parser to drop the relabelled scenario"
    assert audit["gaps"], (
        "coverage would report 0 of 0 legs for the dropped scenario; "
        "the audit must flag it"
    )
    assert any("0 legs parsed" in g["reason"] for g in audit["gaps"])


def test_source_audit_flags_every_scenario_when_all_labels_change():
    audit, _ = _audit(label1="判定基準", label2="判定基準")
    assert len(audit["gaps"]) == 2


def test_source_audit_is_not_applicable_without_japanese_headings():
    text = "## Scenarios\n\n### Base case (60%)\n\n**Trigger**: SPX 7,700 hold\n"
    audit = bps._audit_source_triggers(text, {})
    assert audit["applicable"] is False
    assert audit["gaps"] == []


def test_source_audit_clean_on_the_tracked_fixtures():
    for blog in BLOGS:
        spec = parse_blog(blog)
        audit = bps._audit_source_triggers(
            blog.read_text(encoding="utf-8"), spec.scenarios)
        assert audit["applicable"] is True, blog.name
        assert audit["gaps"] == [], f"{blog.name}: {audit['gaps']}"
        assert audit["raw_with_trigger_block"] >= 4, blog.name


def test_section_heading_is_not_counted_as_a_scenario():
    """'## シナリオ別プラン' is a section title, not a scenario block."""
    audit, _ = _audit()
    assert audit["raw_scenario_count"] == 2


# --- instruments the 2026-09-07 article introduced -------------------------


def test_five_year_yield_legs_are_evaluated():
    """米5年債 legs were unevaluable until the 5Y branch existed."""
    blog = FIXTURES / "2026-09-07-weekly-strategy.md"
    entries = _all_entries(blog)
    five = [e for e in entries if "5年債" in e["trigger"]]
    assert five, "the fixture should carry 米5年債 legs"
    for e in five:
        assert e["indicator"] == "US 5Y Yield", e
        assert e["current"] == MARKET["us5y"]["value"]
        assert e["target"] in (4.45, 4.60), e


def test_breadth_raw_leg_is_evaluated_against_the_raw_series():
    blog = FIXTURES / "2026-09-07-weekly-strategy.md"
    raw = [e for e in _all_entries(blog)
           if "生値" in e["trigger"] and "BREADTH" in e["trigger"].upper()]
    assert raw, "the fixture should carry the Breadth 生値 leg"
    for e in raw:
        assert e["indicator"] == "Breadth Raw (200MA basis)", e
        assert e["current"] == BREADTH["breadth_raw"]
        assert e["target"] == 64.0


def test_breadth_raw_does_not_steal_the_spread_leg():
    """A pt-quoted spread leg must still reach the 8MA-200MA branch."""
    scen = {"bear": {"probability": 28, "triggers": [
        "Breadth 8MA と 200MA の差が +7pt 割れ"]}}
    tds = bps._compute_trigger_distance(scen, MARKET, BREADTH, "post-market", TODAY)
    entries = [e for d in tds for e in d["trigger_distances"]]
    assert entries and entries[0]["indicator"] == "Breadth 8MA-200MA"
