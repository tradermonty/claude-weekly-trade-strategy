"""15-minute interval rule engine — Layer 1 orchestrator."""

from __future__ import annotations

import logging
from typing import Optional

from trading.config import TradingConfig
from trading.core.constants import VIX_RISK_ON, VIX_CAUTION, VIX_STRESS, VIX_PANIC
from trading.data.database import Database
from trading.data.models import CheckResult, MarketData, Portfolio, StrategySpec
from trading.layer1.kill_switch import KillSwitch
from trading.services.alpaca_client import AlpacaClient
from trading.services.email_notifier import EmailNotifier

logger = logging.getLogger(__name__)

VIX_THRESHOLDS = [VIX_RISK_ON, VIX_CAUTION, VIX_STRESS, VIX_PANIC]


class RuleEngine:
    """Evaluate market conditions every 15 minutes and return a CheckResult."""

    def __init__(self, config: TradingConfig, db: Database) -> None:
        self._config = config
        self._db = db
        self._kill_switch = KillSwitch(config, db)
        self._alpaca = AlpacaClient(config.alpaca)
        self._notifier = EmailNotifier(config)

    def check(
        self,
        market_data: MarketData,
        portfolio: Portfolio,
        strategy_spec: StrategySpec,
    ) -> CheckResult:
        """Run all rule checks in priority order.

        Returns the first triggered result:
          1. Kill switch          -> HALT
          2. Stop order fills     -> STOP_TRIGGERED
          3. API failure alert    -> TRIGGER_FIRED (alert only)
          4. VIX threshold cross  -> TRIGGER_FIRED
          5. Index hit level      -> TRIGGER_FIRED
          6. Portfolio drift      -> TRIGGER_FIRED
          7. None of the above    -> NO_ACTION
        """
        # 1. Kill switch
        halt_reason = self._kill_switch.check(market_data, portfolio)
        if halt_reason is not None:
            self._db.log_decision(
                timestamp=market_data.timestamp.isoformat(),
                run_id=None,
                trigger_type="kill_switch",
                result="HALT",
                rationale=halt_reason,
            )
            self._notifier.critical(
                f"KILL SWITCH: {halt_reason}. Trading halted."
            )
            return CheckResult.HALT(halt_reason)

        # 2. Stop order fills
        fill_info = self.check_stop_order_fills()
        if fill_info is not None:
            self._notifier.alert(
                f"Stop triggered: {fill_info.get('symbol', '?')}. Details: {fill_info}"
            )
            return CheckResult.STOP_TRIGGERED(fill_info)

        # 3. API failure alert (3-5 consecutive failures)
        if self.api_failure_alert_needed():
            failures = int(self._db.get_state("consecutive_api_failures", "0"))
            logger.warning("API failure alert: %d consecutive failures", failures)
            self._notifier.alert(
                f"API Alert: {failures} consecutive failures. "
                f"Halt at {self._config.api_fail_halt_threshold}."
            )
            return CheckResult.TRIGGER_FIRED(
                f"api_failure_alert ({failures} consecutive)"
            )

        # 4. VIX threshold cross
        if self.vix_crossed_threshold(market_data):
            return CheckResult.TRIGGER_FIRED("vix_threshold_crossed")

        # 5. Index hit trading level
        if self.index_hit_level(market_data, strategy_spec):
            return CheckResult.TRIGGER_FIRED("index_hit_level")

        # 6. Portfolio drift
        if self.drift_exceeded(portfolio, strategy_spec):
            return CheckResult.TRIGGER_FIRED("portfolio_drift_exceeded")

        return CheckResult.NO_ACTION()

    def vix_crossed_threshold(self, market_data: MarketData) -> bool:
        """Check if VIX crossed any standard threshold since last check."""
        if market_data.vix is None:
            return False

        prev_vix = self._db.get_previous_market_state("vix")
        if prev_vix is None:
            return False

        current = market_data.vix
        previous = prev_vix

        for threshold in VIX_THRESHOLDS:
            crossed_up = previous < threshold <= current
            crossed_down = previous >= threshold > current
            if crossed_up or crossed_down:
                direction = "UP" if crossed_up else "DOWN"
                logger.info(
                    "VIX crossed %.1f %s: %.2f -> %.2f",
                    threshold, direction, previous, current,
                )
                return True

        return False

    def index_hit_level(
        self, market_data: MarketData, strategy_spec: StrategySpec
    ) -> bool:
        """Check if any index hit a buy/sell/stop level from the blog."""
        for index_name, levels in strategy_spec.trading_levels.items():
            current = market_data.get_index(index_name)
            if current is None:
                continue

            if levels.buy_level is not None and current <= levels.buy_level:
                logger.info(
                    "%s hit buy level: %.2f <= %.2f",
                    index_name, current, levels.buy_level,
                )
                return True

            if levels.sell_level is not None and current >= levels.sell_level:
                logger.info(
                    "%s hit sell level: %.2f >= %.2f",
                    index_name, current, levels.sell_level,
                )
                return True

            if levels.stop_loss is not None and current <= levels.stop_loss:
                logger.info(
                    "%s hit stop level: %.2f <= %.2f",
                    index_name, current, levels.stop_loss,
                )
                return True

        return False

    def drift_exceeded(
        self,
        portfolio: Portfolio,
        strategy_spec: StrategySpec,
        threshold: float = 3.0,
    ) -> bool:
        """Check if any position deviates more than threshold% from target."""
        target_alloc = strategy_spec.current_allocation

        for symbol, target_pct in target_alloc.items():
            actual_pct = portfolio.get_position_pct(symbol)
            if abs(actual_pct - target_pct) > threshold:
                logger.info(
                    "Drift: %s actual=%.1f%% target=%.1f%% (diff=%.1f%%)",
                    symbol, actual_pct, target_pct, abs(actual_pct - target_pct),
                )
                return True

        # Also check for positions not in the target (should be 0%)
        for symbol in portfolio.positions:
            if symbol not in target_alloc:
                actual_pct = portfolio.get_position_pct(symbol)
                if actual_pct > threshold:
                    logger.info(
                        "Drift: %s actual=%.1f%% not in target allocation",
                        symbol, actual_pct,
                    )
                    return True

        return False

    def check_stop_order_fills(self) -> Optional[dict]:
        """Check if any GTC stop orders have been filled on Alpaca.

        Returns fill details dict if a stop was filled, None otherwise.
        """
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus, OrderType

            req = GetOrdersRequest(status=QueryOrderStatus.CLOSED)
            orders = self._alpaca._trading.get_orders(req)

            for o in orders:
                if o.order_type != OrderType.STOP:
                    continue
                cid = o.client_order_id or ""
                if not cid.startswith("stop-"):
                    continue
                if str(o.status) != "filled":
                    continue

                state_key = f"stop_fill_processed_{cid}"
                if self._db.get_state(state_key, "0") == "1":
                    continue

                self._db.set_state(state_key, "1")
                filled_price = float(o.filled_avg_price) if o.filled_avg_price else None
                logger.info(
                    "Stop order filled: %s %s at %s",
                    o.symbol, cid, filled_price,
                )
                return {
                    "symbol": o.symbol,
                    "order_id": cid,
                    "filled_price": filled_price,
                    "qty": str(o.qty) if o.qty else None,
                }
        except Exception:
            logger.exception("Failed to check stop order fills")

        return None

    def api_failure_alert_needed(self) -> bool:
        """Return True if consecutive API failures >= warn threshold (3-5)."""
        failures = int(self._db.get_state("consecutive_api_failures", "0"))
        return failures >= self._config.api_fail_warn_threshold
