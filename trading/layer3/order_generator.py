"""Deterministic order generation for Layer 3."""

from __future__ import annotations

import logging
import math
from datetime import date

from trading.config import TradingConfig
from trading.core.constants import WHOLE_SHARES_ONLY
from trading.data.models import Order, Portfolio, StrategyIntent

logger = logging.getLogger(__name__)


class OrderGenerator:
    """Generates concrete orders from a validated strategy intent.

    Converts target allocation percentages into buy/sell limit orders,
    respecting minimum trade thresholds and fractional share rules.
    """

    def __init__(self, config: TradingConfig) -> None:
        self._config = config

    def generate(
        self,
        intent: StrategyIntent,
        portfolio: Portfolio,
        prices: dict[str, float],
    ) -> list[Order]:
        """Generate orders from intent, portfolio state, and current prices.

        Parameters
        ----------
        intent:
            Validated strategy intent with target allocation.
        portfolio:
            Current portfolio state.
        prices:
            Current prices keyed by symbol.

        Returns
        -------
        list[Order]
            Orders sorted: sells first (free up cash), then buys.
        """
        sells: list[Order] = []
        buys: list[Order] = []

        for symbol, target_pct in intent.target_allocation.items():
            price = prices.get(symbol)
            if price is None or price <= 0:
                logger.warning("No price for %s, skipping", symbol)
                continue

            target_value = portfolio.account_value * target_pct / 100.0
            current_value = 0.0
            current_shares = 0.0
            if symbol in portfolio.positions:
                current_value = portfolio.positions[symbol].market_value
                current_shares = portfolio.positions[symbol].shares

            delta = target_value - current_value
            min_threshold = max(
                portfolio.account_value * self._config.min_trade_pct / 100.0,
                self._config.min_trade_usd,
            )

            if abs(delta) < min_threshold:
                continue

            # Calculate shares
            raw_shares = abs(delta) / price
            if not self._supports_fractional(symbol):
                raw_shares = math.floor(raw_shares)
                if raw_shares < 1:
                    continue

            shares = round(raw_shares, 6)
            if shares <= 0:
                continue

            client_order_id = self._generate_client_order_id(symbol, intent)

            if delta > 0:
                # Buy
                order = Order(
                    client_order_id=client_order_id,
                    symbol=symbol,
                    side="buy",
                    quantity=shares,
                    order_type="limit",
                    limit_price=self._calc_limit_price(price, "buy"),
                    time_in_force="day",
                )
                buys.append(order)
            else:
                # Sell — don't sell more than we hold
                sell_shares = min(shares, current_shares)
                if sell_shares <= 0:
                    continue
                order = Order(
                    client_order_id=client_order_id,
                    symbol=symbol,
                    side="sell",
                    quantity=round(sell_shares, 6),
                    order_type="limit",
                    limit_price=self._calc_limit_price(price, "sell"),
                    time_in_force="day",
                )
                sells.append(order)

        # Also generate sell orders for positions not in target allocation
        for symbol in portfolio.positions:
            if symbol not in intent.target_allocation:
                pos = portfolio.positions[symbol]
                price = prices.get(symbol)
                if price is None or price <= 0:
                    continue
                if pos.shares <= 0:
                    continue

                client_order_id = self._generate_client_order_id(symbol, intent)
                order = Order(
                    client_order_id=client_order_id,
                    symbol=symbol,
                    side="sell",
                    quantity=round(pos.shares, 6),
                    order_type="limit",
                    limit_price=self._calc_limit_price(price, "sell"),
                    time_in_force="day",
                )
                sells.append(order)

        # Sells first (free up cash), then buys
        return sells + buys

    def _generate_client_order_id(self, symbol: str, intent: StrategyIntent) -> str:
        """Generate idempotent client order ID.

        Format: {YYYYMMDD}_{run_id}_{symbol}_{scenario}
        """
        today = date.today().strftime("%Y%m%d")
        return f"{today}_{intent.run_id}_{symbol}_{intent.scenario}"

    def _calc_limit_price(self, price: float, side: str) -> float:
        """Calculate limit price with small buffer.

        Buy: price * 1.001 (0.1% above market)
        Sell: price * 0.999 (0.1% below market)
        """
        if side == "buy":
            return round(price * 1.001, 2)
        return round(price * 0.999, 2)

    def _supports_fractional(self, symbol: str) -> bool:
        """Check if symbol supports fractional shares."""
        return symbol not in WHOLE_SHARES_ONLY
