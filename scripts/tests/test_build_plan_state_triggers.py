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

# Each article is evaluated on a session inside its own week. A leg can carry
# one threshold per date ("9/8 に 23.56% 超、9/9 に 24.38% 超..."), so evaluating
# the 2026-09-07 article on an August date leaves that leg with no applicable
# threshold — correctly unevaluated, but not what these tests mean to exercise.
FIXTURE_TODAY = {
    "2026-08-24-weekly-strategy.md": date(2026, 8, 24),
    "2026-08-31-weekly-strategy.md": date(2026, 8, 31),
    # 2026-09-07 is Labor Day; the week's first session is the 8th.
    "2026-09-07-weekly-strategy.md": date(2026, 9, 8),
}

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


# Long-duration Treasuries are the AND partner of the 2026-09-14 Tail Risk rate
# leg, so that group cannot be judged without a TLT price.
ETFS = {"TLT": {"price": 80.87}}


def _distances(blog_path, today=None):
    when = today or FIXTURE_TODAY.get(getattr(blog_path, "name", ""), TODAY)
    return bps._compute_trigger_distance(
        _scenarios(blog_path), MARKET, BREADTH, "post-market", when, ETFS)


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


def _all_entries(blog_path, today=None):
    return [e for blk in _distances(blog_path, today)
            for e in blk["trigger_distances"]]


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


# --- date-qualified thresholds --------------------------------------------
# "Uptrend Ratio が GREEN へ転換 (9/8 に 23.56% 超、9/9 に 24.38% 超、9/10 に
# 22.46% 超、または 9/11 に 22.63% 超)" carries one threshold per date. Taking
# the first number applied Monday's hurdle all week: it both misses a real flip
# (9/10 at 23.0% clears 22.46% but not 23.56%) and invents one.

_GREEN_LEG = ("Uptrend Ratio が GREEN へ転換 (9/8 に 23.56% 超、9/9 に 24.38% 超、"
              "9/10 に 22.46% 超、または 9/11 に 22.63% 超)")


def _green_entry(today, ratio):
    scen = {"bull": {"probability": 20, "triggers": [_GREEN_LEG],
                     "satisfaction_rule": "any", "min_legs": 1}}
    breadth = dict(BREADTH, uptrend_ratio=ratio)
    tds = bps._compute_trigger_distance(
        scen, MARKET, breadth, "post-market", today)
    entries = [e for d in tds for e in d["trigger_distances"]]
    return (entries[0] if entries else None), tds[0]["unevaluated_legs"]


def test_dated_threshold_uses_the_hurdle_for_today():
    entry, unevaluated = _green_entry(date(2026, 9, 10), 23.0)
    assert entry is not None and not unevaluated
    assert entry["target"] == 22.46, "9/10 must use its own hurdle"


def test_dated_threshold_does_not_reuse_mondays_number():
    """23.0% on 9/10 clears 22.46%; the first-number rule called it a miss."""
    entry, _ = _green_entry(date(2026, 9, 10), 23.0)
    assert entry["target"] != 23.56


def test_each_date_gets_its_own_hurdle():
    for day, expected in ((8, 23.56), (9, 24.38), (10, 22.46), (11, 22.63)):
        entry, _ = _green_entry(date(2026, 9, day), 23.0)
        assert entry["target"] == expected, f"9/{day}"


def test_a_date_with_no_hurdle_is_left_unevaluated():
    """Falling back to another day's number would be a fabricated verdict."""
    entry, unevaluated = _green_entry(date(2026, 9, 14), 23.0)
    assert entry is None
    assert unevaluated, "the leg must be reported, not silently dropped"


# --- consecutive CSV observations -----------------------------------------


