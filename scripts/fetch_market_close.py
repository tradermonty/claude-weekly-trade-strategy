#!/usr/bin/env python3
"""
Fetch closing market data from FMP API.

Designed for daily action plan workflow: run after market close to get
accurate VIX, WTI, indices, commodities, ETF prices, and Treasury yields
in one shot -- eliminating WebSearch guesswork.

Uses only stdlib (no external dependencies).

Usage:
    python3 scripts/fetch_market_close.py              # Markdown table
    python3 scripts/fetch_market_close.py --json        # JSON output
    python3 scripts/fetch_market_close.py --compact     # Key indicators only

Data Source: FMP API (financialmodelingprep.com)
Note: FMP VIX may differ slightly from Cboe official. For discrepancies,
      user-confirmed TradingView/Cboe values take priority (see Issue #9).
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime

# --- Configuration ---

FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

# Symbols grouped by category
INDICES = [
    ("^VIX", "VIX"),
    ("^GSPC", "S&P 500"),
    ("^NDX", "Nasdaq 100"),
    ("^DJI", "Dow Jones"),
]

COMMODITIES = [
    ("CLUSD", "WTI Oil (CL)"),
    ("GCUSD", "Gold (GC)"),
    ("HGUSD", "Copper (HG)"),
    ("NGUSD", "Nat Gas (NG)"),
]

ETFS = [
    ("SPY", "SPY"),
    ("QQQ", "QQQ"),
    ("DIA", "DIA"),
    ("GLD", "GLD"),
    ("XLE", "XLE"),
    ("XLV", "XLV"),
    ("XLP", "XLP"),
    ("BIL", "BIL"),
    ("TLT", "TLT"),
    ("URA", "URA"),
]

TREASURY_KEYS = [
    ("month3", "3M"),
    ("year2", "2Y"),
    ("year5", "5Y"),
    ("year10", "10Y"),
    ("year30", "30Y"),
]

# Monty Style thresholds for evaluation
THRESHOLDS = {
    "^VIX": [
        (40.0, "Extreme"),
        (26.0, "Panic"),
        (23.0, "Stress"),
        (20.0, "Caution"),
        (17.0, "Risk-On"),
        (0.0, "Low Vol"),
    ],
    "us10y": [
        (4.60, "Extreme"),
        (4.50, "Red Line"),
        (4.36, "Warning"),
        (4.11, "Lower Bound"),
        (0.0, "Below Range"),
    ],
}


def _load_api_key() -> str:
    """Load FMP API key from environment or .env file."""
    key = os.environ.get("FMP_API_KEY", "")
    if key:
        return key

    # Try .env in project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("FMP_API_KEY=") and not line.startswith("#"):
                    return line.split("=", 1)[1].strip().strip("'\"")
    return ""


def _get_json(url: str, timeout: int = 15):
    """Fetch JSON from URL. Returns parsed data or None."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "fetch-market-close/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        print(f"ERROR: API request failed: {e}", file=sys.stderr)
        return None


def fetch_quotes(symbols: list[str], api_key: str) -> dict[str, dict]:
    """Fetch quotes for multiple symbols. Returns {symbol: quote_data}."""
    joined = ",".join(symbols)
    url = f"{FMP_BASE_URL}/quote/{joined}?apikey={api_key}"
    data = _get_json(url)
    if not data:
        return {}
    return {item["symbol"]: item for item in data if "symbol" in item}


def fetch_treasury(api_key: str) -> dict[str, float]:
    """Fetch latest US Treasury yields. Returns {maturity: yield}.

    Uses v4 endpoint (v3 returns empty for recent dates).
    """
    url = f"https://financialmodelingprep.com/api/v4/treasury?apikey={api_key}"
    data = _get_json(url)
    if not data:
        return {}
    latest = data[0] if isinstance(data, list) else data
    result = {}
    for key, value in latest.items():
        if key == "date":
            result["_date"] = value
            continue
        try:
            result[key] = float(value)
        except (TypeError, ValueError):
            pass
    return result


def _evaluate_vix(price: float) -> str:
    """Evaluate VIX level against Monty Style thresholds."""
    for threshold, label in THRESHOLDS["^VIX"]:
        if price >= threshold:
            return label
    return "Unknown"


def _evaluate_yield(y: float) -> str:
    """Evaluate 10Y yield against Monty Style thresholds."""
    for threshold, label in THRESHOLDS["us10y"]:
        if y >= threshold:
            return label
    return "Unknown"


def _fmt(val, fmt_str=".2f") -> str:
    """Format a numeric value, returning 'N/A' for None."""
    if val is None:
        return "N/A"
    try:
        return format(float(val), fmt_str)
    except (TypeError, ValueError):
        return str(val)


def _fmt_change(val) -> str:
    """Format change with sign."""
    if val is None:
        return "N/A"
    try:
        v = float(val)
        return f"{v:+.2f}"
    except (TypeError, ValueError):
        return str(val)


def _fmt_pct(val) -> str:
    """Format percentage change with sign."""
    if val is None:
        return "N/A"
    try:
        v = float(val)
        return f"{v:+.2f}%"
    except (TypeError, ValueError):
        return str(val)


