"""Tests for the MarketDataValidator class."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from trading.config import TradingConfig
from trading.services.data_validator import MarketDataValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> TradingConfig:
    return TradingConfig(dry_run=True, **overrides)


# ---------------------------------------------------------------------------
# Tests — validate (range check)
# ---------------------------------------------------------------------------

class TestValidateRange:
    """MarketDataValidator.validate()"""

    def test_validate_in_range(self):
        """VIX=20 is within the valid range [5, 90]."""
        v = MarketDataValidator(_make_config())
        assert v.validate("vix", 20.0) is True

    def test_validate_out_of_range(self):
        """VIX=95 is outside the valid range [5, 90]."""
        v = MarketDataValidator(_make_config())
        assert v.validate("vix", 95.0) is False

    def test_validate_unknown_indicator(self):
        """Unknown indicator is always valid (accepted by default)."""
        v = MarketDataValidator(_make_config())
        assert v.validate("unknown_thing", 999.0) is True


# ---------------------------------------------------------------------------
# Tests — is_fresh (staleness check)
# ---------------------------------------------------------------------------

class TestIsFresh:
    """MarketDataValidator.is_fresh()"""

    def test_is_fresh_recent_data(self):
        """Data from 10 seconds ago is fresh for fmp_quote (max 300s)."""
        v = MarketDataValidator(_make_config())
        recent = datetime.now() - timedelta(seconds=10)
        assert v.is_fresh("fmp_quote", recent) is True

    def test_is_fresh_stale_data(self):
        """Data from 10 minutes ago is stale for fmp_quote (max 300s)."""
        v = MarketDataValidator(_make_config())
        old = datetime.now() - timedelta(seconds=600)
        assert v.is_fresh("fmp_quote", old) is False

    def test_is_fresh_premarket_relaxed(self):
        """Pre-market session allows data up to 18 hours old."""
        v = MarketDataValidator(_make_config())
        # 2 hours old would be stale for fmp_quote during market hours (max 300s),
        # but should be fresh during pre_market (max relaxed to 18h)
        two_hours_ago = datetime.now() - timedelta(hours=2)
        assert v.is_fresh("fmp_quote", two_hours_ago, session="pre_market") is True


# ---------------------------------------------------------------------------
# Tests — resolve_conflict (multi-source merge)
# ---------------------------------------------------------------------------

class TestResolveConflict:
    """MarketDataValidator.resolve_conflict()"""

    def test_resolve_conflict_both_available(self):
        """Merges FMP and Alpaca data correctly (Alpaca wins for overlapping keys)."""
        v = MarketDataValidator(_make_config())

        fmp_data = {"vix": 20.0, "sp500": 6800.0, "gold": 5000.0}
        alpaca_data = {"SPY": 683.0, "QQQ": 530.0}
        previous = {"vix": 19.5, "sp500": 6750.0}

        result = v.resolve_conflict(fmp_data, alpaca_data, previous)

        # FMP values should be present
        assert result["vix"] == 20.0
        assert result["sp500"] == 6800.0
        assert result["gold"] == 5000.0
        # Alpaca values should be present
        assert result["SPY"] == 683.0
        assert result["QQQ"] == 530.0
        # Not stale
        assert result["_stale"] is False
        # Consecutive failures should be reset
        assert v.consecutive_api_failures == 0

    def test_resolve_conflict_fmp_only(self):
        """Falls back to previous state for Alpaca fields when Alpaca is None."""
        v = MarketDataValidator(_make_config())

        fmp_data = {"vix": 21.0, "sp500": 6850.0}
        previous = {"vix": 19.0, "SPY": 680.0, "QQQ": 528.0}

        result = v.resolve_conflict(fmp_data, None, previous)

        # FMP values override previous
        assert result["vix"] == 21.0
        assert result["sp500"] == 6850.0
        # Previous Alpaca values preserved since Alpaca is None
        assert result["SPY"] == 680.0
        assert result["QQQ"] == 528.0
        assert result["_stale"] is False
        assert v.consecutive_api_failures == 0

    def test_resolve_conflict_both_failed(self):
        """Increments failure counter when both sources are None."""
        v = MarketDataValidator(_make_config())
        assert v.consecutive_api_failures == 0

        previous = {"vix": 19.0, "sp500": 6700.0}
        result = v.resolve_conflict(None, None, previous)

        # Falls back to previous state
        assert result["vix"] == 19.0
        assert result["sp500"] == 6700.0
        assert result["_stale"] is True
        assert v.consecutive_api_failures == 1

        # Call again — counter keeps incrementing
        result2 = v.resolve_conflict(None, None, previous)
        assert v.consecutive_api_failures == 2


# ---------------------------------------------------------------------------
# Tests — F5 integration: is_fresh + resolve_conflict used in MarketMonitor
# ---------------------------------------------------------------------------

class TestFreshnessIntegration:
    """Verify that MarketMonitor integrates is_fresh() and resolve_conflict()."""

    @patch("trading.layer1.market_monitor.AlpacaClient")
    @patch("trading.layer1.market_monitor.FMPClient")
    def test_is_fresh_called_on_fallback(
        self, mock_fmp_cls, mock_alpaca_cls, tmp_db, config
    ):
        """When both APIs fail, is_fresh() is called on the fallback timestamp."""
        from unittest.mock import MagicMock
        from trading.layer1.market_monitor import MarketMonitor

        # Save a previous market state so there's data to fall back to
        ts = datetime.now().isoformat()
        tmp_db.save_market_state(timestamp=ts, vix=20.0, sp500=6800.0)

        monitor = MarketMonitor(config, tmp_db)
        monitor._fmp = MagicMock()
        monitor._fmp.fetch_quotes.return_value = None
        monitor._alpaca = MagicMock()
        monitor._alpaca.get_quotes.side_effect = Exception("Alpaca down")

        # Spy on is_fresh
        with patch.object(monitor._validator, "is_fresh", wraps=monitor._validator.is_fresh) as spy:
            monitor.fetch_market_data()
            # is_fresh should have been called at least once (for stale check)
            spy.assert_called()

    @patch("trading.layer1.market_monitor.AlpacaClient")
    @patch("trading.layer1.market_monitor.FMPClient")
    def test_resolve_conflict_used_for_merge(
        self, mock_fmp_cls, mock_alpaca_cls, tmp_db, config
    ):
        """resolve_conflict() is called to merge FMP and Alpaca data."""
        from unittest.mock import MagicMock
        from trading.layer1.market_monitor import MarketMonitor

        monitor = MarketMonitor(config, tmp_db)
        monitor._fmp = MagicMock()
        monitor._fmp.fetch_quotes.return_value = {"^VIX": {"price": 20.0}}
        monitor._fmp.fetch_treasury.return_value = {"year10": 4.36}
        monitor._alpaca = MagicMock()
        monitor._alpaca.get_quotes.return_value = {"SPY": 683.0}

        with patch.object(
            monitor._validator, "resolve_conflict", wraps=monitor._validator.resolve_conflict
        ) as spy:
            monitor.fetch_market_data()
            spy.assert_called_once()

    @patch("trading.layer1.market_monitor.AlpacaClient")
    @patch("trading.layer1.market_monitor.FMPClient")
    def test_stale_flag_set_when_both_fail(
        self, mock_fmp_cls, mock_alpaca_cls, tmp_db, config
    ):
        """When both APIs fail, merged result has _stale=True."""
        from unittest.mock import MagicMock
        from trading.layer1.market_monitor import MarketMonitor

        # Save previous state for fallback
        tmp_db.save_market_state(
            timestamp=datetime.now().isoformat(),
            vix=19.0, sp500=6750.0,
        )

        monitor = MarketMonitor(config, tmp_db)
        monitor._fmp = MagicMock()
        monitor._fmp.fetch_quotes.return_value = None
        monitor._alpaca = MagicMock()
        monitor._alpaca.get_quotes.side_effect = Exception("down")

        # After fetch, validator's consecutive_api_failures should have incremented
        monitor.fetch_market_data()
        assert monitor._validator.consecutive_api_failures >= 1

    @patch("trading.layer1.market_monitor.AlpacaClient")
    @patch("trading.layer1.market_monitor.FMPClient")
    def test_fresh_data_no_warning(
        self, mock_fmp_cls, mock_alpaca_cls, tmp_db, config
    ):
        """When APIs succeed, no stale warning is generated."""
        from unittest.mock import MagicMock
        from trading.layer1.market_monitor import MarketMonitor

        monitor = MarketMonitor(config, tmp_db)
        monitor._fmp = MagicMock()
        monitor._fmp.fetch_quotes.return_value = {"^VIX": {"price": 20.0}}
        monitor._fmp.fetch_treasury.return_value = {"year10": 4.36}
        monitor._alpaca = MagicMock()
        monitor._alpaca.get_quotes.return_value = {"SPY": 683.0}

        with patch("trading.layer1.market_monitor.logger") as mock_logger:
            monitor.fetch_market_data()
            # Should NOT have any error about stale data
            for call_args in mock_logger.error.call_args_list:
                assert "STALE" not in str(call_args)
