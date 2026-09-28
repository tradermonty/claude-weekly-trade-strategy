"""Tests for DataProvider dividend-adjusted price handling (Issue #3).

Verifies that ETF valuation/returns use dividend-adjusted prices (FMP ``adjClose``
and Alpaca ``Adjustment.ALL``), that BIL-style distributions are reflected in the
daily return, and that the old unadjusted disk cache keys are no longer used.
"""

from __future__ import annotations

import json
from datetime import date
from unittest import mock

import pytest

from trading.backtest.data_provider import DataProvider
from trading.backtest.portfolio_simulator import SimulatedPortfolio
from trading.config import AlpacaConfig, FMPConfig


class TestFMPAdjustedParsing:
    """(a) FMP ETF parsing uses adjClose and scales open by the same factor."""

    @staticmethod
    def _dp() -> DataProvider:
        return DataProvider(
            AlpacaConfig(api_key="", secret_key="", base_url=""),
            FMPConfig(api_key="test-key", base_url="https://example.com/api/v3"),
        )

    @staticmethod
    def _fake_response(payload: dict):
        """Return a context-manager object that urlopen() yields.

        The production code does ``with urllib.request.urlopen(...) as resp``, so
        the mocked urlopen must return an object supporting the context manager
        protocol and exposing ``.read()``.
        """
        body = json.dumps(payload).encode()
        resp = mock.MagicMock()
        resp.read.return_value = body
        cm = mock.MagicMock()
        cm.__enter__.return_value = resp
        cm.__exit__.return_value = False
        return cm

    def test_adjusted_uses_adjclose_and_scales_open(self, monkeypatch):
        payload = {
            "historical": [
                {"date": "2026-01-05", "close": 100.0, "adjClose": 99.0, "open": 101.0},
                {"date": "2026-01-06", "close": 102.0, "adjClose": 103.0, "open": 100.0},
            ]
        }
        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda *a, **k: self._fake_response(payload),
        )

        close, open_ = self._dp()._fetch_fmp_historical(
            "SPY", date(2026, 1, 1), date(2026, 1, 31), adjusted=True,
        )

        # close == adjClose
        assert close[date(2026, 1, 5)] == 99.0
        assert close[date(2026, 1, 6)] == 103.0
        # open scaled by adjClose/close factor
        assert open_[date(2026, 1, 5)] == pytest.approx(101.0 * 99.0 / 100.0)
        assert open_[date(2026, 1, 6)] == pytest.approx(100.0 * 103.0 / 102.0)

    def test_raw_keeps_close_and_open(self, monkeypatch):
        payload = {
            "historical": [
                {"date": "2026-01-05", "close": 100.0, "adjClose": 99.0, "open": 101.0},
            ]
        }
        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda *a, **k: self._fake_response(payload),
        )

        close, open_ = self._dp()._fetch_fmp_historical(
            "SPY", date(2026, 1, 1), date(2026, 1, 31), adjusted=False,
        )

        # Indicator/index data stays on raw close and open (blog level basis)
        assert close[date(2026, 1, 5)] == 100.0
        assert open_[date(2026, 1, 5)] == 101.0


class TestBILDistributionReturn:
    """(b) A BIL-like series with a distribution day yields the distribution as return."""

    def test_bil_distribution_shows_in_daily_return(self):
        start = date(2026, 1, 2)
        end = date(2026, 1, 30)
        dp = DataProvider(AlpacaConfig(api_key="", secret_key="", base_url=""))
        days = dp.get_trading_days(start, end)

        # BIL raw price is ~flat but adjusted close rises ~$0.02/day (daily
        # distribution), so a total-return series grows rather than staying flat.
        bil_adj: dict[date, float] = {
            d: round(91.56 + i * 0.02, 6) for i, d in enumerate(days)
        }
        dp.inject_etf_data("BIL", bil_adj)

        portfolio = SimulatedPortfolio(100_000)
        day1, day2 = days[0], days[1]
        portfolio.rebalance_to({"BIL": 100.0}, dp.get_etf_prices(day1), day1)
        v0 = portfolio.total_value

        portfolio.update_prices(dp.get_etf_prices(day2))
        v1 = portfolio.total_value

        daily_return = (v1 / v0 - 1) * 100.0
        expected = (bil_adj[day2] / bil_adj[day1] - 1) * 100.0

        # Distribution is captured as a positive daily return.
        assert daily_return > 0
        assert daily_return == pytest.approx(expected, abs=1e-4)


class TestDiskCacheKey:
    """(c) Old, unadjusted cache key names are no longer used."""

    def test_uses_adj_cache_keys(self, tmp_path, monkeypatch):
        dp = DataProvider(
            AlpacaConfig(api_key="", secret_key="", base_url=""),
            FMPConfig(api_key="x"),
            cache_dir=tmp_path,
        )
        start, end = date(2026, 1, 2), date(2026, 1, 9)

        # Write stale unadjusted caches under the old names with bogus data.
        (tmp_path / "etf_SPY.json").write_text(json.dumps({"2026-01-05": 999.0}))
        (tmp_path / "etf_SPY_open.json").write_text(json.dumps({"2026-01-05": 888.0}))

        close = {date(2026, 1, 2): 100.0, date(2026, 1, 5): 101.0}
        open_ = {date(2026, 1, 2): 99.0, date(2026, 1, 5): 100.0}
        monkeypatch.setattr(dp, "_fetch_alpaca_bars", lambda s, st, en: ({}, {}))
        monkeypatch.setattr(
            dp, "_fetch_fmp_historical", lambda s, st, en, adjusted=False: (close, open_)
        )

        dp.load_etf_data(["SPY"], start, end)

        # New adjusted cache files written.
        assert (tmp_path / "etf_adj_SPY.json").exists()
        assert (tmp_path / "etf_adj_SPY_open.json").exists()

        # Old unadjusted cache files are not read or overwritten: their content
        # stays the stale placeholder we wrote above.
        assert json.loads((tmp_path / "etf_SPY.json").read_text())["2026-01-05"] == 999.0
        assert json.loads((tmp_path / "etf_SPY_open.json").read_text())["2026-01-05"] == 888.0

        # In-memory data comes from the fetch, not the stale old-format cache.
        assert dp._etf_cache["SPY"] == close
        assert dp._etf_open_cache["SPY"] == open_
