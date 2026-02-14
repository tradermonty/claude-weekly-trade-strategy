"""Market data validation and conflict resolution."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from trading.config import TradingConfig
from trading.core.constants import VALID_RANGES

logger = logging.getLogger(__name__)


class MarketDataValidator:
    """Validates market data freshness, range, and resolves multi-source conflicts."""

    def __init__(self, config: TradingConfig) -> None:
        self._config = config
        self.consecutive_api_failures: int = 0

    # ------------------------------------------------------------------
    # Range validation
    # ------------------------------------------------------------------

    def validate(self, indicator: str, value: float) -> bool:
        """Return True if *value* falls within the known valid range for *indicator*.

        Unknown indicators are accepted by default.
        """
        bounds = VALID_RANGES.get(indicator)
        if bounds is None:
            return True
        lo, hi = bounds
        if lo <= value <= hi:
            return True
        logger.warning(
            "Validation failed: %s=%.4f outside [%.2f, %.2f]",
            indicator, value, lo, hi,
        )
        return False

    # ------------------------------------------------------------------
    # Freshness check
    # ------------------------------------------------------------------

    def is_fresh(
        self,
        source: str,
        timestamp: datetime,
        session: str = "market",
    ) -> bool:
        """Return True if *timestamp* is fresh enough for *source*.

        During ``pre_market`` session, previous-day-close data is
        considered acceptable (not stale).

        Args:
            source: One of ``"fmp_quote"``, ``"fmp_treasury"``,
                    ``"alpaca_position"``, ``"alpaca_quote"``.
            timestamp: When the data was obtained.
            session: ``"market"`` or ``"pre_market"``.
        """
        max_staleness = self._staleness_seconds(source)
        if max_staleness is None:
            return True

        age = (datetime.now() - timestamp).total_seconds()

        if session == "pre_market":
            # Before market open, previous close (up to 18 h old) is fine.
            max_staleness = max(max_staleness, 18 * 3600)

        if age <= max_staleness:
            return True

        logger.warning(
            "Stale data: source=%s age=%.0fs max=%ds",
            source, age, max_staleness,
        )
        return False

    # ------------------------------------------------------------------
    # Conflict resolution
    # ------------------------------------------------------------------

    def resolve_conflict(
        self,
        fmp_data: Optional[dict],
        alpaca_data: Optional[dict],
        previous_state: dict,
    ) -> dict:
        """Merge FMP and Alpaca data, falling back to *previous_state*.

        Priority order for each field:
          1. Alpaca (fresher for ETF prices / positions)
          2. FMP (primary source for indices, VIX, treasury)
          3. previous_state (stale fallback)

        Both sources failing increments the failure counter.
        """
        merged: dict = {}
        both_failed = fmp_data is None and alpaca_data is None

        if both_failed:
            self.consecutive_api_failures += 1
            logger.warning(
                "Both FMP and Alpaca unavailable (consecutive failures: %d)",
                self.consecutive_api_failures,
            )
            merged.update(previous_state)
            merged["_stale"] = True
            return merged

        # At least one source succeeded — reset counter.
        self.consecutive_api_failures = 0

        # FMP provides indices/commodities/VIX/treasury.
        fmp = fmp_data or {}
        # Alpaca provides ETF prices and positions.
        alpaca = alpaca_data or {}

        # Start with previous state, then layer sources.
        merged.update(previous_state)
        merged.update(fmp)
        merged.update(alpaca)  # Alpaca wins for overlapping keys
        merged["_stale"] = False

        return merged

    # ------------------------------------------------------------------
    # Failure escalation
    # ------------------------------------------------------------------

    @property
    def should_warn(self) -> bool:
        """True when consecutive failures reach the warning threshold."""
        return self.consecutive_api_failures >= self._config.api_fail_warn_threshold

    @property
    def should_halt(self) -> bool:
        """True when consecutive failures reach the halt threshold."""
        return self.consecutive_api_failures >= self._config.api_fail_halt_threshold

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _staleness_seconds(self, source: str) -> Optional[int]:
        mapping = {
            "fmp_quote": self._config.fmp_quote_max_staleness,
            "fmp_treasury": self._config.fmp_treasury_max_staleness,
            "alpaca_position": self._config.alpaca_position_max_staleness,
            "alpaca_quote": self._config.alpaca_quote_max_staleness,
        }
        return mapping.get(source)
