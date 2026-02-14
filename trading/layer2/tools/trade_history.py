"""MCP tool: get_trade_history — returns recent decisions and trades for Claude."""

from __future__ import annotations

import logging

from trading.data.database import Database

logger = logging.getLogger(__name__)


def get_trade_history(db: Database, limit: int = 20) -> dict:
    """Return recent decisions and trades as a dict for Claude.

    Parameters
    ----------
    db:
        Database instance for reading history.
    limit:
        Maximum number of records to return per category.

    Returns
    -------
    dict
        History with keys: recent_decisions, recent_trades.
    """
    decisions = db.get_recent_decisions(limit=limit)
    trades = db.get_recent_trades(limit=limit)

    return {
        "recent_decisions": decisions,
        "recent_trades": trades,
    }
