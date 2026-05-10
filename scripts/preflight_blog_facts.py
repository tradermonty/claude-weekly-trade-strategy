#!/usr/bin/env python3
"""Preflight blog fact snapshot generator.

Generates `reports/YYYY-MM-DD/facts_snapshot.json` with:
- ETF spot prices (FMP API)
- Option expiries (Cboe / VIX calendars, US holiday-aware)
- US federal holidays in target window
- Day-of-week verification table
- Fed events placeholder (must be filled by market-news-analyzer)

Usage:
    python3 scripts/preflight_blog_facts.py --date 2026-05-11
    python3 scripts/preflight_blog_facts.py --date 2026-05-11 --out reports/2026-05-11/facts_snapshot.json

This is the upstream half of the CI pipeline. Downstream (`postflight_blog_check.py`)
verifies that the blog draft body matches this snapshot.

Reference: CLAUDE.md Issue #18 (ETF Spot), #19 (Option Expiry Holidays), #20 (IR Times).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ETF_SYMBOLS = [
    "SPY", "QQQ", "DIA", "IWM",
    "GLD", "SLV", "URA", "TLT", "BIL",
    "XLE", "XLP", "XLV", "XLF", "XLK", "XLY", "XLI", "XLU", "XLRE", "XLB", "XLC",
]

INDEX_FUTURES_SYMBOLS = ["^VIX", "^GSPC", "^NDX", "^DJI"]
COMMODITY_SYMBOLS = ["CLUSD", "GCUSD", "HGUSD", "NGUSD"]


# US federal market holidays 2026 (NYSE / Cboe closed)
US_MARKET_HOLIDAYS_2026 = {
    "2026-01-01": "New Year's Day",
    "2026-01-19": "Martin Luther King Jr. Day",
    "2026-02-16": "Presidents Day",
    "2026-04-03": "Good Friday",
    "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth",
    "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day",
    "2026-11-26": "Thanksgiving",
    "2026-12-25": "Christmas",
}


# Cboe 2026 monthly equity/ETF option standard expiries (third Friday, shifted for holidays)
# Source: https://cdn.cboe.com/resources/options/Cboe2026OPTIONSCalendar.pdf
EQUITY_ETF_MONTHLY_2026 = {
    1: "2026-01-16",
    2: "2026-02-20",
    3: "2026-03-20",
    4: "2026-04-17",   # Good Friday is 4/3 (3rd Friday is 4/17, no shift needed)
    5: "2026-05-15",
    6: "2026-06-18",   # Juneteenth 6/19 → shift to 6/18 (Thu)
    7: "2026-07-17",
    8: "2026-08-21",
    9: "2026-09-18",
    10: "2026-10-16",
    11: "2026-11-20",
    12: "2026-12-18",  # Christmas 12/25 (Fri) → 3rd Friday 12/18 unaffected
}


# VIX monthly options (typically 30 days before SPX month following, on Wednesday;
# shifted earlier when SPX expiry is shifted)
# Source: Macroption + Cboe VIX calendar
VIX_MONTHLY_2026 = {
    1: "2026-01-21",   # Wed
    2: "2026-02-18",   # Wed
    3: "2026-03-18",   # Wed
    4: "2026-04-15",   # Wed
    5: "2026-05-19",   # Tue (shifted earlier due to Juneteenth affecting Jun SPX)
    6: "2026-06-17",   # Wed
    7: "2026-07-22",   # Wed
    8: "2026-08-19",   # Wed
    9: "2026-09-16",   # Wed
    10: "2026-10-21",  # Wed
    11: "2026-11-18",  # Wed
    12: "2026-12-16",  # Wed
}


def fmp_quote_batch(symbols: list[str], api_key: str) -> dict[str, dict[str, Any]]:
    """Fetch FMP quote/full data for a list of symbols."""
    url = f"https://financialmodelingprep.com/api/v3/quote/{','.join(symbols)}?apikey={api_key}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"FMP quote fetch failed for {symbols}: {exc}", file=sys.stderr)
        return {}
    return {row.get("symbol"): row for row in data if row.get("symbol")}


def get_fmp_api_key() -> str:
    key = os.environ.get("FMP_API_KEY", "")
    if key:
        return key
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("FMP_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def get_market_prices(api_key: str) -> dict[str, dict[str, Any]]:
    """Fetch ETF + index + commodity prices from FMP."""
    all_symbols = ETF_SYMBOLS + INDEX_FUTURES_SYMBOLS + COMMODITY_SYMBOLS
    quotes = fmp_quote_batch(all_symbols, api_key)
    out: dict[str, dict[str, Any]] = {}
    for sym in all_symbols:
        row = quotes.get(sym)
        if not row:
            continue
        out[sym] = {
            "price": row.get("price"),
            "change": row.get("change"),
            "change_pct": row.get("changesPercentage"),
            "prev_close": row.get("previousClose"),
            "day_high": row.get("dayHigh"),
            "day_low": row.get("dayLow"),
            "as_of_ts": row.get("timestamp"),
        }
    return out


def derive_gc_gld_ratio(prices: dict[str, Any]) -> float | None:
    gc = prices.get("GCUSD", {}).get("price")
    gld = prices.get("GLD", {}).get("price")
    if not gc or not gld:
        return None
    return round(gc / gld, 2)


def get_option_expiries(target_year: int, target_month: int) -> dict[str, Any]:
    """Return relevant option expiries for the target month and the next month."""
    months = [target_month, (target_month % 12) + 1]
    years = [target_year if m >= target_month else target_year + 1 for m in months]

    out = {
        "us_holidays_in_window": {},
        "equity_etf_standard": {},
        "vix_standard": {},
        "vix_weekly_wednesdays": [],
        "warnings": [],
    }

    for y, m in zip(years, months):
        if y == 2026:
            out["equity_etf_standard"][f"{y}-{m:02d}"] = EQUITY_ETF_MONTHLY_2026.get(m)
            out["vix_standard"][f"{y}-{m:02d}"] = VIX_MONTHLY_2026.get(m)

    if target_year == 2026 and target_month == 6:
        out["warnings"].append(
            "Juneteenth 6/19 (Fri) is a market holiday → June equity/ETF monthly expiry shifted to 6/18 (Thu); VIX May 2026 also shifted to 5/19 (Tue)."
        )

    for hdate_str, name in US_MARKET_HOLIDAYS_2026.items():
        hdate = date.fromisoformat(hdate_str)
        for y, m in zip(years, months):
            if hdate.year == y and hdate.month == m:
                out["us_holidays_in_window"][hdate_str] = name

    # Compute Wednesdays in the target month (VIX weeklies)
    first = date(target_year, target_month, 1)
    next_month = (target_month % 12) + 1
    next_year = target_year + 1 if next_month == 1 else target_year
    last = date(next_year, next_month, 1) - timedelta(days=1)
    d = first
    while d <= last:
        if d.weekday() == 2:  # Wed
            out["vix_weekly_wednesdays"].append(d.isoformat())
        d += timedelta(days=1)

    return out


def day_of_week_table(start: date, end: date) -> list[dict[str, str]]:
    out = []
    d = start
    while d <= end:
        out.append({
            "date": d.isoformat(),
            "day_en": d.strftime("%a"),
            "day_jp": ["月", "火", "水", "木", "金", "土", "日"][d.weekday()],
        })
        d += timedelta(days=1)
    return out


def jst_table(events_et: list[tuple[str, int, int, int, int, int]]) -> list[dict[str, str]]:
    """Convert (label, y, m, d, h, mi) ET tuples to JST."""
    out = []
    for label, y, m, d, h, mi in events_et:
        et = datetime(y, m, d, h, mi, tzinfo=ZoneInfo("America/New_York"))
        jst = et.astimezone(ZoneInfo("Asia/Tokyo"))
        out.append({
            "label": label,
            "et": et.strftime("%Y-%m-%d %a %H:%M ET"),
            "jst": jst.strftime("%Y-%m-%d %a %H:%M JST"),
        })
    return out


def build_snapshot(target_date: date) -> dict[str, Any]:
    api_key = get_fmp_api_key()
    if not api_key:
        print("WARNING: FMP_API_KEY not found. Market prices will be empty.", file=sys.stderr)
        prices = {}
    else:
        prices = get_market_prices(api_key)

    # 7-day window starting from target_date (Mon-Sun)
    start = target_date
    end = target_date + timedelta(days=6)

    snapshot = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(ZoneInfo("UTC")).isoformat(),
        "target_week_start": target_date.isoformat(),
        "target_week_end": end.isoformat(),
        "market_prices": prices,
        "gc_gld_ratio": derive_gc_gld_ratio(prices),
        "option_expiries": get_option_expiries(target_date.year, target_date.month),
        "day_of_week_table": day_of_week_table(start, end),
        "us_market_holidays_2026": US_MARKET_HOLIDAYS_2026,
        "fed_events_placeholder": {
            "note": "Filled by market-news-analyzer with WebFetch verification.",
            "speaker_events": [],
            "statistical_releases": [],
            "fomc_blackout": None,
        },
        "instructions_for_writer": [
            "Use ETF spot prices from market_prices.* as authoritative (Issue #18).",
            "Compute OTM% from spot and strike (no shortcut conversions).",
            "Use option_expiries.equity_etf_standard / vix_standard (Issue #19).",
            "Verify day-of-week against day_of_week_table before writing dates.",
            "Do not write earnings call times that are not in ir_events.yaml (Issue #20).",
        ],
    }
    return snapshot


def main() -> int:
    p = argparse.ArgumentParser(description="Preflight blog facts snapshot generator")
    p.add_argument("--date", required=True, help="Target week start date (YYYY-MM-DD, e.g. 2026-05-11)")
    p.add_argument("--out", default=None, help="Output path (default: reports/<date>/facts_snapshot.json)")
    args = p.parse_args()

    target_date = date.fromisoformat(args.date)
    snapshot = build_snapshot(target_date)

    out_path = Path(args.out) if args.out else PROJECT_ROOT / "reports" / args.date / "facts_snapshot.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))

    summary_lines = [
        f"# Preflight Facts Snapshot — {args.date}",
        f"Generated: {snapshot['generated_at_utc']}",
        f"Output: {out_path.relative_to(PROJECT_ROOT)}",
        "",
        "## ETF Spot Prices (must appear verbatim in blog body)",
    ]
    for sym in ["SPY", "QQQ", "DIA", "IWM", "GLD", "TLT", "BIL", "XLE", "XLP", "XLV"]:
        row = snapshot["market_prices"].get(sym)
        if row and row.get("price") is not None:
            summary_lines.append(f"  {sym}: ${row['price']:.2f} ({row.get('change_pct', 0):+.2f}%)")
    summary_lines.append("")
    summary_lines.append(f"GC/GLD Ratio: {snapshot['gc_gld_ratio']}")
    summary_lines.append("")
    summary_lines.append("## Option Expiries (use these in blog)")
    summary_lines.append("Equity/ETF monthly:")
    for k, v in snapshot["option_expiries"]["equity_etf_standard"].items():
        summary_lines.append(f"  {k}: {v}")
    summary_lines.append("VIX monthly:")
    for k, v in snapshot["option_expiries"]["vix_standard"].items():
        summary_lines.append(f"  {k}: {v}")
    summary_lines.append("VIX weekly (Wed):")
    for d in snapshot["option_expiries"]["vix_weekly_wednesdays"]:
        summary_lines.append(f"  {d}")
    if snapshot["option_expiries"]["warnings"]:
        summary_lines.append("")
        summary_lines.append("WARNINGS:")
        for w in snapshot["option_expiries"]["warnings"]:
            summary_lines.append(f"  ⚠ {w}")
    summary_lines.append("")
    summary_lines.append("## Day-of-Week Table")
    for row in snapshot["day_of_week_table"]:
        summary_lines.append(f"  {row['date']}: {row['day_en']} ({row['day_jp']})")
    summary_lines.append("")
    summary_lines.append("## Holidays in window")
    for d, name in snapshot["option_expiries"]["us_holidays_in_window"].items():
        summary_lines.append(f"  {d}: {name}")
    summary_lines.append("")
    summary_lines.append("Next: market-news-analyzer must fill `ir_events.yaml` with verified IR times.")

    print("\n".join(summary_lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
