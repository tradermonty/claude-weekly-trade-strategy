"""Tail Risk with a second OR route ("経路B").

The 2026-11-09 article fires Tail Risk on "(leg 1 AND leg 2) OR (VIX 26超を終値
2日連続 AND Breadth 生値 50.0% 未満の CSV 2データ点連続)". Until this fix the
parser read only path A, and every coverage check still passed, so the
unattended plan could never report path B as fired.
"""
import copy
import importlib.util
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from trading.layer2.tools.strategy_parser import parse_blog  # noqa: E402


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bps = _load("bps_alt", ".claude/skills/daily-action-plan/scripts/build_plan_state.py")
vp = _load("vp_alt", ".claude/skills/daily-action-plan/scripts/verify_plan.py")

FIXTURES = ROOT / "scripts/tests/fixtures/plan_state"
# Kept outside plan_state/: that folder doubles as the timeline corpus in CI,
# and this excerpt is not a complete article.
BLOG = ROOT / "scripts/tests/fixtures/tail_path/2026-11-09-weekly-strategy.md"
TODAY = date(2026, 11, 10)


def _market(vix, vix_prev, y10=4.86, y10_prev=4.86, oil=90.83):
    return {
        "quotes": {
            "^VIX": {"price": vix, "previousClose": vix_prev},
            "^GSPC": {"price": 7376.86, "previousClose": 7350.35},
            "^NDX": {"price": 26989.99, "previousClose": 26900.0},
            "^DJI": {"price": 51285.73, "previousClose": 51200.0},
            "^RUT": {"price": 2400.0, "previousClose": 2390.0},
            "GCUSD": {"price": 4079.6, "previousClose": 4070.0},
            "CLUSD": {"price": oil, "previousClose": oil},
            "HGUSD": {"price": 6.0435, "previousClose": 6.04},
        },
        "treasury": {
            "year2": 4.51, "year5": 4.60, "year10": y10, "year30": 5.26,
            "_prev": {"year2": 4.51, "year5": 4.60, "year10": y10_prev,
                      "year30": 5.26},
        },
    }


def _breadth(raw, raw_prev):
    return {
        "breadth_date": "2026-11-10", "prev_breadth_date": "2026-11-09",
        "breadth_200ma": 60.0, "breadth_8ma": 59.0, "cross_diff": 1.0,
        "breadth_50_raw": 50.0, "breadth_raw": raw, "prev_breadth_raw": raw_prev,
        "prev_breadth_8ma": 59.5,
        "uptrend_date": "2026-11-10", "uptrend_ratio": 19.67,
        "uptrend_color": "RED", "uptrend_class": "weak",
    }


# Base states two of its legs as prose ("…がそろわない"), which no branch can
# measure. The unattended run declares them manual-only; so do these tests.
MANUAL_ONLY = ["深化の CSV 系が 2本そろわない", "復元条項の 3条件がそろわない"]


def _built(vix, vix_prev, raw, raw_prev, **kw):
    return bps.build_plan_state(
        "post-market", _market(vix, vix_prev, **kw), _breadth(raw, raw_prev),
        str(BLOG), today=TODAY, manual_only_legs=MANUAL_ONLY)


def _tail(ps):
    blk = next(b for b in ps["analysis"]["trigger_distances"]
               if b["scenario"] == "tail_risk")
    rule = ps["analysis"]["trigger_coverage"]["scenario_rules"]["tail_risk"]
    return blk, rule


def _contract_failures(ps):
    result = vp.verify(ps, {}, {})
    return [(c["num"], c["detail"]) for c in result.checks
            if c["status"] == "FAIL" and c["num"] in (18, 19, 20, 21, 22)]


# --- parser ----------------------------------------------------------------

