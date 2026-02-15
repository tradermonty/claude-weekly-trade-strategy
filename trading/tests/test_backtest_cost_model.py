"""Tests for transaction cost model (Phase 1 robustness)."""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

import pytest

from trading.backtest.config import CostModel
from trading.backtest.metrics import BacktestMetrics, BacktestResult, DailySnapshot
from trading.backtest.portfolio_simulator import SimulatedPortfolio, TradeRecord
from trading.backtest.report import print_terminal_report, write_csv_reports


# ---------------------------------------------------------------------------
# TestCostModel
# ---------------------------------------------------------------------------
class TestCostModel:

    def test_buy_cost_is_half_spread(self):
        model = CostModel(spread_bps=2.0)
        cost = model.calculate_cost("buy", shares=100, price=500.0)
        # 100 * 500 * 2 / 10000 = 10.0
        assert cost == pytest.approx(10.0)

    def test_sell_cost_includes_taf(self):
        model = CostModel(spread_bps=2.0, sec_taf_rate=22.90e-6)
        cost = model.calculate_cost("sell", shares=100, price=500.0)
        value = 100 * 500.0
        expected = (2.0 / 10_000) * value + 22.90e-6 * value
        assert cost == pytest.approx(expected)

    def test_zero_spread_zero_buy_cost(self):
        model = CostModel(spread_bps=0.0, sec_taf_rate=0.0)
        assert model.calculate_cost("buy", 100, 500.0) == 0.0

    def test_zero_spread_sell_has_taf(self):
        model = CostModel(spread_bps=0.0, sec_taf_rate=22.90e-6)
        cost = model.calculate_cost("sell", 100, 500.0)
        assert cost == pytest.approx(22.90e-6 * 50_000)

    def test_cost_proportional_to_value(self):
        model = CostModel(spread_bps=1.0)
        cost1 = model.calculate_cost("buy", 100, 100.0)
        cost2 = model.calculate_cost("buy", 200, 100.0)
        assert cost2 == pytest.approx(cost1 * 2)


# ---------------------------------------------------------------------------
# TestPortfolioWithCosts
# ---------------------------------------------------------------------------
class TestPortfolioWithCosts:

    def _make_portfolio(self, spread_bps: float = 5.0) -> SimulatedPortfolio:
        p = SimulatedPortfolio(100_000.0)
        p.set_cost_model(CostModel(spread_bps=spread_bps, sec_taf_rate=0.0))
        return p

    def test_cost_deducted_from_cash(self):
        p = self._make_portfolio(spread_bps=10.0)
        prices = {"SPY": 500.0}
        # target 50% SPY => buy ~$50k worth => ~100 shares
        p.rebalance_to({"SPY": 50.0}, prices, trade_date=date(2025, 1, 1))
        # cost = 100 * 500 * 10/10000 = $50
        # Cash should be ~ 50000 - 50 = 49950 (not exactly due to rounding)
        assert p.cash < 50_000  # cost deducted
        assert p.total_costs > 0

    def test_cost_reduces_final_value(self):
        p_with_cost = self._make_portfolio(spread_bps=20.0)
        p_no_cost = SimulatedPortfolio(100_000.0)
        p_no_cost.set_cost_model(CostModel(spread_bps=0.0, sec_taf_rate=0.0))

        prices = {"SPY": 500.0}
        p_with_cost.rebalance_to({"SPY": 80.0}, prices, trade_date=date(2025, 1, 1))
        p_no_cost.rebalance_to({"SPY": 80.0}, prices, trade_date=date(2025, 1, 1))

        assert p_with_cost.total_value < p_no_cost.total_value

    def test_trade_record_has_cost(self):
        p = self._make_portfolio(spread_bps=5.0)
        prices = {"SPY": 500.0}
        p.rebalance_to({"SPY": 50.0}, prices, trade_date=date(2025, 1, 1))
        assert len(p.trades) > 0
        for t in p.trades:
            assert t.cost > 0

    def test_total_costs_accumulates(self):
        p = self._make_portfolio(spread_bps=5.0)
        prices = {"SPY": 500.0, "QQQ": 400.0}
        p.rebalance_to({"SPY": 50.0, "QQQ": 30.0}, prices, trade_date=date(2025, 1, 1))
        expected = sum(t.cost for t in p.trades)
        assert p.total_costs == pytest.approx(expected)

    def test_sell_cost_deducted(self):
        """Sell trade costs reduce proceeds (cash)."""
        p = self._make_portfolio(spread_bps=5.0)
        prices = {"SPY": 500.0}
        # First buy
        p.rebalance_to({"SPY": 80.0}, prices, trade_date=date(2025, 1, 1))
        cash_after_buy = p.cash
        costs_after_buy = p.total_costs

        # Sell all (target 0%)
        p.rebalance_to({}, prices, trade_date=date(2025, 1, 2))
        # Cost should increase from sell
        assert p.total_costs > costs_after_buy


# ---------------------------------------------------------------------------
# TestTurnover
# ---------------------------------------------------------------------------
class TestTurnover:

    def test_no_trades_zero_turnover(self):
        snaps = [DailySnapshot(date=date(2025, 1, d), total_value=100_000,
                               cash=100_000, positions_value=0)
                 for d in range(1, 6)]
        m = BacktestMetrics(snaps, 100_000.0, trade_records=[])
        assert m.turnover == 0.0

    def test_known_turnover_value(self):
        snaps = [DailySnapshot(date=date(2025, 1, d), total_value=100_000,
                               cash=50_000, positions_value=50_000)
                 for d in range(1, 6)]
        # total trade value = 20_000 (buy) + 10_000 (sell) = 30_000
        trades = [
            TradeRecord(date=date(2025, 1, 1), symbol="SPY", side="buy",
                        shares=40, price=500, value=20_000),
            TradeRecord(date=date(2025, 1, 3), symbol="SPY", side="sell",
                        shares=20, price=500, value=10_000),
        ]
        m = BacktestMetrics(snaps, 100_000.0, trade_records=trades)
        # turnover = 30_000 / 100_000 = 0.3
        assert m.turnover == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# TestReportCostColumns
# ---------------------------------------------------------------------------
class TestReportCostColumns:

    def _make_result(self) -> BacktestResult:
        return BacktestResult(
            phase="B",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 1),
            trading_days=40,
            blogs_used=8,
            blogs_skipped=1,
            initial_capital=100_000,
            final_value=105_000,
            total_return_pct=4.90,
            max_drawdown_pct=-2.5,
            sharpe_ratio=2.1,
            total_trades=50,
            gross_return_pct=5.00,
            total_cost=100.0,
            turnover=1.5,
        )

    def test_summary_csv_has_new_columns(self, tmp_path):
        result = self._make_result()
        write_csv_reports(result, tmp_path)
        with open(tmp_path / "summary.csv") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert "gross_return_pct" in header
        assert "total_cost" in header
        assert "turnover" in header

    def test_trades_csv_has_cost_column(self, tmp_path):
        result = self._make_result()
        result.trade_records = [
            TradeRecord(date=date(2025, 1, 2), symbol="SPY", side="buy",
                        shares=10, price=500, value=5000, cost=0.5),
        ]
        write_csv_reports(result, tmp_path)
        with open(tmp_path / "trades.csv") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert "cost" in header

    def test_terminal_report_shows_net_gross(self):
        result = self._make_result()
        output = print_terminal_report(result)
        assert "Net Return:" in output
        assert "Gross Return:" in output
        assert "Total Costs:" in output
        assert "Turnover:" in output
