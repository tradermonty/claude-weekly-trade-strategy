"""Loss calculation: daily, weekly, and drawdown from HWM."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from trading.data.database import Database
from trading.data.models import Portfolio

logger = logging.getLogger(__name__)


class LossCalculator:
    """Compute portfolio losses relative to daily/weekly snapshots and HWM."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def daily_loss_pct(self, portfolio: Portfolio) -> Optional[float]:
        """Return daily P&L percentage, or None if no snapshot exists yet."""
        snapshot = self._db.get_opening_snapshot(date.today())
        if snapshot is None:
            return None
        if snapshot.account_value == 0:
            return None
        return (portfolio.account_value - snapshot.account_value) / snapshot.account_value * 100.0

    def weekly_loss_pct(self, portfolio: Portfolio) -> Optional[float]:
        """Return weekly P&L percentage, or None if no snapshot exists yet."""
        snapshot = self._db.get_week_opening_snapshot()
        if snapshot is None:
            return None
        if snapshot.account_value == 0:
            return None
        return (portfolio.account_value - snapshot.account_value) / snapshot.account_value * 100.0

    def drawdown_pct(self, portfolio: Portfolio) -> float:
        """Return drawdown from HWM. Always valid (0.0 if HWM is zero)."""
        hwm = self._db.get_high_water_mark()
        if hwm <= 0:
            return 0.0
        return (portfolio.account_value - hwm) / hwm * 100.0

    def update_hwm_if_needed(self, portfolio: Portfolio) -> None:
        """Update the high-water mark if current value exceeds it."""
        self._db.update_high_water_mark(portfolio.account_value)

    def create_daily_snapshot(self, portfolio: Portfolio) -> None:
        """Save daily open snapshot (called at 9:30 ET first check)."""
        today = date.today()
        self._db.save_opening_snapshot("daily_open", today, portfolio.account_value)
        logger.info("Daily snapshot saved: date=%s value=%.2f", today, portfolio.account_value)

    def create_weekly_snapshot(self, portfolio: Portfolio) -> None:
        """Save weekly open snapshot (called on Monday 9:30 ET)."""
        today = date.today()
        self._db.save_opening_snapshot("weekly_open", today, portfolio.account_value)
        logger.info("Weekly snapshot saved: date=%s value=%.2f", today, portfolio.account_value)