def test_parser_reads_path_b_as_its_own_route():
    tail = parse_blog(BLOG).scenarios["tail_risk"]
    assert tail.satisfaction_rule == "all"
    assert len(tail.trigger_groups) == 2          # path A: leg 1, leg 2
    assert len(tail.alternative_paths) == 1
    path = tail.alternative_paths[0]
    assert path.label == "経路B"
    assert path.satisfaction_rule == "all"
    assert [g.legs for g in path.trigger_groups] == [
        ["VIX 26超を終値2日連続"],
        ["Breadth 生値 50.0% 未満を最新の CSV 2データ点連続"],
    ]


def test_path_b_legs_stay_out_of_path_a():
    tail = parse_blog(BLOG).scenarios["tail_risk"]
    primary = " ".join(leg for g in tail.trigger_groups for leg in g.legs)
    assert "50.0% 未満" not in primary
    assert "VIX 26超を終値2日連続" not in primary


def test_older_articles_carry_no_alternative_route():
    for name in ("2026-08-24", "2026-08-31", "2026-09-07", "2026-09-14"):
        spec = parse_blog(FIXTURES / f"{name}-weekly-strategy.md")
        for key, sc in spec.scenarios.items():
            assert sc.alternative_paths == [], f"{name}/{key}"


def test_allocations_still_total_100():
    for key, sc in parse_blog(BLOG).scenarios.items():
        assert round(sum(sc.allocation.values()), 6) == 100, key


# --- build_plan_state ------------------------------------------------------

def test_path_b_fires_tail_when_both_legs_hold():
    ps = _built(vix=27.1, vix_prev=26.4, raw=48.0, raw_prev=49.2)
    blk, rule = _tail(ps)
    assert blk["primary_satisfied"] is False      # no oil/rate leg
    assert blk["alternative_paths"][0]["satisfied"] is True
    assert rule["satisfied"] is True
    assert rule["alternative_paths"][0]["label"] == "経路B"
    assert _contract_failures(ps) == []


def test_path_b_needs_two_closes_over_26():
    ps = _built(vix=27.1, vix_prev=25.64, raw=48.0, raw_prev=49.2)
    _, rule = _tail(ps)
    assert rule["satisfied"] is False
    assert _contract_failures(ps) == []


def test_path_b_needs_breadth_under_50_on_both_points():
    ps = _built(vix=27.1, vix_prev=26.4, raw=48.0, raw_prev=51.0)
    _, rule = _tail(ps)
    assert rule["satisfied"] is False


def test_legs_from_different_routes_do_not_combine():
    """Path A leg 1 holds (VIX 23超2日) and path B leg 2 holds (生値 50 未満).
    Neither route is complete, so Tail must not fire."""
    ps = _built(vix=24.5, vix_prev=24.0, raw=48.0, raw_prev=49.2)
    blk, rule = _tail(ps)
    assert blk["primary_satisfied"] is False
    assert blk["alternative_paths"][0]["satisfied"] is False
    assert rule["satisfied"] is False


def test_path_a_still_fires_on_its_own():
    ps = _built(vix=24.5, vix_prev=24.0, raw=58.8, raw_prev=58.8,
                y10=5.16, y10_prev=5.10)
    blk, rule = _tail(ps)
    assert blk["primary_satisfied"] is True
    assert blk["alternative_paths"][0]["satisfied"] is False
    assert rule["satisfied"] is True


def test_path_b_legs_are_counted_in_coverage():
    ps = _built(vix=25.64, vix_prev=28.18, raw=58.8, raw_prev=61.4)
    cov = ps["analysis"]["trigger_coverage"]
    blk, _ = _tail(ps)
    path_legs = [e for e in blk["trigger_distances"] if e.get("path") == "経路B"]
    assert len(path_legs) == 2
    assert cov["per_scenario"]["tail_risk"]["source"] == \
        cov["per_scenario"]["tail_risk"]["evaluated"]
    assert not cov["unevaluated"].get("tail_risk")
    assert cov["source_audit"]["gaps"] == []


# --- verify_plan -----------------------------------------------------------

