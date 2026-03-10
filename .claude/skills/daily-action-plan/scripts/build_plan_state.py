#!/usr/bin/env python3
"""Build plan_state.json from market data, breadth data, and latest blog.

Integrates FMP market JSON, breadth CSV JSON, and parsed blog strategy
into a single structured JSON for the daily action plan skill.

Usage:
    # Check-only mode (holiday check)
    python3 .claude/skills/daily-action-plan/scripts/build_plan_state.py --check-only

    # Full build
    python3 .claude/skills/daily-action-plan/scripts/build_plan_state.py \
        --timing post-market \
        --market-json /tmp/dap_market.json \
        --breadth-json /tmp/dap_breadth.json \
        --output /tmp/plan_state.json
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from typing import Optional

# Resolve project root from script location
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "..", "..", ".."))


def _ensure_venv():
    """Re-exec under project .venv if running under system Python."""
    if sys.prefix != sys.base_prefix:
        return  # Already in a venv
    venv_python = os.path.join(_PROJECT_ROOT, ".venv", "bin", "python")
    if os.path.isfile(venv_python):
        os.execv(venv_python, [venv_python] + sys.argv)


_ensure_venv()

sys.path.insert(0, _PROJECT_ROOT)

from trading.core.holidays import USMarketCalendar
from trading.layer2.tools.strategy_parser import find_latest_blog, parse_blog

# --- Monty Style Thresholds ---

VIX_THRESHOLDS = [
    (40.0, "Extreme"),
    (26.0, "Panic"),
    (23.0, "Stress"),
    (20.0, "Caution"),
    (17.0, "Risk-On"),
    (0.0, "Low Vol"),
]

YIELD_THRESHOLDS = [
    (4.60, "Extreme"),
    (4.50, "Red Line"),
    (4.36, "Warning"),
    (4.11, "Lower Bound"),
    (0.0, "Below Range"),
]

BREADTH_200MA_THRESHOLDS = [
    (60.0, "healthy"),
    (50.0, "narrow_rally"),
    (40.0, "caution"),
    (0.0, "fragile"),
]

BREADTH_8MA_THRESHOLDS = [
    (73.0, "overbought"),
    (60.0, "healthy_bullish"),
    (40.0, "neutral"),
    (23.0, "bearish"),
    (0.0, "oversold"),
]

UPTREND_THRESHOLDS = [
    (40.0, "strong_bullish"),
    (25.0, "neutral"),
    (15.0, "weak"),
    (0.0, "crisis"),
]

# ETF category mapping
ETF_CATEGORIES = {
    "SPY": "core", "QQQ": "core", "DIA": "core", "IWM": "core",
    "XLV": "defensive", "XLP": "defensive",
    "GLD": "theme", "XLE": "theme", "URA": "theme", "TLT": "theme", "COPX": "theme",
    "BIL": "cash", "SH": "hedge", "SDS": "hedge",
}

# FMP symbol to plan_state key mapping
FMP_MARKET_MAP = {
    "^VIX": ("vix", None),
    "^GSPC": ("sp500", None),
    "^NDX": ("nasdaq", None),
    "^DJI": ("dow", None),
    "GCUSD": ("gold", None),
    "CLUSD": ("oil", None),
    "HGUSD": ("copper", None),
    "NGUSD": ("natgas", None),
}

FMP_ETF_SYMBOLS = [
    "SPY", "QQQ", "DIA", "GLD", "XLE", "XLV", "XLP", "BIL", "TLT", "URA",
]


def _classify(value: float, thresholds: list) -> str:
    """Classify a value against descending thresholds."""
    for threshold, label in thresholds:
        if value >= threshold:
            return label
    return thresholds[-1][1]


def _safe_float(val) -> Optional[float]:
    """Convert to float or None without rounding."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def check_market_status(d: date = None) -> str:
    """Check if market is open on given date."""
    if d is None:
        d = date.today()
    cal = USMarketCalendar()
    if d.weekday() >= 5:
        return "CLOSED"
    if cal.is_market_holiday(d):
        return "CLOSED"
    if cal.is_early_close(d):
        return "EARLY_CLOSE"
    return "OPEN"