def format_compact(quotes: dict, treasury: dict) -> str:
    """Format key indicators only (for quick checks)."""
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append(f"## Market Close ({now}, FMP API)")
    lines.append("")

    # Key indicators
    key_symbols = ["^VIX", "^GSPC", "^NDX", "^DJI", "CLUSD", "GCUSD"]
    key_names = {
        "^VIX": "VIX", "^GSPC": "S&P 500", "^NDX": "Nasdaq 100",
        "^DJI": "Dow", "CLUSD": "WTI Oil", "GCUSD": "Gold(GC)",
    }

    lines.append("| Indicator | Close | Change | %Chg | Eval |")
    lines.append("|-----------|-------|--------|------|------|")

    for sym in key_symbols:
        q = quotes.get(sym)
        if not q:
            continue
        name = key_names.get(sym, sym)
        price = q.get("price")
        evaluation = ""
        if sym == "^VIX" and price is not None:
            evaluation = _evaluate_vix(price)
        lines.append(
            f"| **{name}** | {_fmt(price)} | {_fmt_change(q.get('change'))} "
            f"| {_fmt_pct(q.get('changesPercentage'))} | {evaluation} |"
        )

    # 10Y yield
    y10 = treasury.get("year10")
    if y10 is not None:
        evaluation = _evaluate_yield(y10)
        lines.append(f"| **10Y Yield** | {y10:.3f}% | -- | -- | {evaluation} |")

    lines.append("")
    lines.append(f"*Source: FMP API. VIX discrepancy with Cboe possible (see Issue #9)*")
    return "\n".join(lines)


def format_full(quotes: dict, treasury: dict) -> str:
    """Format complete market data table."""
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"# Market Data Snapshot")
    lines.append(f"**Fetched**: {now} (local)")
    lines.append(f"**Source**: FMP API (financialmodelingprep.com)")
    lines.append("")

    def _table(title: str, symbol_list: list[tuple[str, str]]):
        lines.append(f"## {title}")
        lines.append("")
        lines.append(
            "| Indicator | Close | Change | %Chg | "
            "Day Low | Day High | Prev Close | Eval |"
        )
        lines.append(
            "|-----------|-------|--------|------|"
            "---------|----------|------------|------|"
        )
        for sym, name in symbol_list:
            q = quotes.get(sym)
            if not q:
                lines.append(f"| {name} | -- | -- | -- | -- | -- | -- | -- |")
                continue
            price = q.get("price")
            evaluation = ""
            if sym == "^VIX" and price is not None:
                evaluation = _evaluate_vix(price)
            lines.append(
                f"| **{name}** | {_fmt(price)} "
                f"| {_fmt_change(q.get('change'))} "
                f"| {_fmt_pct(q.get('changesPercentage'))} "
                f"| {_fmt(q.get('dayLow'))} "
                f"| {_fmt(q.get('dayHigh'))} "
                f"| {_fmt(q.get('previousClose'))} "
                f"| {evaluation} |"
            )
        lines.append("")

    _table("Indices & Volatility", INDICES)
    _table("Commodities", COMMODITIES)
    _table("Key ETFs", ETFS)

    # Treasury yields
    if treasury:
        lines.append("## US Treasury Yields")
        t_date = treasury.get("_date", "N/A")
        lines.append(f"*Date: {t_date}*")
        lines.append("")
        lines.append("| Maturity | Yield | Eval |")
        lines.append("|----------|-------|------|")
        for key, label in TREASURY_KEYS:
            val = treasury.get(key)
            if val is not None:
                evaluation = _evaluate_yield(val) if key == "year10" else ""
                lines.append(f"| **{label}** | {val:.3f}% | {evaluation} |")
        lines.append("")

    lines.append("---")
    lines.append(
        "*Note: FMP VIX may differ slightly from Cboe official close. "
        "For discrepancies, user-confirmed TradingView/Cboe values take "
        "priority (Issue #9 rule).*"
    )
    return "\n".join(lines)


def main():
    api_key = _load_api_key()
    if not api_key:
        print(
            "ERROR: FMP_API_KEY not found. Set in environment or .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    json_mode = "--json" in sys.argv
    compact_mode = "--compact" in sys.argv

    # Collect all symbols
    all_symbols = (
        [s for s, _ in INDICES]
        + [s for s, _ in COMMODITIES]
        + [s for s, _ in ETFS]
    )

    # Fetch data
    quotes = fetch_quotes(all_symbols, api_key)
    if not quotes:
        print("ERROR: Failed to fetch quotes from FMP", file=sys.stderr)
        sys.exit(1)

    treasury = fetch_treasury(api_key)

    # Output
    if json_mode:
        output = {
            "timestamp": datetime.now().isoformat(),
            "source": "FMP API",
            "quotes": quotes,
            "treasury": treasury,
        }
        print(json.dumps(output, indent=2, default=str))
    elif compact_mode:
        print(format_compact(quotes, treasury))
    else:
        print(format_full(quotes, treasury))

    # Print fetch summary to stderr
    fetched = len(quotes)
    total = len(all_symbols)
    missing = [s for s in all_symbols if s not in quotes]
    if missing:
        print(f"\nWARN: Missing symbols: {', '.join(missing)}", file=sys.stderr)
    print(
        f"Fetched {fetched}/{total} quotes + treasury yields", file=sys.stderr
    )


if __name__ == "__main__":
    main()
