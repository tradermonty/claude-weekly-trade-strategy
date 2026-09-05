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
    "^RUT": ("russell", None),
    "GCUSD": ("gold", None),
    "CLUSD": ("oil", None),
    "HGUSD": ("copper", None),
    "NGUSD": ("natgas", None),
}

FMP_ETF_SYMBOLS = [
    "SPY", "QQQ", "DIA", "GLD", "XLE", "XLV", "XLP", "BIL", "TLT", "URA", "IWM",
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


def _extract_section(
    text: str, keyword: str, exclude: tuple[str, ...] = (),
) -> Optional[str]:
    """Extract a markdown section by keyword.

    `exclude` skips headings that also contain one of the given substrings, so
    that a lookup for "朝チェック" does not latch onto "夜・早朝チェック".
    """
    pattern = re.compile(
        r"^(#{1,4})\s+.*" + re.escape(keyword) + r".*$",
        re.MULTILINE,
    )
    m = None
    for candidate in pattern.finditer(text):
        if any(word in candidate.group(0) for word in exclude):
            continue
        m = candidate
        break
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
    # Column positions are read from the header rather than assumed, because
    # the table has both a 4-column form (日付 | イベント | Impact | 監視ポイント)
    # and a 5-column JST/ET form (日付 (JST) | 日付 (ET) | イベント | ...).
    # Assuming 4 columns on the 5-column table shifts every field left by one,
    # so the event name lands in "impact" and the impact lands in "watch_point".
    cols = {"date": 0, "date_et": None, "event": 1, "impact": 2, "watch": 3}
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        # Skip separator rows
        if all(c.startswith("-") or c.startswith(":") for c in cells):
            continue
        # Header row: re-derive the column map, then skip. Matches "日付 (JST)"
        # as well as a bare "日付".
        if re.match(r"^\**\s*(日付|Date)\b", cells[0]):
            cols = _map_event_columns(cells)
            continue

        def _cell(key: str) -> str:
            idx = cols.get(key)
            if idx is None or idx >= len(cells):
                return ""
            return re.sub(r"\*+", "", cells[idx]).strip()

        date_cell = _cell("date")
        # Detect "毎日" (daily) events
        is_daily = "毎日" in date_cell
        events.append({
            "date": date_cell,
            "date_et": _cell("date_et"),
            "event": _cell("event"),
            "impact": _cell("impact"),
            "watch_point": _cell("watch"),
            "is_daily": is_daily,
        })
    return events


def _map_event_columns(header_cells: list[str]) -> dict:
    """Derive event-table column indices from its header row."""
    cols = {"date": 0, "date_et": None, "event": None, "impact": None, "watch": None}
    for i, raw in enumerate(header_cells):
        h = re.sub(r"\*+", "", raw).strip()
        if cols["date_et"] is None and ("ET" in h and ("日付" in h or "Date" in h)):
            cols["date_et"] = i
        elif "イベント" in h or "Event" in h:
            cols["event"] = i
        elif "Impact" in h or "影響" in h or "重要度" in h:
            cols["impact"] = i
        elif "監視" in h or "Watch" in h or "ポイント" in h:
            cols["watch"] = i
    # Fall back to legacy positional layout for any column the header lacked.
    for key, default in (("event", 1), ("impact", 2), ("watch", 3)):
        if cols[key] is None:
            cols[key] = default
    return cols


def _parse_checklist(
    text: str, keywords: tuple[str, ...], exclude: tuple[str, ...] = (),
) -> list[str]:
    """Extract checklist items from the first section matching any keyword."""
    section = None
    for keyword in keywords:
        section = _extract_section(text, keyword, exclude=exclude)
        if section:
            break
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


# Explicit weekly-bar confirmation wording. "週足" alone counts (a weekly bar
# reference), but "N週線" (a weekly moving-average *level*) does not.
_WEEKLY_CLOSE_RE = re.compile(
    r"週足(?!線)|週次終値|週末終値|週引け|週足引け|金曜終値|金曜引け"
)

# AND-joined compound triggers ("A — かつ — B", "A かつ B"). Each leg carries
# its own indicator, level, direction and day-count, so they must be split
# before numeric pairing; otherwise the first matching branch wins the whole
# string and pairs a foreign number (e.g. the VIX branch taking the "7" of
# "SPX 7,325" as target 7.0, leaving the real tail condition unevaluated).
_AND_SEPARATOR = re.compile(r"\s*[—–―-]\s*かつ\s*[—–―-]\s*|\s*かつ\s*")


def _parse_trigger_metadata(trigger: str) -> dict:
    """Parse trigger text to extract time_basis, required_days, direction."""
    meta = {
        "time_basis": "daily_close",
        "required_days": 1,
        "direction": None,
        "is_price_trigger": True,
    }

    # Weekly close detection. Must be an explicit weekly-bar confirmation:
    # a bare "週" + "終値" test also fires on price *levels* that merely
    # mention weeks ("SPX 7,325 の20週線帯を終値割れ") and on week-relative
    # labels ("10年債 4.708% (今週高値) 終値上抜け"), both of which the blog
    # confirms on a DAILY close. Misclassifying them as weekly defers a
    # trigger that has already fired to "金曜引け後に確定".
    if _WEEKLY_CLOSE_RE.search(trigger):
        meta["time_basis"] = "weekly_close"
    # Intraday detection
    elif "ザラ場" in trigger or "日中" in trigger:
        meta["time_basis"] = "intraday"
    # Standard daily close (default)
    elif "終値" in trigger:
        meta["time_basis"] = "daily_close"

    # Consecutive observations: "2日連続", "3日連続", and the CSV form the
    # 2026-09-07 article used, "64.0% を CSV 2データ点連続で下回る". Reading only
    # 日連続 left the CSV form at required_days=1, so a single reading below the
    # level counted as met.
    days_m = re.search(r"(\d+)\s*(?:日|データ点|データポイント|本|回)連続", trigger)
    if days_m:
        meta["required_days"] = int(days_m.group(1))

    # Direction: below / above / range
    # Negated break ("26,233 を割らず", "4.60% を下回らず") means "stay above".
    # Must precede the plain below/above checks: "下回らず" contains "下回".
    if re.search(
        r"(割らず|割らない|割り込まず|割り込まない|割れず|下回らず|下回らない|下抜けず|下抜けない)",
        trigger,
    ):
        meta["direction"] = "above"
    elif re.search(r"(超えず|超えない|上回らず|上回らない|上抜けず|上抜けない)", trigger):
        meta["direction"] = "below"
    elif (
        re.search(r"(下回|以下|割れ|未満|下抜け|下放れ)", trigger)
        or re.search(r"<\s*\d", trigger)
    ):
        meta["direction"] = "below"
    elif (
        re.search(r"(超え|超[を（\s]|超$|以上|上抜け|上回|上放れ|奪還|回復)", trigger)
        # "<number>超" followed by any word: 急騰/急伸/定着 etc. ("$85超急騰")
        or re.search(r"\d\s*%?\s*超", trigger)
        # "<number>+" suffix notation ("VIX 26+", "WTI $130+")
        or re.search(r"\d\s*%?\s*\+", trigger)
        or re.search(r">\s*\d", trigger)
    ):
        meta["direction"] = "above"
    elif "維持" in trigger:
        meta["direction"] = "above"
    elif "レンジ" in trigger or re.search(r"[\d,]+\s*%?\s*[-–〜~]\s*\$?[\d,]+", trigger):
        meta["direction"] = "range"
        # Allow commas as thousands separators (e.g. "7,018-7,300"), a percent
        # sign on the low bound ("4.501%〜4.806%"), and 〜/~ as the separator.
        range_m = re.search(
            r"\$?([\d,]+(?:\.\d+)?)\s*%?\s*[-–〜~]\s*\$?([\d,]+(?:\.\d+)?)", trigger,
        )
        if range_m:
            meta["range_low"] = float(range_m.group(1).replace(",", ""))
            meta["range_high"] = float(range_m.group(2).replace(",", ""))

    # Fallback: bare "$X 終値 (N日連続)" without explicit direction marker
    # → assume "above" (continuation pattern: stronger level on same side)
    if (
        meta["direction"] is None
        and "終値" in trigger
        and re.search(r"\$\d", trigger)
    ):
        meta["direction"] = "above"

    # Non-price triggers
    if any(kw in trigger for kw in ("停戦", "報道", "合意", "再開")):
        meta["is_price_trigger"] = False

    return meta


def _check_condition_met(
    value: float, target: float, direction: str,
    range_high: float = None, range_low: float = None,
) -> bool:
    """Check if value meets condition relative to target.

    A range condition takes its bounds from `range_low`/`range_high`, not from
    `target`. `target` holds the single level extracted for the trigger, which
    for "4.60〜4.708%" is the upper bound — using it as the lower bound made
    every in-range value evaluate as unmet.
    """
    if direction == "below":
        return value < target
    elif direction == "above":
        return value >= target
    elif direction == "range" and range_high is not None:
        low = range_low if range_low is not None else target
        return low <= value <= range_high
    return False


# Max days confirmable from prev_close alone (today + prev day)
_MAX_CONFIRMED_DAYS = 2

# Instrument names that, when present, mean a "$" in the leg belongs to an ETF
# conversion note rather than to an oil level.
_INSTRUMENT_NAMES = (
    "SPX", "S&P", "NDX", "NASDAQ", "DOW", "DJI", "RUSSELL", "RUT", "IWM",
    "SPY", "QQQ", "DIA", "GLD", "TLT", "VIX", "UPTREND", "BREADTH",
)


def _first_index_level(trigger: str, minimum: float = 1000.0) -> Optional[float]:
    """First number in `trigger` at index scale.

    Taking only the first number found drops legs whose text begins with a
    non-level figure — "SPX EMA20 帯 7,398〜7,407 を終値で割れ" yields 20, which
    fails the scale filter, and the whole leg then goes unevaluated. Scanning
    for the first number that is actually at index scale keeps such legs.
    """
    for m in re.finditer(r"([\d,]+(?:\.\d+)?)", trigger):
        try:
            value = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if value >= minimum:
            return value
    return None


def _names_other_instrument(trigger: str) -> bool:
    """True when the leg names a non-oil instrument.

    Blog legs carry ETF conversions ("(IWM ≈ $286.86)"), so a bare "$" is not
    evidence of an oil level. Without this guard the oil branch claimed a
    Russell leg and reported a phantom "WTI 883.0" as met every day.
    """
    upper = trigger.upper()
    if any(name in upper for name in _INSTRUMENT_NAMES):
        return True
    return any(kw in trigger for kw in ("年債", "年金利", "銅", "ラッセル", "上昇銘柄比率"))


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
        if met_prev is None:
            # No prior observation on file (CSV series carry no prev_close),
            # so consecutiveness cannot be judged either way.
            return f"0/{required}（前データ点なし・判定不可）"
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
        range_high = meta.get("range_high")
        range_low = meta.get("range_low")
        prev_val = market.get(indicator_key, {}).get("prev_close")
        entry["met_prev"] = (
            _check_condition_met(
                prev_val, target, meta["direction"], range_high, range_low,
            )
            if prev_val is not None else None
        )
        if is_official:
            entry["met_close"] = _check_condition_met(
                current_val, target, meta["direction"], range_high, range_low,
            )
            entry["met_current_quote"] = None
        else:
            entry["met_close"] = None
            entry["met_current_quote"] = _check_condition_met(
                current_val, target, meta["direction"], range_high, range_low,
            )
    else:
        entry["met_close"] = None
        entry["met_current_quote"] = None
        entry["met_prev"] = None

    entry["progress"] = _build_progress_string(entry, meta, today, is_official)
    entry["condition_met"] = _condition_fully_met(entry, meta, today, is_official)


def _collect_and_groups(distances: list) -> list:
    """Rebuild the AND-group verdict list from evaluated legs.

    Aggregates on `condition_met` (which includes the time basis), never on
    `met_close`: a 終値2日連続 leg holding only today has not been met, and
    treating it as met fired the group a day early.
    """
    groups = {}
    for d in distances:
        for e in d.get("trigger_distances", []):
            gid = e.get("and_group")
            if gid:
                groups.setdefault(gid, []).append(e)
    out = []
    for gid in sorted(groups):
        legs = groups[gid]
        flags = [leg.get("condition_met") for leg in legs]
        out.append({
            "group": gid,
            "leg_count": len(legs),
            "met_count": sum(1 for f in flags if f),
            "satisfied": len(legs) >= 2 and all(f is True for f in flags),
            "legs": [leg["trigger"] for leg in legs],
        })
    return out


def _condition_fully_met(
    entry: dict, meta: dict, today: date, is_official: bool,
) -> Optional[bool]:
    """Whether the leg's condition holds INCLUDING its time basis.

    `met_close` alone answers "is the level breached today", which is not the
    same as "has the condition been met". A leg written as 終値2日連続 needs the
    previous close too; a 週足 leg is only decided on Friday. Aggregating groups
    or scenarios on `met_close` fires them a day early.

    Returns None when the verdict cannot be established yet (pre-market, or a
    consecutive-day leg with no previous close on file).
    """
    if not meta["is_price_trigger"] or not meta["direction"]:
        return None

    if meta["time_basis"] == "weekly_close":
        # Only Friday's official close settles a weekly condition.
        if today.weekday() == 4 and is_official:
            return bool(entry.get("met_close"))
        return None

    if not is_official:
        return None  # provisional quote; the close has not printed yet

    if meta["required_days"] > 1:
        met_prev = entry.get("met_prev")
        if met_prev is None:
            return None  # cannot confirm consecutiveness without the prior close
        held_both = bool(entry.get("met_close")) and bool(met_prev)
        if meta["required_days"] > _MAX_CONFIRMED_DAYS:
            # Only today and the previous close are on file, so a 3-day (or
            # longer) run cannot be established. Saying True here fired a
            # "17超を終値3日連続" leg on two days, and contradicted the progress
            # text, which already reported "2/3日達成（2日分のみ確認可）".
            # A run that has already broken is still a definite miss.
            return None if held_both else False
        return held_both

    return bool(entry.get("met_close"))


_BULLET_PREFIX = re.compile(r"^\s*[-*・]\s*")

# "- 終値2日系 (2日確認後の翌営業日寄り): VIX 17超..." — the label carries digits
# ("2日") that would be read as the level. Strip it, but never strip a clock time
# ("8/20(木) 03:00"), which is why the char before the colon must not be a digit.
_LEG_LABEL_PREFIX = re.compile(r"^[^:：\d][^:：]*[^\d:：][:：]\s+")


def _split_trigger_lines(trigger: str) -> list[str]:
    """Split a trigger blob into one line per bullet, minus bullet/label prefix."""
    lines = []
    for raw in trigger.splitlines():
        line = _BULLET_PREFIX.sub("", raw).strip()
        if not line:
            continue
        line = _LEG_LABEL_PREFIX.sub("", line).strip()
        if line:
            lines.append(line)
    return lines


# A leg can carry one threshold per date. The 2026-09-07 article wrote the
# GREEN-flip hurdles as "9/8 に 23.56% 超、9/9 に 24.38% 超、9/10 に 22.46% 超、
# または 9/11 に 22.63% 超": taking the first number applied Monday's hurdle to
# every day of the week, which both misses a real flip and invents one.
_DATED_THRESHOLD = re.compile(
    r"(\d{1,2})\s*/\s*(\d{1,2})\s*に\s*(?:\*\*)?\s*(\d+(?:\.\d+)?)\s*%"
)


def _dated_threshold(trigger: str, today: date) -> tuple[Optional[float], bool]:
    """(threshold for `today`, whether the leg is date-qualified at all).

    Returns (None, True) when the leg lists per-date thresholds but none match
    today: the caller must then leave the leg unevaluated rather than fall back
    to another day's number.
    """
    pairs = _DATED_THRESHOLD.findall(trigger)
    if len(pairs) < 2:
        return None, False
    for mth, day, pct in pairs:
        if int(mth) == today.month and int(day) == today.day:
            return float(pct), True
    return None, True


def _compute_trigger_distance(
    scenarios: dict, market: dict, breadth: dict,
    timing: str, today: date,
) -> list[dict]:
    """Compute distance from current values to scenario triggers."""
    distances = []
    vix = market.get("vix", {}).get("price")
    sp500 = market.get("sp500", {}).get("price")
    nasdaq = market.get("nasdaq", {}).get("price")
    dow = market.get("dow", {}).get("price")
    oil = market.get("oil", {}).get("price")
    russell = market.get("russell", {}).get("price")
    copper = market.get("copper", {}).get("price")
    us10y = market.get("us10y", {}).get("value")
    us30y = market.get("us30y", {}).get("value")
    us2y = market.get("us2y", {}).get("value")
    us5y = market.get("us5y", {}).get("value")
    curve_2s10s = market.get("curve_2s10s", {}).get("value")
    uptrend_ratio = breadth.get("uptrend_ratio")
    cross_diff = breadth.get("cross_diff")
    breadth_50_raw = breadth.get("breadth_50_raw")
    breadth_raw = breadth.get("breadth_raw")

    for name, scenario in scenarios.items():
        triggers = scenario.get("triggers", [])
        # Compound OR-triggers ("A / B / C") must be split so each leg pairs
        # its own indicator with its own level; matching the full string lets
        # the first branch win with a wrong number (e.g. the VIX branch pairing
        # the "10" of "10年債" as target 10.0).
        # Compound AND-triggers ("A — かつ — B") are split the same way, but
        # tagged with a shared and_group so consumers know every leg must be
        # met (an OR leg alone is sufficient; an AND leg alone is not).
        segments: list = []
        for idx, trigger in enumerate(triggers):
            # A trigger blob may carry several bullet lines ("- 単日確定系: ... /
            # WTI 77.79 終値割れ" then "- 終値2日系: VIX 17超..."). Splitting on
            # "/" alone leaves the last leg of one line glued to the next line,
            # so the VIX branch would read WTI's 77.79 as the VIX level.
            for line in _split_trigger_lines(trigger):
                for or_leg in re.split(r"\s+/\s+", line):
                    or_leg = or_leg.strip()
                    if not or_leg:
                        continue
                    and_legs = [s.strip() for s in _AND_SEPARATOR.split(or_leg) if s.strip()]
                    gid = f"{name}#{idx}" if len(and_legs) > 1 else None
                    segments.extend((leg, gid) for leg in and_legs)
        trigger_distances = []
        unevaluated = []
        for trigger, and_group in segments:
            n_before = len(trigger_distances)
            # VIX distance
            if vix and "VIX" in trigger.upper():
                # Prefer the number that follows "VIX" so a leg that still holds
                # another instrument's level cannot donate it as the VIX target.
                vix_m = re.search(r"VIX[^\d]{0,12}(\d+(?:\.\d+)?)", trigger, re.I) \
                    or re.search(r"(\d+(?:\.\d+)?)", trigger)
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
            # Dow distance. Must precede the S&P branch for the same reason as
            # Nasdaq: Dow levels such as "46,000" carry the "6," substring.
            # Matched on the index name only — a "DIA 換算 ≈ $535.7" note is
            # ETF-scale and would be read as an index level.
            elif dow and ("DOW" in trigger.upper() or "DJI" in trigger.upper()
                          or "ダウ" in trigger):
                target = _first_index_level(trigger)
                if target is not None:
                    entry = {
                        "trigger": trigger,
                        "indicator": "Dow Jones",
                        "current": dow,
                        "target": target,
                        "diff": round(dow - target, 2),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "dow", timing, today,
                    )
                    trigger_distances.append(entry)
            # Nasdaq distance. Must precede the S&P branch: NDX levels such as
            # "26,233" contain the "6," substring the S&P branch matches on.
            elif nasdaq and ("NDX" in trigger.upper() or "NASDAQ" in trigger.upper()):
                target = _first_index_level(trigger)
                if target is not None:
                    diff = nasdaq - target
                    entry = {
                        "trigger": trigger,
                        "indicator": "Nasdaq 100",
                        "current": nasdaq,
                        "target": target,
                        "diff": round(diff, 2),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "nasdaq", timing, today,
                    )
                    trigger_distances.append(entry)
            # S&P distance
            elif sp500 and ("S&P" in trigger or "SPX" in trigger.upper()
                            or "6," in trigger or "7," in trigger):
                target = _first_index_level(trigger)
                if target is not None:
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
            # 30Y Treasury yield distance. Must precede the 10Y branch so a
            # "30年債" leg is never absorbed by a neighbouring rule.
            elif us30y and ("30年債" in trigger or "30年金利" in trigger
                            or "30Y" in trigger.upper()):
                y30_m = re.search(r"(\d+(?:\.\d+)?)\s*%", trigger)
                if y30_m:
                    target = float(y30_m.group(1))
                    entry = {
                        "trigger": trigger,
                        "indicator": "US 30Y Yield",
                        "current": us30y,
                        "target": target,
                        "diff": round(us30y - target, 3),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "us30y", timing, today,
                    )
                    trigger_distances.append(entry)
            # 10Y Treasury yield distance. Levels are quoted in percent
            # ("10年債 4.501%〜4.806% レンジ"), so match on the percent sign to
            # avoid picking up the "10" of the "10年債" label itself.
            elif us10y and ("10年債" in trigger or "10年金利" in trigger
                            or "10Y" in trigger.upper()):
                y_m = re.search(r"(\d+(?:\.\d+)?)\s*%", trigger)
                if y_m:
                    target = float(y_m.group(1))
                    diff = us10y - target
                    entry = {
                        "trigger": trigger,
                        "indicator": "US 10Y Yield",
                        "current": us10y,
                        "target": target,
                        "diff": round(diff, 3),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "us10y", timing, today,
                    )
                    trigger_distances.append(entry)
            # Russell / IWM distance. Small caps are the most rate-sensitive
            # index, so weeks driven by the front end put the first trigger
            # here. Placed before the oil branch: without its own branch a
            # "Russell 2,883.0 終値割れ (IWM ≈ $286.86)" leg fell through to
            # oil's "$" fallback and became a phantom "WTI 883.0".
            elif russell and ("RUSSELL" in trigger.upper() or "RUT" in trigger.upper()
                              or "IWM" in trigger.upper() or "ラッセル" in trigger):
                target = _first_index_level(trigger)
                if target is not None:
                    entry = {
                        "trigger": trigger,
                        "indicator": "Russell 2000",
                        "current": russell,
                        "target": target,
                        "diff": round(russell - target, 2),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "russell", timing, today,
                    )
                    trigger_distances.append(entry)
            # 2s10s curve spread, quoted in basis points ("2s10s が 30bp 割れ").
            # Must precede the yield branches so the "10" of "2s10s" is never
            # read as a 10Y level.
            elif curve_2s10s is not None and ("2S10S" in trigger.upper()
                                              or "2s10s" in trigger
                                              or "2年10年差" in trigger):
                c_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:bp|BP|ｂｐ)", trigger)
                if c_m:
                    target = float(c_m.group(1))
                    entry = {
                        "trigger": trigger,
                        "indicator": "2s10s Spread",
                        "current": curve_2s10s,
                        "target": target,
                        "diff": round(curve_2s10s - target, 1),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "curve_2s10s", timing, today,
                    )
                    trigger_distances.append(entry)
            # 2Y Treasury yield. Must precede the 10Y branch so "米2年債" is
            # never absorbed by a neighbouring rule.
            elif us2y and ("2年債" in trigger or "2年金利" in trigger
                           or "2Y" in trigger.upper()):
                y2_m = re.search(r"(\d+(?:\.\d+)?)\s*%", trigger)
                if y2_m:
                    target = float(y2_m.group(1))
                    entry = {
                        "trigger": trigger,
                        "indicator": "US 2Y Yield",
                        "current": us2y,
                        "target": target,
                        "diff": round(us2y - target, 3),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "us2y", timing, today,
                    )
                    trigger_distances.append(entry)
            # 5Y Treasury yield. The 2026-09-07 article moved the policy-path
            # trigger to the belly (5Y +6.0bp, the largest move of any tenor)
            # and dropped the 2Y levels; without this branch those four legs
            # were unevaluable and the coverage gate failed closed.
            elif us5y and ("5年債" in trigger or "5年金利" in trigger
                           or "5Y" in trigger.upper()):
                y5_m = re.search(r"(\d+(?:\.\d+)?)\s*%", trigger)
                if y5_m:
                    target = float(y5_m.group(1))
                    entry = {
                        "trigger": trigger,
                        "indicator": "US 5Y Yield",
                        "current": us5y,
                        "target": target,
                        "diff": round(us5y - target, 3),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "us5y", timing, today,
                    )
                    trigger_distances.append(entry)
            # Copper ("銅 HG 6.1615 終値割れ"). Priced in dollars per pound, so
            # the level is a single digit with four decimals.
            elif copper and ("銅" in trigger or "COPPER" in trigger.upper()
                             or "HG" in trigger.upper()):
                cu_m = re.search(r"(\d+\.\d+)", trigger)
                if cu_m:
                    target = float(cu_m.group(1))
                    entry = {
                        "trigger": trigger,
                        "indicator": "Copper",
                        "current": copper,
                        "target": target,
                        "diff": round(copper - target, 4),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "copper", timing, today,
                    )
                    trigger_distances.append(entry)
            # Uptrend Ratio ("Uptrend Ratio 17.81% 割れ"). A leading breadth
            # series the article treats as its primary internal gauge.
            elif uptrend_ratio is not None and ("UPTREND" in trigger.upper()
                                                or "上昇銘柄比率" in trigger):
                dated_target, is_dated = _dated_threshold(trigger, today)
                up_m = re.search(r"(\d+(?:\.\d+)?)\s*%", trigger)
                if is_dated and dated_target is None:
                    # Per-date hurdles with none for today: no threshold
                    # applies. Claim nothing, so the fallback below records the
                    # leg as unevaluated instead of a wrong verdict standing.
                    pass
                elif is_dated or up_m:
                    target = (
                        dated_target if dated_target is not None
                        else float(up_m.group(1))
                    )
                    entry = {
                        "trigger": trigger,
                        "indicator": "Uptrend Ratio",
                        "current": uptrend_ratio,
                        "target": target,
                        "diff": round(uptrend_ratio - target, 2),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "uptrend_ratio", timing, today,
                    )
                    trigger_distances.append(entry)
            # Breadth-50 raw reading ("Breadth-50 生値 50% 割れ"). Quoted as a
            # percentage, unlike the 8MA-200MA spread which is quoted in pt.
            elif breadth_50_raw is not None and ("BREADTH-50" in trigger.upper()
                                                 or "BREADTH 50" in trigger.upper()
                                                 or "BREADTH-50" in trigger):
                b50_m = re.search(r"(\d+(?:\.\d+)?)\s*%", trigger)
                if b50_m:
                    target = float(b50_m.group(1))
                    entry = {
                        "trigger": trigger,
                        "indicator": "Breadth-50 Raw",
                        "current": breadth_50_raw,
                        "target": target,
                        "diff": round(breadth_50_raw - target, 2),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "breadth_50_raw", timing, today,
                    )
                    trigger_distances.append(entry)
            # Breadth 200-series raw reading ("Breadth 生値 (200日線上) が
            # 64.0% を CSV 2データ点連続で下回る"). The 2026-09-07 article moved
            # the Stress condition off the 8MA-200MA spread and onto the raw
            # percentage, because both averages are EMAs and the spread is
            # decided by the raw level. Quoted in %, so it must be claimed
            # before the spread branch, which reads a pt value.
            elif (breadth_raw is not None and "BREADTH" in trigger.upper()
                  and ("生値" in trigger or "RAW" in trigger.upper())):
                braw_m = re.search(r"(\d+(?:\.\d+)?)\s*%", trigger)
                if braw_m:
                    target = float(braw_m.group(1))
                    entry = {
                        "trigger": trigger,
                        "indicator": "Breadth Raw (200MA basis)",
                        "current": breadth_raw,
                        "target": target,
                        "diff": round(breadth_raw - target, 2),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "breadth_raw", timing, today,
                    )
                    trigger_distances.append(entry)
            # Breadth 8MA-200MA spread ("Breadth 8MA と 200MA の差が +7pt 割れ").
            elif cross_diff is not None and "BREADTH" in trigger.upper():
                br_m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*(?:pt|PT|ポイント)", trigger)
                if br_m:
                    target = float(br_m.group(1))
                    entry = {
                        "trigger": trigger,
                        "indicator": "Breadth 8MA-200MA",
                        "current": cross_diff,
                        "target": target,
                        "diff": round(cross_diff - target, 2),
                    }
                    _enrich_trigger_entry(
                        entry, trigger, market, "cross_diff", timing, today,
                    )
                    trigger_distances.append(entry)
            # Oil distance ("WTI 93.50 終値上抜け" has no $ prefix). The bare
            # "$" fallback only applies when no other instrument is named:
            # blog legs routinely carry an ETF conversion ("(IWM ≈ $286.86)"),
            # and letting "$" alone claim them produced phantom oil targets.
            elif oil and ("原油" in trigger or "WTI" in trigger.upper()
                          or ("$" in trigger and not _names_other_instrument(trigger))):
                oil_m = re.search(r"\$?(\d{2,3}(?:\.\d+)?)", trigger)
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

            if len(trigger_distances) == n_before:
                # No branch claimed this leg. Recording it is what makes the
                # coverage gate fail-closed: a silently dropped leg used to
                # look identical to a scenario that simply had fewer triggers.
                unevaluated.append(trigger)
            for e in trigger_distances[n_before:]:
                e["and_group"] = and_group

        distances.append({
            "scenario": name,
            "probability": scenario.get("probability"),
            "trigger_distances": trigger_distances,
            "source_leg_count": len(segments),
            "evaluated_leg_count": len(trigger_distances),
            "unevaluated_legs": unevaluated,
        })


    # Group verdicts, stamped onto every leg so a consumer reading a single
    # row cannot mistake one met leg for a fired AND scenario.
    for g in _collect_and_groups(distances):
        for d in distances:
            for e in d["trigger_distances"]:
                if e.get("and_group") == g["group"]:
                    e["and_satisfied"] = g["satisfied"]

    # Scenario-level verdicts. The blog states how many legs must hold
    # ("すべて満たす" / "2つ以上" / "いずれか1つ"); without carrying that rule every
    # scenario reads as a plain OR, so a Base case needing all five legs would
    # look fired on one.
    for d in distances:
        sc = scenarios.get(d["scenario"], {})
        rule = sc.get("satisfaction_rule")
        min_legs = sc.get("min_legs")
        # A missing rule is a broken contract, not an OR. Defaulting to "any"
        # turned a dropped field into a scenario that fires on one leg.
        rule_missing = rule is None or (rule == "at_least" and min_legs is None)
        if rule is None:
            rule = "unknown"
        if min_legs is None:
            min_legs = 0

        legs = d["trigger_distances"]
        flags = [e.get("condition_met") for e in legs]
        met = sum(1 for f in flags if f)
        undecided = any(f is None for f in flags)
        if not legs:
            satisfied = False
        elif rule == "all":
            satisfied = all(f is True for f in flags)
        elif rule == "at_least":
            satisfied = met >= min_legs
        elif rule == "any":
            satisfied = met >= 1
        else:
            satisfied = False
        # An "all" rule cannot be declared satisfied while a leg is undecided.
        if rule == "all" and undecided:
            satisfied = False
        if rule_missing:
            satisfied = False

        # Independent conditions the article states outside the leg list
        # ("CPI 発表後の終値でも条件が残っていること", a veto, an execution-date
        # limit). They are prose, not levels, so they cannot be evaluated
        # mechanically — and a scenario carrying one must not be reported as
        # fired on its price legs alone.
        gates = [g for g in (sc.get("gates") or []) if g]
        if gates:
            satisfied = False

        d["satisfaction_rule"] = rule
        d["min_legs"] = min_legs
        d["rule_missing"] = rule_missing
        d["gates"] = gates
        d["gates_unevaluated"] = bool(gates)
        d["met_leg_count"] = met
        d["undecided_leg_count"] = sum(1 for f in flags if f is None)
        d["scenario_satisfied"] = satisfied

    return distances


