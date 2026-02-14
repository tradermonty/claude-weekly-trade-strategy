"""Shared fixtures for all trading system tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading.config import TradingConfig, AlpacaConfig, FMPConfig, EmailConfig
from trading.data.database import Database
from trading.data.models import (
    MarketData,
    Portfolio,
    Position,
    StrategySpec,
    ScenarioSpec,
    TradingLevel,
    StrategyIntent,
    CheckResult,
    CheckResultType,
    ValidationResult,
    ValidationResultType,
    Order,
    AccountSnapshot,
)


@pytest.fixture
def tmp_db():
    """Create an in-memory SQLite database with the schema applied."""
    db = Database(":memory:")
    db.connect()
    db.migrate()
    yield db
    db.close()


@pytest.fixture
def config(tmp_path):
    """Return a TradingConfig suitable for testing (dry_run=True, temp paths)."""
    return TradingConfig(
        dry_run=True,
        db_path=tmp_path / "test.db",
        lock_file=tmp_path / ".scheduler.lock",
        log_dir=tmp_path / "logs",
        blogs_dir=tmp_path / "blogs",
    )


@pytest.fixture
def sample_market_data():
    """Return a MarketData instance with realistic current-market values."""
    return MarketData(
        timestamp=datetime.now(timezone.utc),
        vix=20.5,
        us10y=4.36,
        sp500=6828.0,
        nasdaq=21700.0,
        dow=44500.0,
        gold=5046.0,
        oil=62.8,
        copper=5.8,
        etf_prices={
            "SPY": 683.1,
            "QQQ": 531.2,
            "DIA": 441.3,
        },
    )


@pytest.fixture
def sample_portfolio():
    """Return a Portfolio with a $100K account and diversified positions."""
    return Portfolio(
        account_value=100000,
        cash=28000,
        positions={
            "SPY": Position(
                symbol="SPY",
                shares=32.2,
                market_value=22000,
                cost_basis=20000,
                current_price=683.1,
            ),
            "QQQ": Position(
                symbol="QQQ",
                shares=7.5,
                market_value=4000,
                cost_basis=3500,
                current_price=531.2,
            ),
            "DIA": Position(
                symbol="DIA",
                shares=18.1,
                market_value=8000,
                cost_basis=7800,
                current_price=441.3,
            ),
            "XLV": Position(
                symbol="XLV",
                shares=80.0,
                market_value=12000,
                cost_basis=11500,
                current_price=150.0,
            ),
            "XLP": Position(
                symbol="XLP",
                shares=40.0,
                market_value=4000,
                cost_basis=3800,
                current_price=100.0,
            ),
            "GLD": Position(
                symbol="GLD",
                shares=22.0,
                market_value=12000,
                cost_basis=10000,
                current_price=545.4,
            ),
            "XLE": Position(
                symbol="XLE",
                shares=100.0,
                market_value=10000,
                cost_basis=9500,
                current_price=100.0,
            ),
        },
    )


@pytest.fixture
def sample_strategy_spec():
    """Return a StrategySpec parsed from a blog with base and bear scenarios."""
    return StrategySpec(
        blog_date="2026-02-16",
        current_allocation={
            "SPY": 22.0,
            "QQQ": 4.0,
            "DIA": 8.0,
            "XLV": 12.0,
            "XLP": 4.0,
            "GLD": 12.0,
            "XLE": 10.0,
            "BIL": 28.0,
        },
        scenarios={
            "base": ScenarioSpec(
                name="base",
                probability=45,
                triggers=[],
                allocation={
                    "SPY": 22.0,
                    "QQQ": 4.0,
                    "DIA": 8.0,
                    "XLV": 12.0,
                    "XLP": 4.0,
                    "GLD": 12.0,
                    "XLE": 10.0,
                    "BIL": 28.0,
                },
            ),
            "bear": ScenarioSpec(
                name="bear",
                probability=30,
                triggers=["VIX > 23"],
                allocation={
                    "SPY": 15.0,
                    "QQQ": 2.0,
                    "DIA": 5.0,
                    "XLV": 15.0,
                    "XLP": 8.0,
                    "GLD": 15.0,
                    "XLE": 5.0,
                    "BIL": 35.0,
                },
            ),
        },
        trading_levels={
            "sp500": TradingLevel(
                buy_level=6500.0,
                sell_level=7100.0,
                stop_loss=6300.0,
            ),
            "nasdaq": TradingLevel(
                buy_level=20000.0,
                sell_level=23000.0,
                stop_loss=19500.0,
            ),
        },
        stop_losses={
            "sp500": 6300.0,
            "nasdaq": 19500.0,
            "dow": 42000.0,
        },
        vix_triggers={
            "risk_on": 17.0,
            "caution": 20.0,
            "stress": 23.0,
        },
        yield_triggers={
            "lower": 4.11,
            "warning": 4.36,
            "red_line": 4.50,
        },
        breadth_200ma=55.0,
        uptrend_ratio=32.0,
        bubble_score=9,
        pre_event_dates=["2/18"],
    )