def test_csv_two_point_condition_is_not_met_on_one_reading():
    """"64.0% を CSV 2データ点連続で下回る" needs two readings, not one."""
    trigger = "Breadth 生値 (200日線上) が 64.0% を CSV 2データ点連続で下回る"
    meta = bps._parse_trigger_metadata(trigger)
    assert meta["required_days"] == 2, "データ点連続 must be read as consecutive"

    scen = {"bear": {"probability": 26, "triggers": [trigger],
                     "satisfaction_rule": "any", "min_legs": 1}}
    breadth = dict(BREADTH, breadth_raw=63.0)
    tds = bps._compute_trigger_distance(
        scen, MARKET, breadth, "post-market", TODAY)
    entry = tds[0]["trigger_distances"][0]
    assert entry["met_close"] is True, "today's reading is below the level"
    assert entry["condition_met"] is not True, (
        "no prior observation is on file, so consecutiveness is undecided"
    )
    assert tds[0]["scenario_satisfied"] is False


def test_csv_two_point_progress_says_no_prior_observation():
    trigger = "Breadth 生値 (200日線上) が 64.0% を CSV 2データ点連続で下回る"
    meta = bps._parse_trigger_metadata(trigger)
    entry = {"met_close": True, "met_prev": None, "met_current_quote": True}
    progress = bps._build_progress_string(entry, meta, TODAY, is_official=True)
    assert "判定不可" in progress, progress


# --- satisfaction rules at the real entry point ---------------------------


def test_scenario_dict_without_a_rule_does_not_fire():
    """A missing rule is a broken contract, not an OR."""
    scen = {"bull": {"probability": 20,
                     "triggers": ["SPX 7,000 を終値で上回る"]}}
    tds = bps._compute_trigger_distance(
        scen, MARKET, BREADTH, "post-market", TODAY)
    assert tds[0]["trigger_distances"][0]["condition_met"] is True
    assert tds[0]["rule_missing"] is True
    assert tds[0]["scenario_satisfied"] is False, (
        "one met leg must not fire a scenario whose rule never arrived"
    )


def test_at_least_two_needs_two_legs():
    scen = {"bull": {"probability": 20, "satisfaction_rule": "at_least",
                     "min_legs": 2,
                     "triggers": ["SPX 7,000 を終値で上回る",
                                  "VIX 5 を終値で下回る"]}}
    tds = bps._compute_trigger_distance(
        scen, MARKET, BREADTH, "post-market", TODAY)
    assert tds[0]["met_leg_count"] == 1
    assert tds[0]["scenario_satisfied"] is False


# --- independent mandatory conditions (gates) ------------------------------


def test_a_gate_blocks_the_scenario_even_when_the_legs_hold():
    scen = {"bull": {"probability": 20, "satisfaction_rule": "any", "min_legs": 1,
                     "triggers": ["SPX 7,000 を終値で上回る"],
                     "gates": ["必須条件: 9/11(金) の CPI 発表後の終値でも維持"]}}
    tds = bps._compute_trigger_distance(
        scen, MARKET, BREADTH, "post-market", TODAY)
    assert tds[0]["met_leg_count"] == 1
    assert tds[0]["gates_unevaluated"] is True
    assert tds[0]["scenario_satisfied"] is False


def test_the_0907_risk_on_scenario_carries_its_cpi_gate():
    blog = FIXTURES / "2026-09-07-weekly-strategy.md"
    spec = parse_blog(blog)
    gates = spec.scenarios["bull"].gates
    assert gates, "the article states an independent mandatory condition"
    assert "CPI" in gates[0]


def test_the_0907_risk_on_scenario_cannot_fire_on_price_alone():
    """The reviewer's counterexample: price legs alone must not fire it."""
    blog = FIXTURES / "2026-09-07-weekly-strategy.md"
    scen = _scenarios(blog)
    market = dict(MARKET)
    market["sp500"] = {"price": 7750.0, "prev_close": 7740.0}
    market["us10y"] = {"value": 4.69, "prev_close": 4.70}
    market["us5y"] = {"value": 4.40, "prev_close": 4.41}
    tds = bps._compute_trigger_distance(
        scen, market, BREADTH, "post-market", date(2026, 9, 9))
    bull = [d for d in tds if d["scenario"] == "bull"][0]
    assert bull["met_leg_count"] >= 2, "the price legs do hold in this input"
    assert bull["satisfaction_rule"] == "at_least" and bull["min_legs"] == 2
    assert bull["scenario_satisfied"] is False, (
        "the article requires the CPI-day close as well"
    )


