"""MCP tool: get_market_data — returns current market data for Claude."""

from __future__ import annotations

import logging
from typing import Any

from trading.data.database import Database

logger = logging.getLogger(__name__)


def get_market_data(db: Database, monitor: Any) -> dict:
    """Return current market data as a dict for Claude.

    Reads the latest market state from the database and merges
    with any live data available via the market monitor.

    Parameters
    ----------
    db:
        Database instance for reading stored market states.
    monitor:
        MarketMonitor instance (provides ``latest_data`` attribute
        with a :class:`MarketData` object).

    Returns
    -------
    dict
        Market data with keys: vix, us10y, sp500, nasdaq, dow,
        gold, oil, copper, etf_prices.
    """
    result: dict[str, Any] = {
        "vix": None,
        "us10y": None,
        "sp500": None,
        "nasdaq": None,
        "dow": None,
        "gold": None,
        "oil": None,
        "copper": None,
        "etf_prices": {},
    }

    # Try monitor's latest data first (most fresh)
    if monitor is not None and hasattr(monitor, "latest_data") and monitor.latest_data is not None:
        md = monitor.latest_data
        result["vix"] = md.vix
        result["us10y"] = md.us10y
        result["sp500"] = md.sp500
        result["nasdaq"] = md.nasdaq
        result["dow"] = md.dow
        result["gold"] = md.gold
        result["oil"] = md.oil
        result["copper"] = md.copper
        result["etf_prices"] = dict(md.etf_prices) if md.etf_prices else {}
        return result

    # Fallback to database stored values
    for key in ("vix", "us10y", "sp500", "nasdaq", "dow", "gold", "oil"):
        val = db.get_previous_market_state(key)
        if val is not None:
            result[key] = val

    return result