# --- Source-text audit ------------------------------------------------------
# `source_leg_total` counts legs in parse_blog's OUTPUT, so a scenario the
# parser could not read contributes 0 legs and checks 18-20 all pass on 0 of 0.
# This audit reads the article text directly: when a scenario block carries a
# trigger label but no leg survived parsing, the run must fail rather than
# report full coverage of nothing.

# "### シナリオ 2 (Risk-On): ..." — the char after シナリオ must not be 別, so
# the section heading "## シナリオ別プラン" is not mistaken for a scenario.
_RAW_SCENARIO_HEADING = re.compile(
    r"^#{2,4}\s*(シナリオ\s*[0-9０-９A-Za-z][^\n]*)$", re.M
)
_RAW_TRIGGER_LABEL = re.compile(r"\*\*(?:トリガー(?:条件)?|発動条件|条件)[^*\n]*\*\*")

# Whether a block STATES conditions, judged without reference to the label:
# a heading the parser does not know ("**判定基準**:") leaves the legs in the
# article and out of the plan, and a label-based test cannot see that. A line
# naming an instrument, a number and a comparison is a condition.
_RAW_INSTRUMENTS = (
    "VIX", "SPX", "S&P", "NDX", "Nasdaq", "ナスダック", "Dow", "ダウ",
    "Russell", "小型株", "10年債", "30年債", "2年債", "5年債", "利回り",
    "WTI", "原油", "銅", "HG", "金", "GC", "GLD", "SPY", "QQQ", "DIA", "IWM",
    "Uptrend", "Breadth", "値上がり銘柄比率", "参加率",
)
_RAW_COMPARISON = re.compile(
    r"(終値|割れ|割り込|上抜け|下抜け|超|未満|以上|以下|回復|維持|下回|上回)"
)


