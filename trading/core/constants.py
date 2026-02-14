"""Constants for the trading system — Monty Style thresholds and allowed symbols."""

from __future__ import annotations

# --- Allowed ETF Symbols ---
ALLOWED_SYMBOLS: frozenset[str] = frozenset({
    "SPY", "QQQ", "DIA",   # Core Index
    "XLV", "XLP",           # Defensive Sector
    "GLD", "XLE",           # Theme/Hedge
    "BIL", "TLT",           # Cash/Short-term & Long-term Bonds
    "URA",                   # Uranium
    "SH", "SDS",            # Inverse
})

# --- Fractional Shares Support ---
# Alpaca supports fractional shares for most US ETFs.
# If any symbol is added that doesn't support fractional, add it here.
WHOLE_SHARES_ONLY: frozenset[str] = frozenset()

# --- VIX Thresholds (Monty Style) ---
VIX_RISK_ON = 17.0
VIX_CAUTION = 20.0
VIX_STRESS = 23.0
VIX_PANIC = 26.0
VIX_EXTREME = 40.0

# --- US 10Y Yield Thresholds (Monty Style) ---
YIELD_LOWER = 4.11
YIELD_WARNING = 4.36
YIELD_RED_LINE = 4.50
YIELD_EXTREME = 4.60

# --- Breadth Thresholds (200-day MA above) ---
BREADTH_HEALTHY = 60.0
BREADTH_BORDER = 50.0
BREADTH_FRAGILE = 40.0

# --- Uptrend Ratio Thresholds ---
UPTREND_STRONG_BULLISH = 40.0
UPTREND_NEUTRAL = 25.0
UPTREND_WEAK = 15.0

# --- Index-to-ETF Mapping ---
INDEX_ETF_PAIRS: list[tuple[str, str]] = [
    ("SPY", "^GSPC"),   # S&P 500
    ("QQQ", "^NDX"),    # Nasdaq 100
    ("DIA", "^DJI"),    # Dow Jones
]

# FMP quote symbols for indices and commodities
FMP_SYMBOLS: dict[str, str] = {
    "vix": "^VIX",
    "sp500": "^GSPC",
    "nasdaq": "^NDX",
    "dow": "^DJI",
    "gold": "GCUSD",
    "oil": "CLUSD",
    "copper": "HGUSD",
}

# --- Market Data Validation Ranges ---
VALID_RANGES: dict[str, tuple[float, float]] = {
    "vix": (5.0, 90.0),
    "us10y": (0.0, 20.0),
    "sp500": (1000.0, 20000.0),
    "nasdaq": (3000.0, 50000.0),
    "dow": (10000.0, 100000.0),
    "gold": (500.0, 10000.0),
    "oil": (10.0, 200.0),
    "copper": (1.0, 20.0),
}

# --- Blog Parsing ---
# Stop-loss index names mapped to ETF symbols
INDEX_TO_ETF: dict[str, str] = {
    "sp500": "SPY",
    "nasdaq": "QQQ",
    "dow": "DIA",
    "gold": "GLD",
    "oil": "XLE",
}

# --- Scheduler ---
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0