# --- the audit must not be fooled by equal probabilities -------------------
# Probability is not an identifier. Joining on it let a block whose conditions
# vanished borrow the other block's legs when both scenarios read 50%.

_TIE_BLOG = """## シナリオ別プラン

### シナリオ 1 (Base): レンジ継続 — 筆者推定 **50%**

**{label1}**: SPX 7,700 を終値で維持 / VIX 17 を終値で上回らない

**アクション (合計 100%)**:
- コア: 30%
- 現金: 70%

### シナリオ 2 (Risk-On): 上放れ — 筆者推定 **50%**

**{label2}**: SPX 7,900 を終値2日連続上抜け / VIX 14 を終値2日連続下回る

**アクション (合計 100%)**:
- コア: 50%
- 現金: 50%
"""


def _tie_audit(label1="トリガー (すべて満たす)", label2="トリガー (いずれか1つ)"):
    text = _TIE_BLOG.format(label1=label1, label2=label2)
    spec = parse_blog_text(text)
    return bps._audit_source_triggers(text, spec.scenarios), spec


def test_equal_probability_scenarios_still_pass_when_both_parse():
    audit, spec = _tie_audit()
    assert audit["gaps"] == [], audit["gaps"]
    assert all(sc.triggers for sc in spec.scenarios.values())


def test_equal_probability_does_not_hide_a_dropped_scenario():
    """The reviewer's counterexample: both 50%, one label unreadable."""
    audit, spec = _tie_audit(label2="判定基準")
    dropped = [n for n, sc in spec.scenarios.items() if not sc.triggers]
    assert dropped, "the relabelled scenario should have lost its legs"
    assert audit["gaps"], (
        "a tie on probability must not let the other scenario's legs "
        "stand in for the dropped one"
    )


def test_audit_records_how_it_joined():
    audit, _ = _tie_audit()
    assert audit["join"] in ("position", "probability")


def test_audit_reports_a_count_mismatch_it_cannot_resolve():
    """Fewer parsed scenarios than article blocks, with probabilities tied."""
    text = _TIE_BLOG.format(label1="トリガー (すべて満たす)",
                            label2="トリガー (いずれか1つ)")
    spec = parse_blog_text(text)
    only_one = {"base": spec.scenarios["base"]}
    audit = bps._audit_source_triggers(text, only_one)
    assert audit["gaps"], "2 article blocks vs 1 parsed scenario must not pass"




# --- grouped triggers (2026-09-14) -----------------------------------------
# The 2026-09-14 article states its 警戒 triggers as three labelled groups with
# DIFFERENT counts and fires on any ONE group, and its Tail Risk as two AND legs
# whose members are "または" alternatives. Flattening either shape silently
# changed what fires: one CSV leg satisfied a group the article needs two for,
# and the Tail Risk OR-legs collapsed into a single AND chain.

BLOG_0914 = FIXTURES / "2026-09-14-weekly-strategy.md"


def _groups(blog_path, scenario):
    return _scenarios(blog_path)[scenario]["trigger_groups"]


def test_0914_bear_keeps_each_group_with_its_own_count():
    groups = _groups(BLOG_0914, "bear")
    assert [(g["rule"], g["min_legs"], len(g["legs"])) for g in groups] == [
        ("any", 1, 4),        # 単日確定系 (1本成立)
        ("any", 1, 3),        # 終値2日連続系 (1本成立)
        ("at_least", 2, 3),   # CSV 系 (2本成立)  <- the count that was lost
    ]
    assert "CSV" in groups[2]["label"]


