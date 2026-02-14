"""Phase B: Trigger detection and scenario resolution (no Claude required)."""

from __future__ import annotations

import logging
from typing import Optional

from trading.core.constants import VIX_RISK_ON, VIX_CAUTION, VIX_STRESS
from trading.data.models import MarketData, StrategySpec

logger = logging.getLogger(__name__)

# Trigger type -> candidate scenario names (priority order)
TRIGGER_SCENARIO_MAP: dict[str, list[str]] = {
    "vix_stress": ["tail_risk", "bear"],
    "vix_caution": ["bear", "base"],
    "vix_risk_on": ["bull", "base"],
    "vix_caution_recover": ["base"],
    "index_stop_loss": ["bear", "tail_risk"],
    "index_buy_level": ["bull", "base"],
    "index_sell_level": ["base"],
    "drift": [],  # re-rebalance to current scenario, no scenario change
}


class TriggerMatcher:
    """Detect market triggers and resolve to blog scenarios."""

    def __init__(self, drift_threshold_pct: float = 3.0) -> None:
        self._drift_threshold = drift_threshold_pct
        self._prev_vix: Optional[float] = None

    def check(
        self,
        market_data: MarketData,
        portfolio,  # SimulatedPortfolio
        strategy: StrategySpec,
    ) -> Optional[str]:
        """Check for triggers based on end-of-day market data.

        Returns trigger type string or None.
        """
        vix = market_data.vix

        # VIX cross triggers (use strategy's thresholds if available)
        if vix is not None:
            stress_level = strategy.vix_triggers.get("stress", VIX_STRESS)
            caution_level = strategy.vix_triggers.get("caution", VIX_CAUTION)
            risk_on_level = strategy.vix_triggers.get("risk_on", VIX_RISK_ON)

            if self._prev_vix is not None:
                # Crossing up through stress
                if self._prev_vix < stress_level <= vix:
                    self._prev_vix = vix
                    return "vix_stress"

                # Crossing up through caution
                if self._prev_vix < caution_level <= vix:
                    self._prev_vix = vix
                    return "vix_caution"

                # Crossing down through risk_on
                if self._prev_vix > risk_on_level >= vix:
                    self._prev_vix = vix
                    return "vix_risk_on"

                # Crossing down through caution (recovery)
                if self._prev_vix > caution_level >= vix:
                    self._prev_vix = vix
                    return "vix_caution_recover"

            self._prev_vix = vix

        # Index level triggers
        for index_name, levels in strategy.trading_levels.items():
            index_value = market_data.get_index(index_name)
            if index_value is None:
                continue

            if levels.stop_loss and index_value <= levels.stop_loss:
                return "index_stop_loss"

            if levels.buy_level and index_value <= levels.buy_level:
                return "index_buy_level"

            if levels.sell_level and index_value >= levels.sell_level:
                return "index_sell_level"

        # Drift detection
        if hasattr(portfolio, 'get_allocation_pct'):
            current = portfolio.get_allocation_pct()
            if strategy.current_allocation and current:
                max_drift = max(
                    abs(current.get(sym, 0) - target)
                    for sym, target in strategy.current_allocation.items()
                )
                if max_drift > self._drift_threshold:
                    return "drift"

        return None

    def resolve_scenario(
        self, trigger: str, strategy: StrategySpec,
    ) -> Optional[str]:
        """Resolve trigger to a scenario name with explicit fallback chain."""
        if trigger == "drift":
            # Drift: no scenario change, just re-rebalance
            return None

        candidates = TRIGGER_SCENARIO_MAP.get(trigger, [])

        for name in candidates:
            if name in strategy.scenarios:
                return name

        # Fallback to base
        logger.warning(
            "No matching scenario for trigger=%s, candidates=%s, "
            "falling back to 'base'",
            trigger, candidates,
        )
        if "base" in strategy.scenarios:
            return "base"

        raise ValueError(
            f"No usable scenario for trigger={trigger} in blog {strategy.blog_date}"
        )