def test_verify_rejects_a_route_verdict_that_does_not_follow_its_legs():
    ps = _built(vix=27.1, vix_prev=26.4, raw=48.0, raw_prev=49.2)
    bad = copy.deepcopy(ps)
    blk, _ = _tail(bad)
    blk["alternative_paths"][0]["satisfied"] = False
    assert any(num == 20 for num, _ in _contract_failures(bad))


def test_verify_rejects_a_scenario_that_ignores_its_route():
    ps = _built(vix=27.1, vix_prev=26.4, raw=48.0, raw_prev=49.2)
    bad = copy.deepcopy(ps)
    bad["analysis"]["trigger_coverage"]["scenario_rules"]["tail_risk"]["satisfied"] = False
    assert any(num == 20 for num, _ in _contract_failures(bad))


def test_verify_rejects_dropped_route_legs():
    ps = _built(vix=27.1, vix_prev=26.4, raw=48.0, raw_prev=49.2)
    bad = copy.deepcopy(ps)
    blk, _ = _tail(bad)
    blk["alternative_paths"] = []
    assert any(num == 20 for num, _ in _contract_failures(bad))


# --- source audit ----------------------------------------------------------

def test_audit_flags_a_route_written_as_prose():
    """The form the article first used: a bold route label with no trigger
    label, which the parser cannot read."""
    text = BLOG.read_text(encoding="utf-8")
    start = text.index("**トリガー (経路B")
    end = text.index("**経路B の判定**")
    prose = ("**経路B 株式内部経路 (新設、経路A との OR)**: 同じ判定日に、"
             "VIX **26超を終値2日連続** AND Breadth 生値 **50.0% 未満**。\n\n")
    text = text[:start] + prose + text[end:]
    import tempfile
    path = Path(tempfile.mkdtemp()) / BLOG.name
    path.write_text(text, encoding="utf-8")
    spec = parse_blog(path)
    assert spec.scenarios["tail_risk"].alternative_paths == []
    audit = bps._audit_source_triggers(text, spec.scenarios)
    assert any("OR route" in g["reason"] for g in audit["gaps"]), audit["gaps"]


# --- review follow-ups -------------------------------------------------------

def _variant(old, new):
    """The 11-09 fixture with one piece of the path B label rewritten."""
    import tempfile
    text = BLOG.read_text(encoding="utf-8")
    assert old in text
    text = text.replace(old, new, 1)
    path = Path(tempfile.mkdtemp()) / BLOG.name
    path.write_text(text, encoding="utf-8")
    return text, parse_blog(path)


PATH_B_LABEL = "経路B 株式内部経路、新設、2脚の AND、経路A との OR"


def test_other_or_wordings_are_read_as_a_route():
    """A narrow "との OR" match dropped path B with every gate still green."""
    for wording in ("経路A と OR", "経路A と並列 (OR)", "経路A、または",
                    "経路A or", "OR (経路A と並列)"):
        label = PATH_B_LABEL.replace("経路A との OR", wording)
        text, spec = _variant(PATH_B_LABEL, label)
        tail = spec.scenarios["tail_risk"]
        assert len(tail.alternative_paths) == 1, wording
        assert tail.alternative_paths[0].satisfaction_rule == "all", wording
        assert len(tail.trigger_groups) == 2, wording
        audit = bps._audit_source_triggers(text, spec.scenarios)
        assert audit["gaps"] == [], (wording, audit["gaps"])


def test_route_rule_survives_labels_written_without_spaces():
    """A cross-clause strip swallowed "2脚のAND", so path B fired on one leg."""
    for label in ("経路B、2脚のAND、経路Aとの OR", "経路B、2脚のAND、経路AとOR",
                  "経路B、すべて満たす、経路A との OR",
                  "経路B株式内部経路、2脚の AND、OR (経路Aと並列)"):
        _, spec = _variant(PATH_B_LABEL, label)
        paths = spec.scenarios["tail_risk"].alternative_paths
        assert len(paths) == 1, label
        assert paths[0].satisfaction_rule == "all", label


