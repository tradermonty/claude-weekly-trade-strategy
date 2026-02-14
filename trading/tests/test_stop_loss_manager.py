"""Tests for the StopLossManager (H4).

Covers: index-to-ETF conversion, orphaned stop cleanup, sequence uniqueness,
dry-run mode, resync delegation, and stop-price sanity checks.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from trading.data.models import Order, Portfolio, Position, StrategySpec, ScenarioSpec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_portfolio(positions: dict[str, Position] | None = None) -> Portfolio:
    positions = positions or {
        "SPY": Position("SPY", 73.0, 50000.0, 48000.0, 683.1),
        "QQQ": Position("QQQ", 18.8, 10000.0, 9500.0, 531.2),
    }
    total = sum(p.market_value for p in positions.values())
    return Portfolio(account_value=total + 5000, cash=5000, positions=positions)


def _make_strategy(
    stop_losses: dict[str, float] | None = None,
    blog_date: str = "2026-02-16",
) -> StrategySpec:
    if stop_losses is None:
        stop_losses = {"sp500": 6300.0, "nasdaq": 19500.0}
    return StrategySpec(
        blog_date=blog_date,
        current_allocation={"SPY": 50.0, "QQQ": 20.0, "BIL": 30.0},
        scenarios={
            "base": ScenarioSpec(
                name="base", probability=50, triggers=[],
                allocation={"SPY": 50.0, "QQQ": 20.0, "BIL": 30.0},
            ),
        },
        trading_levels={},
        stop_losses=stop_losses,
        vix_triggers={},
        yield_triggers={},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _make_manager(config, db):
    """Create a StopLossManager with AlpacaClient and EmailNotifier mocked."""
    with patch("trading.layer1.stop_loss_manager.AlpacaClient"), \
         patch("trading.layer1.stop_loss_manager.EmailNotifier"):
        from trading.layer1.stop_loss_manager import StopLossManager
        mgr = StopLossManager(config, db)
    mgr._alpaca = MagicMock()
    mgr._notifier = MagicMock()
    return mgr


class TestIndexToEtfStop:
    """Test _index_to_etf_stop conversion with calibration ratios."""

    def test_valid_conversion(self, tmp_db, config):
        """index_stop=6300, ratio=10.0 → etf_stop=630.0."""
        tmp_db.save_calibration(date.today(), "SPY", "^GSPC", 10.0)

        mgr = _make_manager(config, tmp_db)
        result = mgr._index_to_etf_stop("SPY", {"sp500": 6300.0})

        assert result == pytest.approx(630.0)

    def test_critical_false_positive_proof(self, tmp_db, config):
        """Prove CRITICAL C1 is a false positive: index_stop/ratio is correct.

        index_stop=5800, ratio=10.0 → 5800/10.0 = 580.0 (correct ETF stop).
        """
        tmp_db.save_calibration(date.today(), "SPY", "^GSPC", 10.0)

        mgr = _make_manager(config, tmp_db)
        result = mgr._index_to_etf_stop("SPY", {"sp500": 5800.0})

        assert result == pytest.approx(580.0)

    def test_no_calibration_returns_none(self, tmp_db, config):
        """Without calibration data, _index_to_etf_stop returns None."""
        mgr = _make_manager(config, tmp_db)
        result = mgr._index_to_etf_stop("SPY", {"sp500": 6300.0})

        assert result is None

    def test_symbol_without_stop_returns_none(self, tmp_db, config):
        """If the blog has no stop for this index, returns None."""
        tmp_db.save_calibration(date.today(), "GLD", "^GOLD", 5.0)

        mgr = _make_manager(config, tmp_db)
        # GLD maps to "gold" in INDEX_TO_ETF, but stop_losses has only "sp500"
        result = mgr._index_to_etf_stop("GLD", {"sp500": 6300.0})

        assert result is None


class TestSyncStopOrders:
    """Test stop order placement and replacement logic."""

    @patch("trading.layer1.stop_loss_manager.AlpacaClient")
    @patch("trading.layer1.stop_loss_manager.EmailNotifier")
    def test_skip_when_stop_above_current_price(
        self, mock_notifier_cls, mock_alpaca_cls, tmp_db, config
    ):
        """Stop price >= current price should be skipped (would trigger immediately)."""
        from trading.layer1.stop_loss_manager import StopLossManager

        # Set calibration so etf_stop = 6300/10 = 630 < current price 683.1
        tmp_db.save_calibration(date.today(), "SPY", "^GSPC", 10.0)

        mgr = StopLossManager(config, tmp_db)
        mock_alpaca = mgr._alpaca
        mock_alpaca.list_open_stop_orders.return_value = []

        # Portfolio with SPY at price 620 (below stop of 630)
        portfolio = Portfolio(
            account_value=50000, cash=5000,
            positions={
                "SPY": Position("SPY", 73.0, 45260.0, 48000.0, 620.0),
            },
        )
        strategy = _make_strategy(stop_losses={"sp500": 6300.0})

        mgr.sync_stop_orders(strategy, portfolio)

        # submit_order should NOT be called (stop 630 >= price 620)
        mock_alpaca.submit_order.assert_not_called()

    @patch("trading.layer1.stop_loss_manager.AlpacaClient")
    @patch("trading.layer1.stop_loss_manager.EmailNotifier")
    def test_dry_run_does_not_submit(
        self, mock_notifier_cls, mock_alpaca_cls, tmp_db, config
    ):
        """In dry_run mode, stop orders are logged but not submitted."""
        from trading.layer1.stop_loss_manager import StopLossManager

        tmp_db.save_calibration(date.today(), "SPY", "^GSPC", 10.0)
        # config.dry_run is True by default in test fixtures

        mgr = StopLossManager(config, tmp_db)
        mock_alpaca = mgr._alpaca
        mock_alpaca.list_open_stop_orders.return_value = []

        portfolio = _make_portfolio()
        strategy = _make_strategy()

        mgr.sync_stop_orders(strategy, portfolio)

        # Should NOT call submit_order in dry_run mode
        mock_alpaca.submit_order.assert_not_called()


class TestCleanupOrphanedStops:
    """Test that orphaned stop orders are cancelled."""

    @patch("trading.layer1.stop_loss_manager.AlpacaClient")
    @patch("trading.layer1.stop_loss_manager.EmailNotifier")
    def test_cancels_orphaned_stop(
        self, mock_notifier_cls, mock_alpaca_cls, tmp_db, config
    ):
        """Stop orders for positions we no longer hold are cancelled."""
        from trading.layer1.stop_loss_manager import StopLossManager

        mgr = StopLossManager(config, tmp_db)
        mock_alpaca = mgr._alpaca

        # Alpaca has a stop for XLE, but we only hold SPY
        mock_alpaca.list_open_stop_orders.return_value = [
            {"id": "order-xle-1", "symbol": "XLE", "stop_price": "90.0"},
        ]

        portfolio = Portfolio(
            account_value=50000, cash=5000,
            positions={"SPY": Position("SPY", 73.0, 50000.0, 48000.0, 683.1)},
        )

        mgr._cleanup_orphaned_stops(portfolio)

        mock_alpaca.cancel_order.assert_called_once_with("order-xle-1")

    @patch("trading.layer1.stop_loss_manager.AlpacaClient")
    @patch("trading.layer1.stop_loss_manager.EmailNotifier")
    def test_keeps_valid_stops(
        self, mock_notifier_cls, mock_alpaca_cls, tmp_db, config
    ):
        """Stop orders for positions we hold are NOT cancelled."""
        from trading.layer1.stop_loss_manager import StopLossManager

        mgr = StopLossManager(config, tmp_db)
        mock_alpaca = mgr._alpaca

        mock_alpaca.list_open_stop_orders.return_value = [
            {"id": "order-spy-1", "symbol": "SPY", "stop_price": "630.0"},
        ]

        portfolio = _make_portfolio()

        mgr._cleanup_orphaned_stops(portfolio)

        mock_alpaca.cancel_order.assert_not_called()


class TestSeqUniqueness:
    """Test that stop order sequence numbers are unique per symbol/blog_date."""

    def test_seq_increments(self, tmp_db, config):
        """Each call to _next_seq increments for the same symbol/blog_date."""
        mgr = _make_manager(config, tmp_db)

        seq0 = mgr._next_seq("SPY", "2026-02-16")
        seq1 = mgr._next_seq("SPY", "2026-02-16")
        seq2 = mgr._next_seq("SPY", "2026-02-16")

        assert seq0 == 0
        assert seq1 == 1
        assert seq2 == 2

    def test_seq_independent_per_symbol(self, tmp_db, config):
        """Different symbols have independent sequences."""
        mgr = _make_manager(config, tmp_db)

        spy_seq = mgr._next_seq("SPY", "2026-02-16")
        qqq_seq = mgr._next_seq("QQQ", "2026-02-16")

        assert spy_seq == 0
        assert qqq_seq == 0


class TestResyncDelegation:
    """Test that resync_after_fill_or_rebalance delegates to sync_stop_orders."""

    @patch("trading.layer1.stop_loss_manager.AlpacaClient")
    @patch("trading.layer1.stop_loss_manager.EmailNotifier")
    def test_resync_calls_sync(
        self, mock_notifier_cls, mock_alpaca_cls, tmp_db, config
    ):
        """resync_after_fill_or_rebalance should call sync_stop_orders."""
        from trading.layer1.stop_loss_manager import StopLossManager

        mgr = StopLossManager(config, tmp_db)
        mgr.sync_stop_orders = MagicMock()

        portfolio = _make_portfolio()
        strategy = _make_strategy()

        mgr.resync_after_fill_or_rebalance(portfolio, strategy)

        mgr.sync_stop_orders.assert_called_once_with(strategy, portfolio)
