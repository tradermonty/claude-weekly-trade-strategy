"""MCP tool: get_signal_status — returns current signal state for Claude."""

from __future__ import annotations

import logging

from trading.data.database import Database

logger = logging.getLogger(__name__)


def get_signal_status(db: Database) -> dict:
    """Return current signal state as a dict for Claude.

    Parameters
    ----------
    db:
        Database instance for reading state values.

    Returns
    -------
    dict
        Signal status with keys: consecutive_api_failures,
        current_scenario, last_check_result, vix_previous.
    """
    return {
        "consecutive_api_failures": int(db.get_state("consecutive_api_failures", "0")),
        "current_scenario": db.get_state("current_scenario", "base"),
        "last_check_result": db.get_state("last_check_result", "no_action"),
        "vix_previous": _safe_float(db.get_state("vix_previous", "")),
    }


def _safe_float(val: str) -> float | None:
    """Convert a string to float, returning None on failure."""
    if not val:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
