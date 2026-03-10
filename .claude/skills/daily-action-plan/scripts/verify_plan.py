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