def _block_states_conditions(block: str) -> bool:
    """True when some line names an instrument, a number and a comparison."""
    for line in block.splitlines():
        if not any(ch.isdigit() for ch in line):
            continue
        if not _RAW_COMPARISON.search(line):
            continue
        if any(name in line for name in _RAW_INSTRUMENTS):
            return True
    return False
_RAW_HEADING_PROB = re.compile(r"(\d{1,3})\s*%")


def _heading_probability(heading: str) -> Optional[int]:
    """The scenario probability written in its heading, if any."""
    tail = heading.split("筆者推定")[-1]
    matches = _RAW_HEADING_PROB.findall(tail) or _RAW_HEADING_PROB.findall(heading)
    return int(matches[-1]) if matches else None


def _audit_source_triggers(blog_text: str, spec_scenarios: dict) -> dict:
    """Compare the article's scenario blocks against what the parser produced.

    Joins on the probability written in each heading, which is the one field
    both sides carry. Returns `applicable: False` for articles whose headings do
    not match the Japanese scenario format (older English posts), so the gate
    never fails on a format it was not written for.
    """
    headings = list(_RAW_SCENARIO_HEADING.finditer(blog_text))
    if not headings:
        return {
            "applicable": False,
            "reason": "no Japanese scenario headings found",
            "raw_scenario_count": 0,
            "parsed_scenario_count": len(spec_scenarios),
            "gaps": [],
        }

    # Join article blocks to parsed scenarios by POSITION when the counts
    # agree: probability is not an identifier, and two scenarios sharing one
    # (50/50) let a block whose conditions vanished borrow the other block's
    # legs, which is the same blind spot one level up.
    ordered = list(spec_scenarios.items())
    positional = len(ordered) == len(headings)

    by_prob: dict = {}
    for name, sc in spec_scenarios.items():
        by_prob.setdefault(sc.probability, []).append((name, sc))
    ambiguous_prob = any(len(v) > 1 for v in by_prob.values())

    gaps = []
    with_label = 0

    # The article and the parse must describe the same number of scenarios.
    # Without this, a scenario missing entirely from the parse slipped through
    # whenever another scenario happened to share its probability.
    if not positional:
        gaps.append({
            "heading": "(all)",
            "reason": (
                f"scenario count mismatch: {len(headings)} in the article, "
                f"{len(ordered)} parsed"
            ),
        })

    for i, m in enumerate(headings):
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(blog_text)
        section = re.search(r"^##\s", blog_text[start:end], re.M)
        if section:
            end = start + section.start()
        block = blog_text[start:end]
        heading = m.group(1).strip()

        has_label = bool(_RAW_TRIGGER_LABEL.search(block))
        if has_label:
            with_label += 1
        if not (has_label or _block_states_conditions(block)):
            continue

        prob = _heading_probability(heading)
        if positional:
            candidates = [ordered[i]]
        else:
            candidates = by_prob.get(prob) if prob is not None else None
            if candidates and ambiguous_prob and len(candidates) > 1:
                gaps.append({
                    "heading": heading[:70],
                    "reason": (
                        f"cannot map to a parsed scenario: probability {prob} "
                        f"is shared by {len(candidates)} scenarios and the "
                        f"counts differ ({len(headings)} in the article, "
                        f"{len(ordered)} parsed)"
                    ),
                })
                continue
        if not candidates:
            gaps.append({
                "heading": heading[:70],
                "reason": f"no parsed scenario with probability {prob}",
            })
            continue
        if all(not sc.triggers for _, sc in candidates):
            gaps.append({
                "heading": heading[:70],
                "reason": (
                    "conditions written in the article, 0 legs parsed"
                    if not has_label else
                    "trigger block in the article, 0 legs parsed"
                ),
            })

    return {
        "applicable": True,
        "join": "position" if positional else "probability",
        "raw_scenario_count": len(headings),
        "raw_with_trigger_block": with_label,
        "parsed_scenario_count": len(spec_scenarios),
        "gaps": gaps,
    }