def test_or_between_a_routes_own_legs_is_not_a_route():
    from trading.layer2.tools.strategy_parser import _is_alt_path_label
    assert not _is_alt_path_label(" (経路A、脚1 または 脚2 のいずれか)")
    assert not _is_alt_path_label(" (経路A インフレ経路、2脚の AND)")
    assert _is_alt_path_label(" (経路B、2脚の AND、経路A との OR)")


def test_a_second_trigger_label_the_parser_ignores_is_flagged():
    """Without any OR wording the label is not a route; the audit must say so
    rather than let its legs vanish."""
    text, spec = _variant(PATH_B_LABEL, "経路B 株式内部経路、新設、2脚の AND")
    assert spec.scenarios["tail_risk"].alternative_paths == []
    audit = bps._audit_source_triggers(text, spec.scenarios)
    assert any("route label" in g["reason"] for g in audit["gaps"]), audit["gaps"]


def test_symmetric_or_labels_keep_path_a_as_the_primary():
    text, spec = _variant("経路A インフレ経路、2脚の AND",
                          "経路A インフレ経路、2脚の AND、経路B との OR")
    tail = spec.scenarios["tail_risk"]
    assert tail.satisfaction_rule == "all"
    assert len(tail.trigger_groups) == 2
    assert [p.label for p in tail.alternative_paths] == ["経路B"]
    assert bps._audit_source_triggers(text, spec.scenarios)["gaps"] == []


def test_duplicate_route_names_stay_separate():
    from trading.layer2.tools.strategy_parser import _parse_alternative_paths
    block = (
        "**トリガー (経路A、2脚の AND)**:\n"
        "- **脚1**: VIX 23超を終値2日連続\n"
        "- **脚2**: WTI $100 終値上抜け\n\n"
        "**トリガー (経路B、2脚の AND、経路A との OR)**:\n"
        "- **脚1**: VIX 26超を終値2日連続\n"
        "- **脚2**: Breadth 生値 50.0% 未満を最新の CSV 2データ点連続\n\n"
        "**トリガー (経路B、経路A との OR)**:\n"
        "- **脚1**: VIX 30超を終値2日連続\n"
        "- **脚2**: WTI $110 終値上抜け\n"
    )
    labels = [p.label for p in _parse_alternative_paths(block)]
    assert len(labels) == 2 and len(set(labels)) == 2, labels


def test_verify_recomputes_the_primary_path_with_an_intraday_route():
    """With route_verdicts present, #20 used to take primary_satisfied on
    trust, so a tampered Tail verdict passed every check."""
    ps = _built(vix=24.5, vix_prev=24.0, raw=58.8, raw_prev=58.8)
    blk, _ = _tail(ps)
    assert blk.get("route_verdicts"), "fixture must exercise the intraday route"
    assert _contract_failures(ps) == []
    bad = copy.deepcopy(ps)
    blk, rule = _tail(bad)
    blk["primary_satisfied"] = True
    blk["scenario_satisfied"] = True
    rule["satisfied"] = True
    assert any(num == 20 for num, _ in _contract_failures(bad))
    bad2 = copy.deepcopy(ps)
    _tail(bad2)[0]["route_verdicts"]["close"] = True
    assert any(num == 20 for num, _ in _contract_failures(bad2))


def test_layer2_prompt_spells_out_each_route():
    from trading.layer2.agent_runner import _route_text
    tail = parse_blog(BLOG).scenarios["tail_risk"]
    primary = _route_text(tail.satisfaction_rule, tail.min_legs,
                          tail.trigger_groups, tail.triggers)
    assert primary.count(" AND ") == 1          # leg 1 AND leg 2
    assert " OR " in primary                    # each leg is an OR inside
    path = tail.alternative_paths[0]
    text = _route_text(path.satisfaction_rule, path.min_legs,
                       path.trigger_groups, path.triggers)
    assert text == ("[脚1 (株価の下げの持続): VIX 26超を終値2日連続] AND "
                    "[脚2 (株式内部の崩れ): Breadth 生値 50.0% 未満を最新の "
                    "CSV 2データ点連続]")
