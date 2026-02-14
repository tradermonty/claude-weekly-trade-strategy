"""Alpaca server-side stop order management."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from trading.config import TradingConfig
from trading.core.constants import INDEX_TO_ETF
from trading.data.database import Database
from trading.data.models import Order, Portfolio, StrategySpec
from trading.services.alpaca_client import AlpacaClient
from trading.services.email_notifier import EmailNotifier

logger = logging.getLogger(__name__)


class StopLossManager:
    """Manage Alpaca server-side GTC stop orders based on blog strategy."""

    def __init__(self, config: TradingConfig, db: Database) -> None:
        self._config = config
        self._db = db
        self._alpaca = AlpacaClient(config.alpaca)
        self._notifier = EmailNotifier(config)

    def sync_stop_orders(
        self, strategy_spec: StrategySpec, portfolio: Portfolio
    ) -> None:
        """Sync stop orders for all positions based on the current strategy.

        For each position held, compute the ETF stop price from the blog's
        index-based stop levels and create/replace the server-side GTC stop.
        """
        self._cleanup_orphaned_stops(portfolio)

        for symbol, position in portfolio.positions.items():
            etf_stop = self._index_to_etf_stop(symbol, strategy_spec.stop_losses)
            if etf_stop is None:
                continue

            if etf_stop >= position.current_price:
                logger.warning(
                    "Stop price %.2f >= current price %.2f for %s, skipping",
                    etf_stop, position.current_price, symbol,
                )
                continue

            self._place_or_replace_stop(
                symbol=symbol,
                qty=position.shares,
                stop_price=etf_stop,
                blog_date=strategy_spec.blog_date,
            )

    def resync_after_fill_or_rebalance(
        self, portfolio: Portfolio, strategy_spec: StrategySpec
    ) -> None:
        """Re-sync stops after any trade or rebalance."""
        self.sync_stop_orders(strategy_spec, portfolio)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _cleanup_orphaned_stops(self, portfolio: Portfolio) -> None:
        """Cancel GTC stop orders for positions that no longer exist."""
        try:
            open_orders = self._alpaca.list_open_stop_orders()
        except Exception:
            logger.exception("Failed to list open stop orders for cleanup")
            return

        held_symbols = set(portfolio.positions.keys())

        for order in open_orders:
            if order["symbol"] not in held_symbols:
                try:
                    self._alpaca.cancel_order(order["id"])
                    logger.info(
                        "Cancelled orphaned stop order %s for %s",
                        order["id"], order["symbol"],
                    )
                except Exception:
                    logger.exception(
                        "Failed to cancel orphaned stop %s", order["id"]
                    )

    def _place_or_replace_stop(
        self, symbol: str, qty: float, stop_price: float, blog_date: str
    ) -> None:
        """Place a new stop or replace an existing one."""
        try:
            existing = self._alpaca.list_open_stop_orders(symbol)
        except Exception:
            logger.exception("Failed to list existing stops for %s", symbol)
            existing = []

        # Cancel all existing stops for this symbol
        if len(existing) >= 1:
            for order in existing:
                try:
                    self._alpaca.cancel_order(order["id"])
                    logger.info("Cancelled old stop %s for %s", order["id"], symbol)
                except Exception:
                    # Order may have been filled or already cancelled
                    logger.warning(
                        "Could not cancel stop %s for %s (may be filled/cancelled)",
                        order["id"], symbol,
                    )

        # Place new stop
        seq = self._next_seq(symbol, blog_date)
        client_order_id = f"stop-{symbol}-{blog_date}-{seq}"

        if self._config.dry_run:
            logger.info(
                "[DRY RUN] Would place stop: %s qty=%.4f stop=%.2f",
                symbol, qty, stop_price,
            )
            return

        try:
            order = Order(
                client_order_id=client_order_id,
                symbol=symbol,
                side="sell",
                quantity=qty,
                order_type="stop",
                stop_price=stop_price,
                time_in_force="gtc",
            )
            self._alpaca.submit_order(order)
            logger.info(
                "Placed stop order %s: %s qty=%.4f stop=%.2f",
                client_order_id, symbol, qty, stop_price,
            )
        except Exception:
            logger.exception("Failed to place stop order for %s", symbol)
            self._notifier.alert(
                f"Stop order failure: {symbol} at ${stop_price:.2f}"
            )

    def _index_to_etf_stop(
        self, symbol: str, stop_losses: dict[str, float]
    ) -> Optional[float]:
        """Convert an index-level stop to an ETF stop price using calibration.

        The blog specifies stops as index levels (e.g. sp500: 5800).
        We need to convert to ETF prices (e.g. SPY: 580).

        Returns None if no stop is defined or calibration is unavailable.
        """
        # Find the index name for this ETF symbol
        index_name: Optional[str] = None
        for idx, etf in INDEX_TO_ETF.items():
            if etf == symbol:
                index_name = idx
                break

        if index_name is None or index_name not in stop_losses:
            return None

        index_stop = stop_losses[index_name]

        # Get today's calibration ratio
        ratio = self._db.get_calibration(date.today(), symbol)
        if ratio is None or ratio == 0:
            logger.warning(
                "No calibration ratio for %s, cannot convert stop", symbol
            )
            return None

        return index_stop / ratio

    def _next_seq(self, symbol: str, blog_date: str) -> int:
        """Get the next stop order sequence number from DB."""
        return self._db.increment_stop_seq(symbol, blog_date)