def build_plan_state(
    timing: str,
    market_json: dict,
    breadth_json: dict,
    blog_path: str,
    today: date = None,
    manual_only_legs: list = None,
) -> dict:
    """Build the plan_state structure.

    `manual_only_legs` declares trigger legs that are checked by hand.
    Coverage check #18 is fail-closed, so a leg no branch can evaluate
    must be declared here rather than silently dropped.
    """
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

    # Treasury yields. `prev_close` comes from the previous business day's row
    # of the FMP treasury series; without it a "終値2日連続" yield trigger can
    # never reach 2/2 because _enrich_trigger_entry has no prior value to test.
    treasury_prev = treasury.get("_prev") or {}

    us10y = _safe_float(treasury.get("year10"))
    yield_eval = _classify(us10y, YIELD_THRESHOLDS) if us10y else ""
    market["us10y"] = {
        "value": us10y,
        "prev_close": _safe_float(treasury_prev.get("year10")),
        "eval": yield_eval,
    }

    # Treasury 30Y. Scenario triggers reference it directly ("30年債 5.30%
    # 終値上抜け"), so without it that leg is silently unevaluated.
    # No eval label: the Monty threshold table is defined for the 10Y only.
    market["us30y"] = {
        "value": _safe_float(treasury.get("year30")),
        "prev_close": _safe_float(treasury_prev.get("year30")),
        "eval": "",
    }

    # Treasury 2Y. The 2026-08-31 week moved the primary rate trigger to the
    # front end (2年債 +10bp while the 10Y fell 1bp), so a 10Y-only market dict
    # cannot evaluate the article's own headline condition.
    us2y = _safe_float(treasury.get("year2"))
    market["us2y"] = {
        "value": us2y,
        "prev_close": _safe_float(treasury_prev.get("year2")),
        "eval": "",
    }

    # Treasury 5Y. Same reason as the 2Y entry above: the 2026-09-07 week put
    # the policy-path trigger on the belly of the curve.
    market["us5y"] = {
        "value": _safe_float(treasury.get("year5")),
        "prev_close": _safe_float(treasury_prev.get("year5")),
        "eval": "",
    }

    # 2s10s spread in basis points, plus its previous close, so curve triggers
    # ("2s10s が 30bp 割れを終値2日連続") are evaluable on the same footing.
    prev_2y = _safe_float(treasury_prev.get("year2"))
    prev_10y = _safe_float(treasury_prev.get("year10"))
    market["curve_2s10s"] = {
        "value": (
            round((us10y - us2y) * 100, 1)
            if us10y is not None and us2y is not None else None
        ),
        "prev_close": (
            round((prev_10y - prev_2y) * 100, 1)
            if prev_10y is not None and prev_2y is not None else None
        ),
        "eval": "",
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
        "breadth_50_raw": _safe_float(breadth_json.get("breadth_50_raw")),
        "breadth_raw": _safe_float(breadth_json.get("breadth_raw")),
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
        # satisfaction_rule/min_legs must travel with the scenario. Dropping
        # them here made every scenario an OR at the real entry point, however
        # correctly the parser had read "すべて満たす" or "2つ以上", so a Base
        # case needing five legs looked fired on one and the unit tests that
        # passed the parser's own output never saw it.
        scenarios[name] = {
            "probability": sc.probability,
            "triggers": sc.triggers,
            "allocation": sc.allocation,
            "satisfaction_rule": getattr(sc, "satisfaction_rule", None),
            "min_legs": getattr(sc, "min_legs", None),
            "gates": list(getattr(sc, "gates", []) or []),
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
    # Heading wording drifts week to week: "夜チェック" (through 2026-06) vs
    # "夜・早朝チェック — JST 基準" (2026-07 onward).
    morning_checklist = _parse_checklist(
        blog_text, ("朝チェック",), exclude=("夜",),
    )
    evening_checklist = _parse_checklist(
        blog_text, ("夜チェック", "夜・早朝チェック", "夜／早朝チェック", "夜・翌朝チェック"),
    )

    # Trigger distances
    trigger_distances = _compute_trigger_distance(
        scenarios, market, breadth, timing, today,
    )

    # Coverage summary. verify_plan fails closed on this: every leg written in
    # the blog must either be evaluated here or be named in manual_only.
    # Counting only the emitted rows hid 9 of 21 legs on 2026-08-31.
    # Per-group AND verdicts. Action generation must read `satisfied` and never
    # a single leg: an AND group whose partner is unmet has NOT fired, and the
    # met leg on its own is not a signal.

    source_audit = _audit_source_triggers(blog_text, spec.scenarios)

    trigger_coverage = {
        "source_audit": source_audit,
        "source_leg_total": sum(d["source_leg_count"] for d in trigger_distances),
        "evaluated_leg_total": sum(d["evaluated_leg_count"] for d in trigger_distances),
        "per_scenario": {
            d["scenario"]: {
                "source": d["source_leg_count"],
                "evaluated": d["evaluated_leg_count"],
            }
            for d in trigger_distances
        },
        "unevaluated": {
            d["scenario"]: d["unevaluated_legs"]
            for d in trigger_distances if d["unevaluated_legs"]
        },
        "manual_only": list(manual_only_legs or []),
        "and_groups": _collect_and_groups(trigger_distances),
        "scenario_rules": {
            d["scenario"]: {
                "rule": d["satisfaction_rule"],
                "min_legs": d["min_legs"],
                "rule_missing": d.get("rule_missing", False),
                "gates": d.get("gates", []),
                "gates_unevaluated": d.get("gates_unevaluated", False),
                "leg_count": len(d["trigger_distances"]),
                "met_leg_count": d["met_leg_count"],
                "undecided_leg_count": d["undecided_leg_count"],
                "satisfied": d["scenario_satisfied"],
            }
            for d in trigger_distances
        },
    }

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
            "trigger_coverage": trigger_coverage,
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
    parser.add_argument(
        "--manual-only-leg",
        action="append",
        default=[],
        metavar="TEXT",
        help=(
            "Declare a trigger leg as manually checked (repeatable). Coverage "
            "check #18 is fail-closed: a leg no branch can evaluate makes it "
            "fail unless declared here. Use the leg text exactly as it appears "
            "in trigger_coverage.unevaluated."
        ),
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
        manual_only_legs=args.manual_only_leg,
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
