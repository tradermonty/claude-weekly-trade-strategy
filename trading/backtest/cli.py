"""CLI for running backtests: ``python -m trading.backtest``."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from trading.backtest.config import BacktestConfig
from trading.backtest.data_provider import DataProvider
from trading.backtest.engine import PhaseAEngine, PhaseBEngine
from trading.backtest.report import print_terminal_report, write_csv_reports
from trading.backtest.strategy_timeline import StrategyTimeline
from trading.config import AlpacaConfig, FMPConfig
from trading.core.holidays import USMarketCalendar

_calendar = USMarketCalendar()


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def _trim_end_date(d: date) -> date:
    """Trim end date to today if in the future, and to last trading day."""
    today = date.today()
    if d > today:
        d = today
    while d.weekday() >= 5 or _calendar.is_market_holiday(d):
        d -= timedelta(days=1)
    return d


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading.backtest",
        description="Backtest weekly trade strategy blog posts",
    )
    parser.add_argument(
        "--start", type=_parse_date, required=True,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end", type=_parse_date, default=None,
        help="End date (YYYY-MM-DD), defaults to today",
    )
    parser.add_argument(
        "--capital", type=float, default=100_000,
        help="Initial capital (default: 100000)",
    )
    parser.add_argument(
        "--phase", choices=["A", "B"], default="A",
        help="Phase A (weekly rebalance) or B (rule engine)",
    )
    parser.add_argument(
        "--slippage", type=float, default=0,
        help="Slippage in basis points (default: 0)",
    )
    parser.add_argument(
        "--blogs-dir", type=Path, default=Path("blogs"),
        help="Path to blogs directory (default: blogs/)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output directory for CSV reports",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Verbose logging",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    # Trim end date
    end = args.end or date.today()
    end = _trim_end_date(end)

    config = BacktestConfig(
        start=args.start,
        end=end,
        initial_capital=args.capital,
        phase=args.phase,
        slippage_bps=args.slippage,
        blogs_dir=args.blogs_dir,
        output_dir=args.output,
        verbose=args.verbose,
    )

    # Build timeline
    timeline = StrategyTimeline()
    timeline.build(config.blogs_dir)

    if not timeline.entries:
        print("ERROR: No valid blog posts found in", config.blogs_dir, file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(timeline.entries)} valid blogs, {len(timeline.skipped)} skipped", file=sys.stderr)
    print(f"Effective start: {timeline.effective_start}", file=sys.stderr)

    # Build data provider (FMP is always available as ETF data fallback)
    alpaca = AlpacaConfig.from_env()
    fmp = FMPConfig.from_env()

    cache_dir = Path(".backtest_cache")
    data_provider = DataProvider(alpaca, fmp, cache_dir)

    # Load data
    symbols = list(set(
        sym for entry in timeline.entries
        for sym in entry.strategy.current_allocation.keys()
    ))
    print(f"Loading data for {len(symbols)} symbols: {', '.join(sorted(symbols))}", file=sys.stderr)

    data_provider.load_etf_data(symbols, config.start, end)

    if args.phase == "B":
        data_provider.load_fmp_data(config.start, end)

    # Run engine
    if args.phase == "A":
        engine = PhaseAEngine(config, timeline, data_provider)
    else:
        engine = PhaseBEngine(config, timeline, data_provider)

    result = engine.run()

    # Output
    print_terminal_report(result)

    if config.output_dir:
        write_csv_reports(result, config.output_dir)
        print(f"\nCSV reports written to {config.output_dir}/", file=sys.stderr)