def test_0914_bear_csv_group_needs_two_legs_not_one():
    """One CSV leg must NOT fire the group the article needs two for."""
    csv_group = _groups(BLOG_0914, "bear")[2]
    meta = {"group": "bear#g2", "rule": csv_group["rule"],
            "min_legs": csv_group["min_legs"],
            "leg_total": len(csv_group["legs"]), "unevaluated": 0}

    one_met = [{"condition_met": True}, {"condition_met": False},
               {"condition_met": False}]
    two_met = [{"condition_met": True}, {"condition_met": True},
               {"condition_met": False}]
    assert bps._evaluate_group(meta, one_met)["satisfied"] is False
    assert bps._evaluate_group(meta, two_met)["satisfied"] is True


def test_0914_tail_risk_is_and_of_or_groups():
    groups = _groups(BLOG_0914, "tail_risk")
    assert _scenarios(BLOG_0914)["tail_risk"]["satisfaction_rule"] == "all"
    assert [(g["rule"], g["min_legs"], len(g["legs"])) for g in groups] == [
        ("any", 1, 2),   # 脚1: VIX または SPX
        ("any", 1, 3),   # 脚2: WTI または 10年債 または (TLT かつ 30年債)
    ]
    # The inner AND must survive as ONE leg, not two independent alternatives.
    assert any("かつ" in leg for leg in groups[1]["legs"])


def test_0914_russell_level_is_not_the_index_name():
    """'Russell 2000 2,883.0' must read 2883.0, not the 2000 in the name."""
    legs = [e for e in _all_entries(BLOG_0914, date(2026, 9, 14))
            if e["indicator"] == "Russell 2000"]
    assert legs, "no Russell leg was evaluated"
    assert all(e["target"] != 2000.0 for e in legs), legs
    assert any(e["target"] == 2883.0 for e in legs), legs


def test_0914_every_leg_is_evaluated():
    for blk in _distances(BLOG_0914, date(2026, 9, 14)):
        assert not blk["unevaluated_legs"], (
            f"{blk['scenario']}: {blk['unevaluated_legs']}")


# --- 2026-09-28 review: relative EMA leg and the VIX intraday escalation ---


_EMA_LEG = ("Breadth 生値が同じデータ点の EMA(8) を上回る状態を CSV 2データ点連続 "
            "(現在 生値 47.70%、EMA(8) 52.59%、差 +4.89pt)")


def _single(trigger, breadth):
    scen = {"bull": {"probability": 16, "triggers": [trigger],
                     "satisfaction_rule": "all", "min_legs": 0}}
    return bps._compute_trigger_distance(
        scen, MARKET, breadth, "post-market", TODAY)[0]


def test_ema_leg_compares_raw_with_same_point_ema_not_a_quoted_number():
    """The 47.70% in the parenthesis is a snapshot, not the threshold."""
    blk = _single(_EMA_LEG, dict(BREADTH, breadth_raw=48.0, breadth_8ma=52.0))
    (entry,) = blk["trigger_distances"]
    assert entry["target"] == 52.0, entry
    assert entry["current"] == 48.0
    assert entry["met_close"] is False, "raw below its EMA(8) must not be met"
    assert entry["required_days"] == 2


def test_ema_leg_above_is_met_today_but_consecutiveness_stays_undecided():
    blk = _single(_EMA_LEG, dict(BREADTH, breadth_raw=55.0, breadth_8ma=52.0))
    (entry,) = blk["trigger_distances"]
    assert entry["met_close"] is True
    assert entry["condition_met"] is not True, "one CSV point is not two"
    assert blk["scenario_satisfied"] is not True


def test_vix_intraday_escalation_is_its_own_route():
    """'VIX 23超を終値2日連続 (26超はザラ場で確認し即時扱い)' is two routes."""
    leg = "VIX 23超を終値2日連続 (26超はザラ場で確認し即時扱い)"
    legs = bps._split_vix_intraday_escalation(leg)
    assert len(legs) == 2, legs
    close_meta = bps._parse_trigger_metadata(legs[0])
    fast_meta = bps._parse_trigger_metadata(legs[1])
    assert (close_meta["time_basis"], close_meta["required_days"]) == ("daily_close", 2)
    assert (fast_meta["time_basis"], fast_meta["required_days"]) == ("intraday", 1)


