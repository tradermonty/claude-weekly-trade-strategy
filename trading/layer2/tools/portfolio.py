"""MCP tool: get_portfolio_state — returns current portfolio for Claude."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_portfolio_state(client: Any) -> dict:
    """Return current portfolio state as a dict for Claude.

    Parameters
    ----------
    client:
        AlpacaClient instance (provides ``get_portfolio()``).

    Returns
    -------
    dict
        Portfolio data with keys: account_value, cash, positions.
        Each position has: symbol, shares, market_value, pct.
    """
    result: dict[str, Any] = {
        "account_value": 0.0,
        "cash": 0.0,
        "positions": [],
    }

    portfolio = client.get_portfolio()
    if portfolio is None:
        logger.warning("Could not retrieve portfolio from Alpaca")
        return result

    result["account_value"] = portfolio.account_value
    result["cash"] = portfolio.cash

    positions = []
    for symbol, pos in portfolio.positions.items():
        pct = 0.0
        if portfolio.account_value > 0:
            pct = round((pos.market_value / portfolio.account_value) * 100, 2)
        positions.append({
            "symbol": symbol,
            "shares": pos.shares,
            "market_value": round(pos.market_value, 2),
            "pct": pct,
        })

    # Sort by market value descending for readability
    positions.sort(key=lambda p: p["market_value"], reverse=True)
    result["positions"] = positions

    return result
