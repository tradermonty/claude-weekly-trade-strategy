"""Kill switch — hard-halt conditions that stop all trading."""

from __future__ import annotations

import logging
from typing import Optional

from trading.config import TradingConfig
from trading.data.database import Database
from trading.data.models import MarketData, Portfolio
from trading.layer1.loss_calculator import LossCalculator

logger = logging.getLogger(__name__)


class KillSwitch:
    """Check multiple halt conditions and return the first triggered reason."""

    def __init__(self, config: TradingConfig, db: Database) -> None:
        self._config = config
        self._db = db
        self._loss_calc = LossCalculator(db)

    def check(self, market_data: MarketData, portfolio: Portfolio) -> Optional[str]:
        """Return a reason string if any halt condition is met, else None.

        Checks are evaluated in priority order; the first triggered wins.
        """
        # 1. Daily loss
        daily = self._loss_calc.daily_loss_pct(portfolio)
        if daily is not None and daily <= self._config.max_daily_loss_pct:
            logger.critical(
                "KILL SWITCH: daily loss %.2f%% exceeds limit %.2f%%",
                daily, self._config.max_daily_loss_pct,
            )
            return "daily_loss_exceeded"

        # 2. Weekly loss
        weekly = self._loss_calc.weekly_loss_pct(portfolio)
        if weekly is not None and weekly <= self._config.max_weekly_loss_pct:
            logger.critical(
                "KILL SWITCH: weekly loss %.2f%% exceeds limit %.2f%%",
                weekly, self._config.max_weekly_loss_pct,
            )
            return "weekly_loss_exceeded"

        # 3. Drawdown from HWM
        dd = self._loss_calc.drawdown_pct(portfolio)
        if dd <= self._config.max_drawdown_pct:
            logger.critical(
                "KILL SWITCH: drawdown %.2f%% exceeds limit %.2f%%",
                dd, self._config.max_drawdown_pct,
            )
            return "drawdown_exceeded"

        # 4. VIX extreme
        if market_data.vix is not None and market_data.vix > self._config.vix_extreme:
            logger.critical(
                "KILL SWITCH: VIX %.2f exceeds extreme %.2f",
                market_data.vix, self._config.vix_extreme,
            )
            return "vix_extreme"

        # 5. API consecutive failures (>=6 is HALT; 3-5 is ALERT_ONLY in rule_engine)
        failures = int(self._db.get_state("consecutive_api_failures", "0"))
        if failures >= self._config.api_fail_halt_threshold:
            logger.critical(
                "KILL SWITCH: %d consecutive API failures (halt threshold %d)",
                failures, self._config.api_fail_halt_threshold,
            )
            return "api_consecutive_failures_halt"

        return None