def test_0928_tail_fires_on_intraday_vix_27_with_10y_held():
    """Prior VIX 14.87 -> 27 intraday, 10Y 5.17%: Tail must fire directly."""
    scen = {"tail_risk": {
        "probability": 12, "triggers": [],
        "satisfaction_rule": "all", "min_legs": 0,
        "trigger_groups": [
            {"label": "脚1", "rule": "any", "min_legs": 1, "legs": [
                "VIX 23超を終値2日連続 (26超はザラ場で確認し即時扱い)",
                "SPX 7,232.1 を終値2日連続割れ"]},
            {"label": "脚2", "rule": "any", "min_legs": 1, "legs": [
                "脚1 が成立した日の終値で 10年債 5.15% 以上 (現在 5.170%)",
                "WTI $100 終値上抜け"]},
        ]}}
    market = dict(MARKET, vix={"price": 27.0, "prev_close": 14.87},
                  us10y={"value": 5.17, "prev_close": 5.17})
    blk = bps._compute_trigger_distance(
        scen, market, BREADTH, "post-market", TODAY)[0]
    vix = [e for e in blk["trigger_distances"] if e["indicator"] == "VIX"]
    assert sorted(e["target"] for e in vix) == [23.0, 26.0], vix
    assert any(e["target"] == 26.0 and e["condition_met"] is True for e in vix)
    assert blk["scenario_satisfied"] is True
    g0 = blk["trigger_groups"][0]
    assert g0["leg_total"] == 3, "VIX close + VIX intraday + SPX"
    assert g0["met_legs"] + g0["undecided_legs"] <= g0["leg_total"], g0


# --- 2026-09-28 review round 2: intraday before the close, CSV prior points --


def _fetcher():
    fspec = importlib.util.spec_from_file_location(
        "fb", ROOT / ".claude/skills/breadth-chart-analyst/scripts/fetch_breadth_csv.py")
    fb = importlib.util.module_from_spec(fspec)
    fspec.loader.exec_module(fb)
    return fb


def test_fetcher_carries_the_previous_csv_point():
    fb = _fetcher()
    rows = [
        fb.BreadthData(date="2026-09-23", sp500_price=770.0, breadth_raw=0.499,
                       breadth_200ma=0.632, breadth_8ma=0.537,
                       breadth_50_raw=0.2934, trend="-1"),
        fb.BreadthData(date="2026-09-24", sp500_price=771.0, breadth_raw=0.477,
                       breadth_200ma=0.6303, breadth_8ma=0.5259,
                       breadth_50_raw=0.2635, trend="-1"),
    ]
    ups = [fb.UptrendData(date="2026-09-24", ratio=0.1368, ma_10=0.1375,
                          slope=0.001, trend="up"),
           fb.UptrendData(date="2026-09-25", ratio=0.1385, ma_10=0.1379,
                          slope=0.0004, trend="up")]
    r = fb.analyze(rows, ups, [])
    assert r.prev_breadth_date == "2026-09-23"
    assert r.prev_breadth_raw == 49.9
    assert r.prev_breadth_8ma == 53.7
    assert r.prev_uptrend_date == "2026-09-24"
    assert r.prev_uptrend_ratio == 13.68


_BULL_LEGS = [
    _EMA_LEG,
    "Breadth 生値 45% 以上を CSV 2データ点連続",
    "Uptrend Ratio 15.52% 超を CSV 2データ点連続 (色ではなく水準で判定、現在 13.85%)",
]


def _bull(breadth, timing="pre-market"):
    scen = {"bull": {"probability": 16, "triggers": list(_BULL_LEGS),
                     "satisfaction_rule": "all", "min_legs": 0}}
    return bps._compute_trigger_distance(scen, MARKET, breadth, timing, TODAY)[0]


