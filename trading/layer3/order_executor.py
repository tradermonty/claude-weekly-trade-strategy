"""Order execution via Alpaca for Layer 3."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from trading.config import TradingConfig
from trading.data.database import Database
from trading.data.models import Order
from trading.services.alpaca_client import AlpacaClient

logger = logging.getLogger(__name__)


class OrderExecutor:
    """Executes orders via Alpaca and logs results to the database.

    In dry_run mode, orders are logged but not actually submitted.
    """

    def __init__(self, config: TradingConfig, db: Database) -> None:
        self._config = config
        self._db = db
        self._client: Optional[AlpacaClient] = None

    def _get_client(self) -> AlpacaClient:
        """Lazy-init Alpaca client."""
        if self._client is None:
            self._client = AlpacaClient(self._config.alpaca)
        return self._client

    def execute(self, orders: list[Order]) -> list[dict]:
        """Submit orders to Alpaca and log to database.

        Parameters
        ----------
        orders:
            List of orders to execute.

        Returns
        -------
        list[dict]
            Results with keys: client_order_id, order_id, status, filled_price.
        """
        results: list[dict] = []

        for order in orders:
            if self._config.dry_run:
                result = self._dry_run_order(order)
            else:
                result = self._live_order(order)
            results.append(result)

        return results

    def _dry_run_order(self, order: Order) -> dict:
        """Log order without submitting to Alpaca."""
        logger.info(
            "[DRY RUN] %s %s %.6f shares of %s @ limit $%.2f (id: %s)",
            order.side.upper(),
            order.order_type,
            order.quantity,
            order.symbol,
            order.limit_price or 0,
            order.client_order_id,
        )

        self._db.save_trade(
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            status="dry_run",
            filled_price=order.limit_price,
            filled_at=datetime.now(timezone.utc).isoformat(),
        )

        return {
            "client_order_id": order.client_order_id,
            "order_id": None,
            "status": "dry_run",
            "filled_price": order.limit_price,
        }

    def _live_order(self, order: Order) -> dict:
        """Submit order to Alpaca."""
        client = self._get_client()

        logger.info(
            "Submitting %s %s %.6f shares of %s @ limit $%.2f (id: %s)",
            order.side.upper(),
            order.order_type,
            order.quantity,
            order.symbol,
            order.limit_price or 0,
            order.client_order_id,
        )

        # Save pending trade first
        self._db.save_trade(
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            status="submitted",
        )

        result = client.submit_order(order)
        if result is None:
            logger.error("Order submission failed for %s", order.client_order_id)
            self._db.update_trade_status(order.client_order_id, "failed")
            return {
                "client_order_id": order.client_order_id,
                "order_id": None,
                "status": "failed",
                "filled_price": None,
            }

        order_id = result.get("id")
        status = result.get("status", "unknown")
        filled_price_str = result.get("filled_avg_price")
        filled_price = float(filled_price_str) if filled_price_str else None

        self._db.update_trade_status(
            order.client_order_id,
            status,
            filled_price=filled_price,
            filled_at=result.get("created_at"),
        )

        return {
            "client_order_id": order.client_order_id,
            "order_id": order_id,
            "status": status,
            "filled_price": filled_price,
        }

    def check_fill_status(self, client_order_id: str) -> dict:
        """Check if an order has been filled.

        Parameters
        ----------
        client_order_id:
            The client order ID to check.

        Returns
        -------
        dict
            Order status with keys: client_order_id, status, filled_price.
        """
        client = self._get_client()

        # Alpaca's get_order expects their internal ID, but we use client_order_id.
        # We search through recent orders.
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus

            req = GetOrdersRequest(status=QueryOrderStatus.ALL)
            orders = client._trading.get_orders(req)
            for o in orders:
                if o.client_order_id == client_order_id:
                    filled_price = float(o.filled_avg_price) if o.filled_avg_price else None
                    status = str(o.status)

                    if filled_price is not None:
                        self._db.update_trade_status(
                            client_order_id,
                            status,
                            filled_price=filled_price,
                            filled_at=str(o.filled_at) if o.filled_at else None,
                        )

                    return {
                        "client_order_id": client_order_id,
                        "status": status,
                        "filled_price": filled_price,
                    }
        except Exception:
            logger.exception("Error checking fill status for %s", client_order_id)

        return {
            "client_order_id": client_order_id,
            "status": "unknown",
            "filled_price": None,
        }

    def wait_for_fills(
        self,
        order_ids: list[str],
        timeout_seconds: int = 60,
    ) -> list[dict]:
        """Poll for order fills until timeout.

        Parameters
        ----------
        order_ids:
            List of client_order_id values to monitor.
        timeout_seconds:
            Maximum seconds to wait.

        Returns
        -------
        list[dict]
            Final status for each order.
        """
        pending = set(order_ids)
        results: dict[str, dict] = {}
        deadline = time.time() + timeout_seconds

        while pending and time.time() < deadline:
            for oid in list(pending):
                status = self.check_fill_status(oid)
                results[oid] = status
                if status["status"] in ("filled", "cancelled", "expired", "failed", "rejected"):
                    pending.discard(oid)

            if pending:
                time.sleep(2)

        # Mark remaining as timed out
        for oid in pending:
            if oid not in results:
                results[oid] = {
                    "client_order_id": oid,
                    "status": "timeout",
                    "filled_price": None,
                }

        return [results[oid] for oid in order_ids if oid in results]