def _extract_section(text: str, keyword: str) -> Optional[str]:
    """Extract a markdown section by keyword."""
    pattern = re.compile(
        r"^(#{1,4})\s+.*" + re.escape(keyword) + r".*$",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        return None
    level = len(m.group(1))
    start = m.end()
    next_heading = re.compile(r"^#{1," + str(level) + r"}\s+", re.MULTILINE)
    end_match = next_heading.search(text, start)
    end = end_match.start() if end_match else len(text)
    return text[start:end]


def _parse_events_detail(text: str) -> list[dict]:
    """Parse events from the 重要イベント table."""
    section = _extract_section(text, "重要イベント")
    if not section:
        return []
    events = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        # Skip separator rows and header row
        if all(c.startswith("-") or c.startswith(":") for c in cells):
            continue
        if cells[0] in ("日付", "Date"):
            continue
        date_cell = re.sub(r"\*+", "", cells[0]).strip()
        event_name = re.sub(r"\*+", "", cells[1]).strip()
        impact = re.sub(r"\*+", "", cells[2]).strip()
        watch = re.sub(r"\*+", "", cells[3]).strip() if len(cells) > 3 else ""
        # Detect "毎日" (daily) events
        is_daily = "毎日" in date_cell
        events.append({
            "date": date_cell,
            "event": event_name,
            "impact": impact,
            "watch_point": watch,
            "is_daily": is_daily,
        })
    return events


def _parse_checklist(text: str, keyword: str) -> list[str]:
    """Extract checklist items from a section."""
    section = _extract_section(text, keyword)
    if not section:
        return []
    items = []
    for line in section.splitlines():
        line = line.strip()
        m = re.match(r"-\s*\[[ x]\]\s*(.*)", line)
        if m:
            items.append(re.sub(r"\*+", "", m.group(1)).strip())
    return items


def _get_todays_events(events: list[dict], today: date) -> list[dict]:
    """Filter events for today, including daily events."""
    result = []
    today_str = f"{today.month}/{today.day}"
    for ev in events:
        if ev.get("is_daily"):
            result.append(ev)
            continue
        # Token-boundary match: "3/1" must not match "3/10(火)"
        date_field = ev.get("date", "")
        if re.search(rf"(?<!\d){re.escape(today_str)}(?!\d)", date_field):
            result.append(ev)
    return result


def _parse_trigger_metadata(trigger: str) -> dict:
    """Parse trigger text to extract time_basis, required_days, direction."""
    meta = {
        "time_basis": "daily_close",
        "required_days": 1,
        "direction": None,
        "is_price_trigger": True,
    }

    # Weekly close detection
    if "週足" in trigger or ("週" in trigger and "終値" in trigger):
        meta["time_basis"] = "weekly_close"
    # Intraday detection
    elif "ザラ場" in trigger or "日中" in trigger:
        meta["time_basis"] = "intraday"
    # Standard daily close (default)
    elif "終値" in trigger:
        meta["time_basis"] = "daily_close"

    # Consecutive days: "2日連続", "3日連続"
    days_m = re.search(r"(\d+)日連続", trigger)
    if days_m:
        meta["required_days"] = int(days_m.group(1))

    # Direction: below / above
    if re.search(r"(下回|以下|割れ)", trigger):
        meta["direction"] = "below"
    elif re.search(r"(超え|超$|超（|以上|超\s)", trigger):
        meta["direction"] = "above"
    elif "維持" in trigger:
        meta["direction"] = "above"

    # Non-price triggers
    if any(kw in trigger for kw in ("停戦", "報道", "合意", "再開")):
        meta["is_price_trigger"] = False

    return meta


def _check_condition_met(value: float, target: float, direction: str) -> bool:
    """Check if value meets condition relative to target."""
    if direction == "below":
        return value < target
    elif direction == "above":
        return value >= target
    return False


# Max days confirmable from prev_close alone (today + prev day)
_MAX_CONFIRMED_DAYS = 2


def _build_progress_string(
    entry: dict, meta: dict, today: date, is_official: bool,
) -> str:
    """Generate human-readable progress string for trigger evaluation.

    Args:
        is_official: True when timing is post-market (closing price confirmed).
                     False for pre-market (price is provisional).
    """
    if not meta["is_price_trigger"]:
        return "未確認"

    met_close = entry.get("met_close")
    met_quote = entry.get("met_current_quote")
    met_prev = entry.get("met_prev")
    required = meta["required_days"]
    time_basis = meta["time_basis"]

    # Weekly close: only confirmed on Friday post-market
    if time_basis == "weekly_close":
        if today.weekday() == 4 and is_official:  # Friday post-market
            return "達成" if met_close else "未達（週足確定）"
        else:
            current_met = met_close if is_official else met_quote
            status = "水準上" if current_met else "水準下"
            return f"推移中（{status}、金曜引け後に確定）"

    # Pre-market: closing price not yet confirmed
    if not is_official:
        if required > 1:
            if met_prev:
                return "前日条件充足（本日終値待ち）"
            else:
                return f"0/{required}日（前日未達）"
        else:
            return "本日終値待ち"

    # Post-market (is_official=True) below

    # Consecutive-day conditions
    if required > 1:
        if met_close and met_prev:
            days_met = min(2, _MAX_CONFIRMED_DAYS)
            if days_met >= required:
                return f"{required}/{required}日達成"
            return f"{days_met}/{required}日達成（{_MAX_CONFIRMED_DAYS}日分のみ確認可）"
        elif met_close:
            return f"1/{required}日達成（本日条件充足）"
        elif met_prev:
            return f"0/{required}日（前日充足→本日リセット）"
        else:
            return f"0/{required}日（未達）"

    # Single-day conditions
    if required == 1:
        return "達成" if met_close else "未達"

    return ""


def _enrich_trigger_entry(
    entry: dict, trigger: str, market: dict,
    indicator_key: str, timing: str, today: date,
) -> None:
    """Add metadata, condition-met flags, and progress to a trigger entry."""
    meta = _parse_trigger_metadata(trigger)
    entry["time_basis"] = meta["time_basis"]
    entry["required_days"] = meta["required_days"]
    entry["direction"] = meta["direction"]
    entry["is_price_trigger"] = meta["is_price_trigger"]

    is_official = timing == "post-market"
    target = entry["target"]
    current_val = entry["current"]

    if meta["is_price_trigger"] and meta["direction"]:
        prev_val = market.get(indicator_key, {}).get("prev_close")
        entry["met_prev"] = (
            _check_condition_met(prev_val, target, meta["direction"])
            if prev_val is not None else None
        )
        if is_official:
            entry["met_close"] = _check_condition_met(
                current_val, target, meta["direction"],
            )
            entry["met_current_quote"] = None
        else:
            entry["met_close"] = None
            entry["met_current_quote"] = _check_condition_met(
                current_val, target, meta["direction"],
            )
    else:
        entry["met_close"] = None
        entry["met_current_quote"] = None
        entry["met_prev"] = None

    entry["progress"] = _build_progress_string(entry, meta, today, is_official)


def _compute_trigger_distance(
    scenarios: dict, market: dict, breadth: dict,
    timing: str, today: date,
) -> list[dict]:
    """Compute distance from current values to scenario triggers."""
    distances = []
    vix = market.get("vix", {}).get("price")
    sp500 = market.get("sp500", {}).get("price")
    oil = market.get("oil", {}).get("price")

    for name, scenario in scenarios.items():
        triggers = scenario.get("triggers", [])
        trigger_distances = []
        for trigger in triggers:
            # VIX distance
            if vix and "VIX" in trigger.upper():
                vix_m = re.search(r"(\d+(?:\.\d+)?)", trigger)
                if vix_m:
                    target = float(vix_m.group(1))
                    diff = vix - target
                    entry = {
                        "trigger": trigger,
                        "indicator": "VIX",
                        "current": vix,
                        "target": target,
                        "diff": round(diff, 2),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "vix", timing, today,
                    )
                    trigger_distances.append(entry)
            # S&P distance
            elif sp500 and ("S&P" in trigger or "6," in trigger or "7," in trigger):
                sp_m = re.search(r"([\d,]+(?:\.\d+)?)", trigger)
                if sp_m:
                    target = float(sp_m.group(1).replace(",", ""))
                    if target > 1000:  # filter out small numbers
                        diff = sp500 - target
                        entry = {
                            "trigger": trigger,
                            "indicator": "S&P 500",
                            "current": sp500,
                            "target": target,
                            "diff": round(diff, 2),
                        }
                        _enrich_trigger_entry(
                            entry, trigger, market, "sp500", timing, today,
                        )
                        trigger_distances.append(entry)
            # Oil distance
            elif oil and ("原油" in trigger or "$" in trigger):
                oil_m = re.search(r"\$(\d+(?:\.\d+)?)", trigger)
                if oil_m:
                    target = float(oil_m.group(1))
                    diff = oil - target
                    entry = {
                        "trigger": trigger,
                        "indicator": "WTI Oil",
                        "current": oil,
                        "target": target,
                        "diff": round(diff, 2),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "oil", timing, today,
                    )
                    trigger_distances.append(entry)

        distances.append({
            "scenario": name,
            "probability": scenario.get("probability"),
            "trigger_distances": trigger_distances,
        })

    return distances


def build_plan_state(
    timing: str,
    market_json: dict,
    breadth_json: dict,
    blog_path: str,
    today: date = None,
) -> dict:
    """Build the plan_state structure."""
    if today is None:
        today = date.today()

    spec = parse_blog(blog_path)
    blog_text = open(blog_path, encoding="utf-8").read()

    # Market status
    status = check_market_status(today)

    # --- Market data (no rounding - transfer as-is from FMP JSON) ---
    market = {}
    quotes = market_json.get("quotes", {})
    treasury = market_json.get("treasury", {})

    for fmp_sym, (key, _) in FMP_MARKET_MAP.items():
        q = quotes.get(fmp_sym, {})
        price = _safe_float(q.get("price"))
        change = _safe_float(q.get("change"))
        change_pct = _safe_float(q.get("changesPercentage"))
        prev_close = _safe_float(q.get("previousClose"))
        day_high = _safe_float(q.get("dayHigh"))
        day_low = _safe_float(q.get("dayLow"))

        eval_str = ""
        if key == "vix" and price is not None:
            eval_str = _classify(price, VIX_THRESHOLDS)

        market[key] = {
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "prev_close": prev_close,
            "day_high": day_high,
            "day_low": day_low,
            "eval": eval_str,
        }

    # Treasury 10Y (no rounding)
    us10y = _safe_float(treasury.get("year10"))
    yield_eval = _classify(us10y, YIELD_THRESHOLDS) if us10y else ""
    market["us10y"] = {
        "value": us10y,
        "eval": yield_eval,
    }

    # ETF prices (no rounding)
    etfs = {}
    for sym in FMP_ETF_SYMBOLS:
        q = quotes.get(sym, {})
        etfs[sym] = {
            "price": _safe_float(q.get("price")),
            "change": _safe_float(q.get("change")),
            "change_pct": _safe_float(q.get("changesPercentage")),
        }

    # --- Breadth data (no rounding - transfer as-is from CSV JSON) ---
    breadth = {
        "breadth_date": breadth_json.get("breadth_date", ""),
        "breadth_200ma": _safe_float(breadth_json.get("breadth_200ma")),
        "breadth_200ma_class": breadth_json.get("breadth_200ma_class", ""),
        "breadth_8ma": _safe_float(breadth_json.get("breadth_8ma")),
        "breadth_8ma_class": breadth_json.get("breadth_8ma_class", ""),
        "dead_cross": breadth_json.get("dead_cross", False),
        "cross_diff": _safe_float(breadth_json.get("cross_diff")),
        "uptrend_date": breadth_json.get("uptrend_date", ""),
        "uptrend_ratio": _safe_float(breadth_json.get("uptrend_ratio")),
        "uptrend_color": breadth_json.get("uptrend_color", ""),
        "uptrend_class": breadth_json.get("uptrend_class", ""),
        "uptrend_slope": _safe_float(breadth_json.get("uptrend_slope")),
        "uptrend_trend": breadth_json.get("uptrend_trend", ""),
    }

    # --- Blog data ---
    blog_allocation = spec.current_allocation
    allocation_categories = {}
    for etf, pct in blog_allocation.items():
        cat = ETF_CATEGORIES.get(etf, "other")
        if cat not in allocation_categories:
            allocation_categories[cat] = {}
        allocation_categories[cat][etf] = pct

    scenarios = {}
    for name, sc in spec.scenarios.items():
        scenarios[name] = {
            "probability": sc.probability,
            "triggers": sc.triggers,
            "allocation": sc.allocation,
        }

    # Trading levels
    trading_levels = {}
    for name, tl in spec.trading_levels.items():
        trading_levels[name] = {
            "buy_level": tl.buy_level,
            "sell_level": tl.sell_level,
            "stop_loss": tl.stop_loss,
        }

    # Events
    events_detail = _parse_events_detail(blog_text)
    todays_events = _get_todays_events(events_detail, today)

    # Checklists
    morning_checklist = _parse_checklist(blog_text, "朝チェック")
    evening_checklist = _parse_checklist(blog_text, "夜チェック")

    # Trigger distances
    trigger_distances = _compute_trigger_distance(
        scenarios, market, breadth, timing, today,
    )

    # Pre-market note
    is_official_close = timing == "post-market"
    data_note = "" if is_official_close else (
        "Pre-market: extended-hours quote; previous close used for comparison"
    )

    plan_state = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "timing": timing,
            "date": today.isoformat(),
            "is_trading_day": status != "CLOSED",
            "market_status": status,
            "is_official_close": is_official_close,
            "data_note": data_note,
            "blog_date": spec.blog_date,
            "blog_path": str(blog_path),
        },
        "market": market,
        "etfs": etfs,
        "breadth": breadth,
        "blog": {
            "phase": spec.phase,
            "current_allocation": blog_allocation,
            "allocation_categories": allocation_categories,
            "scenarios": scenarios,
            "trading_levels": trading_levels,
            "vix_triggers": spec.vix_triggers,
            "yield_triggers": spec.yield_triggers,
            "breadth_200ma": spec.breadth_200ma,
            "uptrend_ratio": spec.uptrend_ratio,
            "bubble_score": spec.bubble_score,
        },
        "events": {
            "all_events": events_detail,
            "todays_events": todays_events,
        },
        "checklists": {
            "morning": morning_checklist,
            "evening": evening_checklist,
        },
        "analysis": {
            "trigger_distances": trigger_distances,
        },
    }

    return plan_state


