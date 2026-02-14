"""Order validation for Layer 3."""

from __future__ import annotations

import logging
from datetime import date

from trading.config import TradingConfig
from trading.core.constants import ALLOWED_SYMBOLS
from trading.data.database import Database
from trading.data.models import Portfolio, StrategyIntent, StrategySpec, ValidationResult

logger = logging.getLogger(__name__)


class OrderValidator:
    """Validates strategy intent before order generation.

    Checks symbol allowlist, scenario validity, allocation deviation,
    pre-event freeze, daily limits, and allocation totals.
    """

    def __init__(self, config: TradingConfig, db: Database) -> None:
        self._config = config
        self._db = db

    def validate(
        self,
        intent: StrategyIntent,
        strategy_spec: StrategySpec,
        portfolio: Portfolio,
    ) -> ValidationResult:
        """Validate a strategy intent against rules.

        Checks are performed in order; all errors are collected.

        Parameters
        ----------
        intent:
            Strategy intent from Claude agent.
        strategy_spec:
            Parsed strategy from the blog.
        portfolio:
            Current portfolio state.

        Returns
        -------
        ValidationResult
            APPROVED if all checks pass, REJECTED with error list otherwise.
        """
        errors: list[str] = []

        # 1. All symbols in ALLOWED_SYMBOLS
        unknown = set(intent.target_allocation.keys()) - ALLOWED_SYMBOLS
        if unknown:
            errors.append(f"Unknown symbols: {sorted(unknown)}")

        # 2. Scenario exists in strategy_spec
        if intent.scenario not in strategy_spec.scenarios:
            errors.append(
                f"Scenario '{intent.scenario}' not found in strategy. "
                f"Available: {sorted(strategy_spec.scenarios.keys())}"
            )
            # Early return — cannot validate allocation against non-existent scenario
            return ValidationResult.REJECTED(errors)

        # 3. Each symbol within ±max_deviation_pct of scenario allocation
        scenario_alloc = strategy_spec.get_scenario_allocation(intent.scenario)
        for symbol, target_pct in intent.target_allocation.items():
            if symbol not in ALLOWED_SYMBOLS:
                continue  # Already caught in check 1
            expected = scenario_alloc.get(symbol, 0.0)
            deviation = abs(target_pct - expected)
            if deviation > self._config.max_deviation_pct:
                errors.append(
                    f"{symbol}: target {target_pct:.1f}% deviates {deviation:.1f}% "
                    f"from scenario '{intent.scenario}' allocation {expected:.1f}% "
                    f"(max ±{self._config.max_deviation_pct}%)"
                )

        # 4. Pre-event freeze
        if self.is_pre_event_freeze(strategy_spec):
            current_scenario = self._db.get_state("current_scenario", "base")
            if intent.scenario != current_scenario:
                errors.append(
                    f"Pre-event freeze active: cannot change scenario from "
                    f"'{current_scenario}' to '{intent.scenario}'"
                )

        # 5. Daily order count
        today_orders = self._db.count_today_orders()
        if today_orders >= self._config.max_daily_orders:
            errors.append(
                f"Daily order limit reached: {today_orders}/{self._config.max_daily_orders}"
            )

        # 6. Daily turnover
        if portfolio.account_value > 0:
            today_turnover = self._db.get_today_turnover()
            today_turnover_pct = (today_turnover / portfolio.account_value) * 100
            # Estimate planned turnover
            planned_turnover = self._estimate_turnover(intent, portfolio)
            planned_pct = (planned_turnover / portfolio.account_value) * 100
            total_pct = today_turnover_pct + planned_pct
            if total_pct > self._config.max_daily_turnover_pct:
                errors.append(
                    f"Daily turnover would exceed limit: "
                    f"{total_pct:.1f}% > {self._config.max_daily_turnover_pct}%"
                )

        # 7. Single order size check
        if portfolio.account_value > 0:
            for symbol, target_pct in intent.target_allocation.items():
                current_pct = portfolio.get_position_pct(symbol)
                change_pct = abs(target_pct - current_pct)
                if change_pct > self._config.max_single_order_pct:
                    errors.append(
                        f"{symbol}: single order {change_pct:.1f}% exceeds "
                        f"max {self._config.max_single_order_pct}%"
                    )

        # 8. Total allocation ≈ 100%
        total = sum(intent.target_allocation.values())
        if abs(total - 100.0) > 0.5:
            errors.append(
                f"Total allocation {total:.1f}% is not ~100% (tolerance ±0.5%)"
            )

        if errors:
            logger.warning("Validation rejected: %s", errors)
            return ValidationResult.REJECTED(errors)

        logger.info("Validation approved for scenario '%s'", intent.scenario)
        return ValidationResult.APPROVED()

    def is_pre_event_freeze(self, strategy_spec: StrategySpec) -> bool:
        """Check if today is in the pre-event freeze dates.

        Parameters
        ----------
        strategy_spec:
            Strategy spec containing pre_event_dates.

        Returns
        -------
        bool
            True if today is a pre-event freeze date.
        """
        today_str = date.today().isoformat()
        return today_str in strategy_spec.pre_event_dates

    def _estimate_turnover(self, intent: StrategyIntent, portfolio: Portfolio) -> float:
        """Estimate planned turnover in dollar terms."""
        total = 0.0
        for symbol, target_pct in intent.target_allocation.items():
            target_value = portfolio.account_value * target_pct / 100.0
            current_value = 0.0
            if symbol in portfolio.positions:
                current_value = portfolio.positions[symbol].market_value
            total += abs(target_value - current_value)
        return total
