#!/usr/bin/env python3
"""Verify plan_state.json against source data for consistency.

Runs 15 checks to ensure plan_state values match FMP and breadth source
data, and that internal blog data is self-consistent.

Usage:
    python3 .claude/skills/daily-action-plan/scripts/verify_plan.py \
        --plan-state /tmp/plan_state.json \
        --market-json /tmp/dap_market.json \
        --breadth-json /tmp/dap_breadth.json
"""

import argparse
import json
import os
import sys
from datetime import date
from typing import Optional


class VerificationResult:
    def __init__(self):
        self.checks: list[dict] = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def check(self, num: int, name: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else "FAIL"
        self.checks.append({
            "num": num, "name": name, "status": status, "detail": detail,
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def skip(self, num: int, name: str, reason: str = ""):
        self.checks.append({
            "num": num, "name": name, "status": "SKIP", "detail": reason,
        })
        self.skipped += 1

    def summary(self) -> str:
        lines = ["=" * 60, "Verification Results", "=" * 60, ""]
        for c in self.checks:
            marker = {"PASS": "OK", "FAIL": "NG", "SKIP": "--"}[c["status"]]
            detail = f" ({c['detail']})" if c["detail"] else ""
            lines.append(f"  [{marker}] #{c['num']:02d} {c['name']}{detail}")
        lines.append("")
        lines.append(f"Total: {self.passed} PASS, {self.failed} FAIL, {self.skipped} SKIP")
        verdict = "PASS" if self.failed == 0 else "FAIL"
        lines.append(f"Verdict: {verdict}")
        lines.append("=" * 60)
        return "\n".join(lines)

    @property
    def is_pass(self) -> bool:
        return self.failed == 0


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _exact_match(plan_val, source_val, label: str) -> tuple[bool, str]:
    """Check exact match between plan_state and source values."""
    pv = _safe_float(plan_val)
    sv = _safe_float(source_val)
    if pv is None and sv is None:
        return True, f"{label}: both None"
    if pv is None or sv is None:
        return False, f"{label}: plan={pv}, source={sv}"
    if pv == sv:
        return True, f"{label}: {pv}"
    return False, f"{label}: plan={pv} != source={sv}"


def verify(plan_state: dict, market_json: dict, breadth_json: dict) -> VerificationResult:
    """Run all verification checks."""
    result = VerificationResult()
    is_trading_day = plan_state.get("meta", {}).get("is_trading_day", True)

    quotes = market_json.get("quotes", {})
    treasury = market_json.get("treasury", {})
    market = plan_state.get("market", {})
    breadth = plan_state.get("breadth", {})

    # --- Source data checks (1-10) ---
    if not is_trading_day:
        for i in range(1, 11):
            result.skip(i, "Source data (non-trading day)", "Market closed")
    else:
        # #1: VIX
        ok, detail = _exact_match(
            market.get("vix", {}).get("price"),
            quotes.get("^VIX", {}).get("price"),
            "VIX",
        )
        result.check(1, "VIX price match", ok, detail)

        # #2: S&P 500
        ok, detail = _exact_match(
            market.get("sp500", {}).get("price"),
            quotes.get("^GSPC", {}).get("price"),
            "S&P 500",
        )
        result.check(2, "S&P 500 price match", ok, detail)

        # #3: Nasdaq 100
        ok, detail = _exact_match(
            market.get("nasdaq", {}).get("price"),
            quotes.get("^NDX", {}).get("price"),
            "Nasdaq 100",
        )
        result.check(3, "Nasdaq 100 price match", ok, detail)

        # #4: Dow Jones
        ok, detail = _exact_match(
            market.get("dow", {}).get("price"),
            quotes.get("^DJI", {}).get("price"),
            "Dow Jones",
        )
        result.check(4, "Dow Jones price match", ok, detail)

        # #5: 10Y yield
        ok, detail = _exact_match(
            market.get("us10y", {}).get("value"),
            treasury.get("year10"),
            "10Y Yield",
        )
        result.check(5, "10Y yield match", ok, detail)

        # #6: Gold
        ok, detail = _exact_match(
            market.get("gold", {}).get("price"),
            quotes.get("GCUSD", {}).get("price"),
            "Gold",
        )
        result.check(6, "Gold price match", ok, detail)

        # #7: Oil
        ok, detail = _exact_match(
            market.get("oil", {}).get("price"),
            quotes.get("CLUSD", {}).get("price"),
            "Oil",
        )
        result.check(7, "Oil price match", ok, detail)

        # #8: Breadth 200MA
        ok, detail = _exact_match(
            breadth.get("breadth_200ma"),
            breadth_json.get("breadth_200ma"),
            "Breadth 200MA",
        )
        result.check(8, "Breadth 200MA match", ok, detail)

        # #9: Breadth 8MA
        ok, detail = _exact_match(
            breadth.get("breadth_8ma"),
            breadth_json.get("breadth_8ma"),
            "Breadth 8MA",
        )
        result.check(9, "Breadth 8MA match", ok, detail)

        # #10: Uptrend Ratio
        ok, detail = _exact_match(
            breadth.get("uptrend_ratio"),
            breadth_json.get("uptrend_ratio"),
            "Uptrend Ratio",
        )
        result.check(10, "Uptrend Ratio match", ok, detail)

    # --- Internal consistency checks (11-15) ---
    blog = plan_state.get("blog", {})

    # #11: Blog allocation total
    alloc = blog.get("current_allocation", {})
    alloc_total = sum(float(v) for v in alloc.values())
    ok = abs(alloc_total - 100) < 1
    result.check(11, "Blog allocation total = 100%", ok, f"total={alloc_total:.1f}%")

    # #12: Each scenario allocation total
    scenarios = blog.get("scenarios", {})
    all_ok = True
    details = []
    for name, sc in scenarios.items():
        sc_alloc = sc.get("allocation", {})
        sc_total = sum(float(v) for v in sc_alloc.values())
        if abs(sc_total - 100) >= 2:
            all_ok = False
            details.append(f"{name}={sc_total:.1f}%")
    result.check(
        12, "Scenario allocation totals = 100%", all_ok,
        ", ".join(details) if details else "all OK",
    )

    # #13: Scenario probability total
    prob_total = sum(sc.get("probability", 0) for sc in scenarios.values())
    ok = prob_total == 100
    result.check(13, "Scenario probability total = 100%", ok, f"total={prob_total}%")

    # #14: VIX trigger thresholds
    vix_triggers = blog.get("vix_triggers", {})
    vix_ok = (
        vix_triggers.get("risk_on") == 17
        and vix_triggers.get("caution") == 20
        and vix_triggers.get("stress") == 23
    )
    result.check(
        14, "VIX trigger thresholds (17/20/23)", vix_ok,
        f"risk_on={vix_triggers.get('risk_on')}, "
        f"caution={vix_triggers.get('caution')}, "
        f"stress={vix_triggers.get('stress')}",
    )

    # #15: 10Y trigger thresholds
    yield_triggers = blog.get("yield_triggers", {})
    yield_ok = (
        yield_triggers.get("lower") == 4.11
        and yield_triggers.get("warning") == 4.36
        and yield_triggers.get("red_line") == 4.50
    )
    result.check(
        15, "10Y trigger thresholds (4.11/4.36/4.50)", yield_ok,
        f"lower={yield_triggers.get('lower')}, "
        f"warning={yield_triggers.get('warning')}, "
        f"red_line={yield_triggers.get('red_line')}",
    )

    # --- Trigger metadata checks (16-17) ---
    _REQUIRED_TRIGGER_FIELDS = {
        "time_basis", "required_days", "direction", "is_price_trigger",
        "met_close", "met_current_quote", "met_prev", "progress",
    }

    # #16: Trigger metadata field completeness
    all_complete = True
    field_errors = []
    for sd in plan_state.get("analysis", {}).get("trigger_distances", []):
        for td in sd.get("trigger_distances", []):
            missing = _REQUIRED_TRIGGER_FIELDS - set(td.keys())
            if missing:
                all_complete = False
                field_errors.append(
                    f"{td.get('trigger', '?')[:25]}: missing {missing}"
                )
    result.check(
        16, "Trigger metadata fields present", all_complete,
        "; ".join(field_errors) if field_errors else "all OK",
    )

    # #17: Trigger progress semantic validation
    timing = plan_state.get("meta", {}).get("timing", "")
    is_official = timing == "post-market"
    plan_date_str = plan_state.get("meta", {}).get("date", "")
    semantic_ok = True
    semantic_errors = []

    for sd in plan_state.get("analysis", {}).get("trigger_distances", []):
        for td in sd.get("trigger_distances", []):
            progress = td.get("progress", "")
            tb = td.get("time_basis", "")
            req = td.get("required_days", 1)
            is_price = td.get("is_price_trigger", False)

            # Rule A: weekly_close must NOT say "達成" unless Friday post-market
            if tb == "weekly_close" and "達成" in progress:
                if plan_date_str:
                    d = date.fromisoformat(plan_date_str)
                    if d.weekday() != 4 or not is_official:
                        semantic_ok = False
                        semantic_errors.append(
                            f"weekly '{td['trigger'][:25]}' says '達成' on non-Fri or pre-market"
                        )

            # Rule B: pre-market must NEVER say "達成" for price triggers
            if not is_official and is_price and "達成" in progress:
                semantic_ok = False
                semantic_errors.append(
                    f"pre-market '{td['trigger'][:25]}' says '達成' (closing not confirmed)"
                )

            # Rule C: consecutive-day trigger must show N/M format (post-market)
            if req > 1 and td.get("met_close") is not None and is_official:
                if f"/{req}日" not in progress and "条件充足" not in progress:
                    semantic_ok = False
                    semantic_errors.append(
                        f"consecutive '{td['trigger'][:25]}' missing N/{req}日: '{progress}'"
                    )

            # Rule D: met_close consistency with timing
            if is_price:
                if is_official and td.get("met_close") is None:
                    semantic_ok = False
                    semantic_errors.append(
                        f"post-market '{td['trigger'][:25]}' has met_close=None"
                    )
                if not is_official and td.get("met_close") is not None:
                    semantic_ok = False
                    semantic_errors.append(
                        f"pre-market '{td['trigger'][:25]}' has met_close={td.get('met_close')}"
                    )

    result.check(
        17, "Trigger progress semantic rules", semantic_ok,
        "; ".join(semantic_errors) if semantic_errors else "all OK",
    )

    # --- #18: Trigger coverage (fail-closed) ---
    # Checks 16-17 only inspect the rows that were emitted, so a leg no branch
    # claimed passed silently. On 2026-08-31 that hid 9 of 21 legs, including
    # the article's own headline indicator. Every blog leg must be either
    # evaluated or explicitly declared manual-only.
    coverage = plan_state.get("analysis", {}).get("trigger_coverage") or {}
    manual_only = set(coverage.get("manual_only", []))
    src_total = coverage.get("source_leg_total")
    eval_total = coverage.get("evaluated_leg_total")

    if src_total is None or eval_total is None:
        result.check(
            18, "Trigger coverage (every blog leg evaluated)", False,
            "trigger_coverage missing - rebuild plan_state with the current "
            "build_plan_state.py",
        )
    else:
        problems = []
        for scenario, legs in (coverage.get("unevaluated") or {}).items():
            for leg in legs:
                if leg not in manual_only:
                    problems.append(f"{scenario}: {leg[:45]}")

        # Arithmetic identity, not just an empty list. `unevaluated` can be
        # empty while the totals disagree (a stale or hand-edited plan_state),
        # and checking only the list let 12/21 pass.
        if eval_total + len(manual_only) != src_total:
            problems.append(
                f"count mismatch: evaluated {eval_total} + manual_only "
                f"{len(manual_only)} != source {src_total}"
            )

        # Same identity per scenario, recomputed from trigger_distances rather
        # than trusting the stored block: iterating `per_scenario` alone meant
        # deleting the block skipped the check entirely.
        blocks = plan_state.get("analysis", {}).get("trigger_distances", []) or []
        actual = {
            b.get("scenario"): {
                "source": b.get("source_leg_count"),
                "evaluated": len(b.get("trigger_distances", [])),
            }
            for b in blocks
        }
        per_scenario = coverage.get("per_scenario")
        if per_scenario is None:
            problems.append("per_scenario block missing")
            per_scenario = {}
        elif set(per_scenario) != set(actual):
            problems.append(
                f"per_scenario covers {sorted(per_scenario)} but plan has "
                f"{sorted(actual)}"
            )
        for scenario, counts in actual.items():
            declared = sum(
                1 for leg in (coverage.get("unevaluated") or {}).get(scenario, [])
                if leg in manual_only
            )
            stored = per_scenario.get(scenario, {})
            if stored and (stored.get("source") != counts["source"]
                           or stored.get("evaluated") != counts["evaluated"]):
                problems.append(
                    f"{scenario}: stored {stored.get('evaluated')}/{stored.get('source')} "
                    f"but legs give {counts['evaluated']}/{counts['source']}"
                )
            if counts["evaluated"] + declared != counts["source"]:
                problems.append(
                    f"{scenario}: {counts['evaluated']}+{declared} != {counts['source']}"
                )
        # The totals must also match what the legs actually show.
        if sum(c["evaluated"] for c in actual.values()) != eval_total:
            problems.append(
                f"evaluated_leg_total {eval_total} != "
                f"{sum(c['evaluated'] for c in actual.values())} from legs"
            )

        result.check(
            18, "Trigger coverage (every blog leg evaluated)", not problems,
            f"{eval_total}/{src_total} legs evaluated"
            + (f"; {'; '.join(problems)}" if problems else ""),
        )

    # --- #19: AND-group semantics ---
    # Legs sharing an and_group must ALL be met before the scenario fires.
    # Tagging alone is not enough: without this check a tail-risk scenario whose
    # sibling leg was dropped looked satisfiable by the surviving leg alone.
    and_groups = {}
    for sd in plan_state.get("analysis", {}).get("trigger_distances", []):
        for td in sd.get("trigger_distances", []):
            gid = td.get("and_group")
            if gid:
                and_groups.setdefault(gid, []).append(td)

    stored_groups = {
        g.get("group"): g
        for g in (plan_state.get("analysis", {})
                  .get("trigger_coverage", {}) or {}).get("and_groups", [])
        if isinstance(g, dict)
    }

    and_ok = True
    and_errors = []
    met_key = "met_close" if is_official else "met_current_quote"
    for gid, legs in and_groups.items():
        if len(legs) < 2:
            and_ok = False
            and_errors.append(
                f"{gid}: only {len(legs)} leg tagged - the AND partner was dropped"
            )
            continue
        # Recompute from `condition_met`, which folds in the time basis. Using
        # met_close counts a 終値2日連続 leg as met on day one.
        flags = [leg.get("condition_met") for leg in legs]
        recomputed = all(f is True for f in flags)
        met_count = sum(1 for f in flags if f)
        stored = stored_groups.get(gid)
        if stored is None:
            and_ok = False
            and_errors.append(f"{gid}: no and_groups verdict stored in plan_state")
            continue
        # `satisfied` must be present, not merely falsy-by-absence: deleting the
        # key used to pass whenever the recomputed verdict was also False.
        if "satisfied" not in stored:
            and_ok = False
            and_errors.append(f"{gid}: stored group has no 'satisfied' key")
        elif bool(stored["satisfied"]) != recomputed:
            and_ok = False
            and_errors.append(
                f"{gid}: stored satisfied={stored['satisfied']} but legs give "
                f"{recomputed}"
            )
        if stored.get("leg_count") != len(legs):
            and_ok = False
            and_errors.append(
                f"{gid}: leg_count {stored.get('leg_count')} != {len(legs)} present"
            )
        if stored.get("met_count") != met_count:
            and_ok = False
            and_errors.append(
                f"{gid}: met_count {stored.get('met_count')} != {met_count} from legs"
            )
        # Every leg carries the group verdict so a consumer reading a single row
        # cannot mistake one met leg for a fired scenario. Its VALUE must match
        # too; checking only presence let a leg claim True under a False group.
        for leg in legs:
            if "and_satisfied" not in leg:
                and_ok = False
                and_errors.append(f"{gid}: a leg is missing and_satisfied")
            elif bool(leg["and_satisfied"]) != recomputed:
                and_ok = False
                and_errors.append(
                    f"{gid}: leg and_satisfied={leg['and_satisfied']} != group "
                    f"{recomputed}"
                )

    result.check(
        19, "AND-group verdicts stored and consistent", and_ok,
        "; ".join(and_errors) if and_errors
        else f"{len(and_groups)} group(s) OK"
        + (f" (satisfied: {[g for g, s in stored_groups.items() if s.get('satisfied')]})"
           if any(s.get("satisfied") for s in stored_groups.values()) else ""),
    )

    # --- #20: Scenario satisfaction rules ---
    # The blog says how many legs a scenario needs ("すべて満たす" / "2つ以上" /
    # "いずれか1つ"). Without that rule stored and checked, every scenario reads
    # as a plain OR and a Base case requiring all five legs looks fired on one.
    stored_rules = coverage.get("scenario_rules")
    rule_ok = True
    rule_errors = []
    if stored_rules is None:
        rule_ok = False
        rule_errors.append(
            "scenario_rules missing - rebuild plan_state with the current "
            "build_plan_state.py"
        )
    else:
        blocks = plan_state.get("analysis", {}).get("trigger_distances", []) or []
        if set(stored_rules) != {b.get("scenario") for b in blocks}:
            rule_ok = False
            rule_errors.append(
                f"scenario_rules covers {sorted(stored_rules)} but plan has "
                f"{sorted(b.get('scenario') for b in blocks)}"
            )
        for b in blocks:
            name = b.get("scenario")
            stored = stored_rules.get(name)
            if stored is None:
                rule_ok = False
                rule_errors.append(f"{name}: no rule stored")
                continue
            legs = b.get("trigger_distances", [])
            flags = [leg.get("condition_met") for leg in legs]
            met = sum(1 for f in flags if f)
            rule = stored.get("rule")
            min_legs = stored.get("min_legs", 1)
            if rule == "all":
                expected = bool(legs) and all(f is True for f in flags)
            elif rule == "at_least":
                expected = met >= min_legs
            elif rule == "any":
                expected = met >= 1
            else:
                rule_ok = False
                rule_errors.append(f"{name}: unknown rule {rule!r}")
                continue
            if "satisfied" not in stored:
                rule_ok = False
                rule_errors.append(f"{name}: no 'satisfied' key")
            elif bool(stored["satisfied"]) != expected:
                rule_ok = False
                rule_errors.append(
                    f"{name}: stored satisfied={stored['satisfied']} but "
                    f"rule={rule} min={min_legs} met={met}/{len(legs)} gives {expected}"
                )
            if stored.get("met_leg_count") != met:
                rule_ok = False
                rule_errors.append(
                    f"{name}: met_leg_count {stored.get('met_leg_count')} != {met}"
                )
            if stored.get("leg_count") != len(legs):
                rule_ok = False
                rule_errors.append(
                    f"{name}: leg_count {stored.get('leg_count')} != {len(legs)}"
                )

    fired = (
        [n for n, s in (stored_rules or {}).items() if s.get("satisfied")]
        if stored_rules else []
    )
    result.check(
        20, "Scenario satisfaction rules stored and consistent", rule_ok,
        "; ".join(rule_errors) if rule_errors
        else f"{len(stored_rules or {})} scenario(s) OK"
             + (f"; fired: {fired}" if fired else "; none fired"),
    )

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Verify plan_state.json against source data"
    )
    parser.add_argument("--plan-state", required=True, help="Path to plan_state.json")
    parser.add_argument("--market-json", required=True, help="Path to FMP market JSON")
    parser.add_argument("--breadth-json", required=True, help="Path to breadth CSV JSON")

    args = parser.parse_args()

    files = {
        "plan_state": args.plan_state,
        "market": args.market_json,
        "breadth": args.breadth_json,
    }
    for label, path in files.items():
        if not os.path.isfile(path):
            print(f"ERROR: {label} JSON not found: {path}", file=sys.stderr)
            sys.exit(1)

    loaded = {}
    for label, path in files.items():
        try:
            with open(path, encoding="utf-8") as f:
                loaded[label] = json.load(f)
        except json.JSONDecodeError as e:
            with open(path, encoding="utf-8") as f:
                preview = f.read(200)
            print(
                f"ERROR: {path} is not valid JSON: {e}\n"
                f"First 200 chars: {preview!r}",
                file=sys.stderr,
            )
            sys.exit(1)

    plan_state = loaded["plan_state"]
    market_json = loaded["market"]
    breadth_json = loaded["breadth"]

    result = verify(plan_state, market_json, breadth_json)
    print(result.summary())

    sys.exit(0 if result.is_pass else 1)


if __name__ == "__main__":
    main()