def test_csv_partial_restore_confirms_two_points_each_against_its_own_ema():
    """Each point is compared with ITS OWN EMA(8); CSV points are settled data,
    so the verdict does not wait for a post-market run."""
    breadth = dict(BREADTH, breadth_raw=55.0, breadth_8ma=52.0, uptrend_ratio=16.0,
                   breadth_raw_prev=54.0, breadth_8ma_prev=53.0,
                   uptrend_ratio_prev=15.9)
    blk = _bull(breadth)
    flags = [e["condition_met"] for e in blk["trigger_distances"]]
    assert flags == [True, True, True], blk["trigger_distances"]
    assert blk["scenario_satisfied"] is True


def test_csv_prior_point_below_its_own_ema_breaks_the_run():
    # Prior raw 54 is above TODAY's EMA 52 but below its own EMA 55.
    breadth = dict(BREADTH, breadth_raw=55.0, breadth_8ma=52.0, uptrend_ratio=16.0,
                   breadth_raw_prev=54.0, breadth_8ma_prev=55.0,
                   uptrend_ratio_prev=15.9)
    blk = _bull(breadth)
    ema = blk["trigger_distances"][0]
    assert ema["met_prev"] is False
    assert ema["condition_met"] is False
    assert blk["scenario_satisfied"] is False


def test_csv_without_prior_point_stays_undecided():
    breadth = dict(BREADTH, breadth_raw=55.0, breadth_8ma=52.0, uptrend_ratio=16.0)
    blk = _bull(breadth)
    assert all(e["condition_met"] is None for e in blk["trigger_distances"])


_TAIL_0928 = {"tail_risk": {
    "probability": 12, "triggers": [],
    "satisfaction_rule": "all", "min_legs": 0,
    "trigger_groups": [
        {"label": "脚1", "rule": "any", "min_legs": 1, "legs": [
            "VIX 23超を終値2日連続 (26超はザラ場で確認し即時扱い)",
            "SPX 7,232.1 を終値2日連続割れ"]},
        {"label": "脚2", "rule": "any", "min_legs": 1, "legs": [
            "10年債 5.15% 以上を脚1 成立日の終値で確認 "
            "(脚1 が VIX 26 超のザラ場で成立した場合は前営業日終値で判定)",
            "WTI $100 終値上抜け "
            "(脚1 が VIX 26 超のザラ場で成立した場合は当日ザラ場の $100 超で判定)"]},
    ]}}


def _tail(market, timing):
    return bps._compute_trigger_distance(
        _TAIL_0928, market, BREADTH, timing, TODAY)[0]


def test_intraday_vix_fires_before_the_close():
    market = dict(MARKET, vix={"price": 27.0, "prev_close": 14.87},
                  us10y={"value": 5.17, "prev_close": 5.17})
    blk = _tail(market, "pre-market")
    fast = [e for e in blk["trigger_distances"]
            if e["indicator"] == "VIX" and e["target"] == 26.0]
    assert fast and fast[0]["condition_met"] is True, fast
    assert blk["scenario_satisfied"] is True


def test_intraday_route_reads_the_prior_close_for_rates():
    """Prior 10Y 5.17%, today 5.10%: the intraday route judges on the prior close."""
    market = dict(MARKET, vix={"price": 27.0, "prev_close": 14.87},
                  us10y={"value": 5.10, "prev_close": 5.17})
    for timing in ("pre-market", "post-market"):
        blk = _tail(market, timing)
        leg2 = [e for e in blk["trigger_distances"]
                if e["or_group"] == "tail_risk#g1"]
        # Leg 2 must read rates and oil only — never the "VIX 26" it mentions.
        assert {e["indicator"] for e in leg2} == {"US 10Y Yield", "WTI Oil"}, leg2
        prior = [e for e in leg2 if e.get("route") == "intraday_partner"
                 and e["indicator"] == "US 10Y Yield"]
        assert prior and prior[0]["condition_met"] is True, leg2
        assert blk["scenario_satisfied"] is True, timing


