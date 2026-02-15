"""Tests for backtest CLI parser and report output."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from trading.backtest.cli import build_parser, _trim_end_date
from trading.backtest.metrics import BacktestResult, DailySnapshot, WeeklyPerformance
from trading.backtest.portfolio_simulator import TradeRecord
from trading.backtest.report import print_terminal_report, write_csv_reports


# --- CLI Parser Tests ---

class TestBuildParser:
    def test_required_start(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_start_only(self):
        parser = build_parser()
        args = parser.parse_args(["--start", "2026-01-05"])
        assert args.start == date(2026, 1, 5)
        assert args.end is None
        assert args.capital == 100_000
        assert args.phase == "A"
        assert args.slippage == 0
        assert args.verbose is False

    def test_all_options(self):
        parser = build_parser()
        args = parser.parse_args([
            "--start", "2026-01-05",
            "--end", "2026-02-14",
            "--capital", "50000",
            "--phase", "B",
            "--slippage", "10",
            "--blogs-dir", "/tmp/blogs",
            "--output", "/tmp/output",
            "--verbose",
        ])
        assert args.start == date(2026, 1, 5)
        assert args.end == date(2026, 2, 14)
        assert args.capital == 50_000
        assert args.phase == "B"
        assert args.slippage == 10
        assert args.blogs_dir == Path("/tmp/blogs")
        assert args.output == Path("/tmp/output")
        assert args.verbose is True

    def test_invalid_phase_rejected(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--start", "2026-01-05", "--phase", "C"])


class TestTrimEndDate:
    def test_trims_weekend(self):
        # 2026-01-10 is Saturday
        result = _trim_end_date(date(2026, 1, 10))
        assert result == date(2026, 1, 9)  # Friday

    def test_trims_sunday(self):
        result = _trim_end_date(date(2026, 1, 11))
        assert result == date(2026, 1, 9)

    def test_weekday_unchanged(self):
        result = _trim_end_date(date(2026, 1, 9))
        assert result == date(2026, 1, 9)

    def test_trims_future_date(self):
        far_future = date(2099, 12, 31)
        result = _trim_end_date(far_future)
        assert result <= date.today()


# --- Report Output Tests ---

def _sample_result() -> BacktestResult:
    """Create a sample BacktestResult for testing."""
    snapshots = [
        DailySnapshot(date=date(2026, 1, 5), total_value=100_000, cash=30_000,
                       positions_value=70_000, allocation={"SPY": 50, "BIL": 20},
                       scenario="base", trades_today=3),
        DailySnapshot(date=date(2026, 1, 6), total_value=100_500, cash=30_000,
                       positions_value=70_500, allocation={"SPY": 50.2, "BIL": 19.8},
                       scenario="base", trades_today=0),
    ]
    weekly = [
        WeeklyPerformance(blog_date="2026-01-05", start_value=100_000,
                          end_value=100_500, return_pct=0.5, trades=3, scenario="base"),
    ]
    trades = [
        TradeRecord(date=date(2026, 1, 5), symbol="SPY", side="buy",
                    shares=100.0, price=500.0, value=50_000.0, reason="rebalance"),
        TradeRecord(date=date(2026, 1, 5), symbol="BIL", side="buy",
                    shares=200.0, price=100.0, value=20_000.0, reason="rebalance"),
        TradeRecord(date=date(2026, 1, 5), symbol="QQQ", side="sell",
                    shares=50.0, price=400.0, value=20_000.0, reason="rebalance"),
    ]
    return BacktestResult(
        phase="A",
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 6),
        trading_days=2,
        blogs_used=1,
        blogs_skipped=5,
        initial_capital=100_000,
        final_value=100_500,
        total_return_pct=0.5,
        max_drawdown_pct=-0.1,
        sharpe_ratio=1.5,
        total_trades=3,
        daily_snapshots=snapshots,
        weekly_performance=weekly,
        skipped_reasons=[("2025-11-03", "current_allocation empty")],
        trade_records=trades,
    )


class TestTerminalReport:
    def test_contains_key_fields(self):
        result = _sample_result()
        output = print_terminal_report(result)
        assert "Phase A" in output
        assert "$100,000.00" in output
        assert "$100,500.00" in output
        assert "+0.50%" in output
        assert "Sharpe" in output

    def test_weekly_performance_section(self):
        result = _sample_result()
        output = print_terminal_report(result)
        assert "Weekly Performance" in output
        assert "2026-01-05" in output

    def test_skipped_section(self):
        result = _sample_result()
        output = print_terminal_report(result)
        assert "Skipped Blogs" in output
        assert "2025-11-03" in output
        assert "current_allocation empty" in output


class TestCSVReports:
    def test_creates_three_files(self, tmp_path):
        result = _sample_result()
        write_csv_reports(result, tmp_path)
        assert (tmp_path / "summary.csv").exists()
        assert (tmp_path / "daily.csv").exists()
        assert (tmp_path / "trades.csv").exists()

    def test_summary_csv_content(self, tmp_path):
        result = _sample_result()
        write_csv_reports(result, tmp_path)

        with open(tmp_path / "summary.csv") as f:
            reader = csv.reader(f)
            header = next(reader)
            row = next(reader)

        assert "phase" in header
        assert "total_return_pct" in header
        assert row[header.index("phase")] == "A"
        assert float(row[header.index("initial_capital")]) == 100_000

    def test_daily_csv_has_all_rows(self, tmp_path):
        result = _sample_result()
        write_csv_reports(result, tmp_path)

        with open(tmp_path / "daily.csv") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)

        assert "date" in header
        assert "total_value" in header
        assert len(rows) == 2  # 2 daily snapshots

    def test_trades_csv_has_individual_records(self, tmp_path):
        """trades.csv should contain individual trade records, not weekly summaries."""
        result = _sample_result()
        write_csv_reports(result, tmp_path)

        with open(tmp_path / "trades.csv") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)

        assert "date" in header
        assert "symbol" in header
        assert "side" in header
        assert "shares" in header
        assert "price" in header
        assert "value" in header
        assert "reason" in header
        assert len(rows) == 3  # 3 individual trades

        # Verify content of first trade
        first = dict(zip(header, rows[0]))
        assert first["symbol"] == "SPY"
        assert first["side"] == "buy"
        assert float(first["shares"]) == 100.0
        assert first["reason"] == "rebalance"

    def test_creates_output_dir(self, tmp_path):
        result = _sample_result()
        output = tmp_path / "subdir" / "output"
        write_csv_reports(result, output)
        assert output.exists()
        assert (output / "summary.csv").exists()