def main():
    parser = argparse.ArgumentParser(
        description="Build plan_state.json for daily action plan"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check market status and exit",
    )
    parser.add_argument(
        "--timing",
        choices=["pre-market", "post-market"],
        default="post-market",
        help="Timing context",
    )
    parser.add_argument("--market-json", help="Path to FMP market JSON")
    parser.add_argument("--breadth-json", help="Path to breadth CSV JSON")
    parser.add_argument("--output", help="Output path for plan_state.json")
    parser.add_argument(
        "--date",
        help="Override date (YYYY-MM-DD format, for testing)",
    )

    args = parser.parse_args()

    # Parse date override
    today = date.today()
    if args.date:
        today = date.fromisoformat(args.date)

    # Check-only mode
    if args.check_only:
        status = check_market_status(today)
        print(status)
        sys.exit(0)  # Always 0; SKILL.md reads stdout for branching

    # Validate required args
    if not args.market_json or not args.breadth_json:
        print(
            "ERROR: --market-json and --breadth-json required for full build",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load input JSONs
    for label, path in [("market", args.market_json), ("breadth", args.breadth_json)]:
        if not os.path.isfile(path):
            print(f"ERROR: {label} JSON not found: {path}", file=sys.stderr)
            sys.exit(1)

    try:
        with open(args.market_json, encoding="utf-8") as f:
            market_json = json.load(f)
    except json.JSONDecodeError as e:
        with open(args.market_json, encoding="utf-8") as f:
            preview = f.read(200)
        print(
            f"ERROR: {args.market_json} is not valid JSON: {e}\n"
            f"First 200 chars: {preview!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with open(args.breadth_json, encoding="utf-8") as f:
            breadth_json = json.load(f)
    except json.JSONDecodeError as e:
        with open(args.breadth_json, encoding="utf-8") as f:
            preview = f.read(200)
        print(
            f"ERROR: {args.breadth_json} is not valid JSON: {e}\n"
            f"First 200 chars: {preview!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Find latest blog
    blogs_dir = os.path.join(_PROJECT_ROOT, "blogs")
    blog_path = find_latest_blog(blogs_dir)
    if not blog_path:
        print("ERROR: No blog found in blogs/", file=sys.stderr)
        sys.exit(1)

    # Build plan state
    plan_state = build_plan_state(
        timing=args.timing,
        market_json=market_json,
        breadth_json=breadth_json,
        blog_path=str(blog_path),
        today=today,
    )

    # Output
    output_json = json.dumps(plan_state, indent=2, ensure_ascii=False, default=str)

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"Plan state written to {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