def test_prior_close_rate_route_does_not_pair_with_the_closing_vix_route():
    """VIX 23 closed twice, but no intraday 26 break: today's close decides rates."""
    market = dict(MARKET, vix={"price": 24.0, "prev_close": 24.5},
                  us10y={"value": 5.10, "prev_close": 5.17})
    blk = _tail(market, "post-market")
    leg2 = [e for e in blk["trigger_distances"] if e["or_group"] == "tail_risk#g1"]
    assert {e["indicator"] for e in leg2} == {"US 10Y Yield", "WTI Oil"}, leg2
    assert blk["scenario_satisfied"] is False, blk["trigger_distances"]


def test_intraday_leg1_does_not_pair_with_the_closing_leg2():
    """VIX 14.87 -> 27 intraday, 10Y 5.10 -> 5.17: the intraday route judges
    rates on the PRIOR close (5.10), so Tail must not fire on today's 5.17."""
    market = dict(MARKET, vix={"price": 27.0, "prev_close": 14.87},
                  us10y={"value": 5.17, "prev_close": 5.10})
    for timing in ("pre-market", "post-market"):
        blk = _tail(market, timing)
        assert blk["scenario_satisfied"] is False, (timing, blk["trigger_distances"])
        assert blk["route_verdicts"]["intraday"] is False, blk["route_verdicts"]


def test_closing_routes_still_fire_on_their_own():
    """VIX 23 closed twice and 10Y closed above 5.15: the closing path fires."""
    market = dict(MARKET, vix={"price": 24.0, "prev_close": 24.5},
                  us10y={"value": 5.17, "prev_close": 5.10})
    blk = _tail(market, "post-market")
    assert blk["route_verdicts"]["close"] is True, blk["route_verdicts"]
    assert blk["scenario_satisfied"] is True


def test_intraday_oil_route_uses_the_live_quote():
    market = dict(MARKET, vix={"price": 27.0, "prev_close": 14.87},
                  us10y={"value": 5.10, "prev_close": 5.10},
                  oil={"price": 101.0, "prev_close": 96.0})
    blk = _tail(market, "pre-market")
    oil = [e for e in blk["trigger_distances"]
           if e["indicator"] == "WTI Oil" and e.get("route") == "intraday_partner"]
    assert oil and oil[0]["condition_met"] is True, blk["trigger_distances"]
    assert blk["scenario_satisfied"] is True


def test_output_path_confined_to_allowed_dirs(tmp_path=None):
    # The unattended runner may execute this script, so --output must not be
    # usable to write a repository file when DAP_ALLOWED_OUTPUT_DIRS is set.
    import os
    import tempfile
    base = Path(tempfile.mkdtemp())
    allowed = base / "reports"
    allowed.mkdir()
    old = os.environ.get("DAP_ALLOWED_OUTPUT_DIRS")
    os.environ["DAP_ALLOWED_OUTPUT_DIRS"] = f"/tmp{os.pathsep}{allowed}"
    try:
        assert bps._output_path_allowed(str(allowed / "plan_state.json"))
        assert bps._output_path_allowed("/tmp/plan_state.json")
        assert not bps._output_path_allowed(str(base / "trading" / "x.json"))
        # "../" must not step out of an allowed directory
        assert not bps._output_path_allowed(str(allowed / ".." / "x.json"))
        assert not bps._output_path_allowed(str(ROOT / "trading" / "x.json"))
        del os.environ["DAP_ALLOWED_OUTPUT_DIRS"]
        assert bps._output_path_allowed(str(ROOT / "trading" / "x.json"))
    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)
        if old is None:
            os.environ.pop("DAP_ALLOWED_OUTPUT_DIRS", None)
        else:
            os.environ["DAP_ALLOWED_OUTPUT_DIRS"] = old


def test_group_short_of_its_label_count_never_fires():
    # The parser keeps "3本成立" even when only two legs were parsed. With both
    # parsed legs met, the group must still not be satisfied.
    group = {"rule": "at_least", "min_legs": 3}
    legs = [{"condition_met": True}, {"condition_met": True}]
    assert bps._evaluate_group(group, legs)["satisfied"] is False


# The runner must stay at the END of this file: CI executes it with
# `python <file>`, and it enumerates globals() when it runs, so any test
# defined below it would never execute.
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
