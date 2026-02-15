"""CLI for running backtests: ``python -m trading.backtest``."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from trading.backtest.config import BacktestConfig, CostModel
from trading.backtest.data_provider import DataProvider
from trading.backtest.engine import PhaseAEngine, PhaseBEngine
from trading.backtest.report import (
    print_comparison_table,
    print_terminal_report,
    write_csv_reports,
)
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
        "--timing", choices=["transition", "week_end"], default="transition",
        help="Rebalance timing: transition (blog publish day) or week_end (Friday)",
    )
    parser.add_argument(
        "--spread-bps", type=float, default=1.0,
        help="Spread cost in basis points per side (default: 1.0)",
    )
    parser.add_argument(
        "--benchmark", action="store_true",
        help="Run benchmark comparison (SPY B&H, 60/40, Equal-Weight)",
    )
    parser.add_argument(
        "--cost-matrix", action="store_true",
        help="Run cost sensitivity matrix (4 modes x 5 cost levels)",
    )
    parser.add_argument(
        "--full-robustness", action="store_true",
        help="Run full robustness analysis (cost matrix + benchmarks + report)",
    )
    parser.add_argument(
        "--walk-forward", action="store_true",
        help="Run walk-forward validation (sub-period consistency + statistical tests)",
    )
    parser.add_argument(
        "--window-weeks", type=int, default=6,
        help="Rolling window size in weeks for walk-forward (default: 6)",
    )
    parser.add_argument(
        "--step-weeks", type=int, default=2,
        help="Rolling window step size in weeks (default: 2)",
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

    cost_model = CostModel(spread_bps=args.spread_bps)

    config = BacktestConfig(
        start=args.start,
        end=end,
        initial_capital=args.capital,
        phase=args.phase,
        slippage_bps=args.slippage,
        blogs_dir=args.blogs_dir,
        output_dir=args.output,
        verbose=args.verbose,
        rebalance_timing=args.timing,
        cost_model=cost_model,
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

    # Load data for all symbols used in blogs
    symbols = list(set(
        sym for entry in timeline.entries
        for sym in entry.strategy.current_allocation.keys()
    ))

    # Walk-forward needs SPY for benchmark comparison
    if args.walk_forward:
        if "SPY" not in symbols:
            symbols.append("SPY")

    # Benchmarks may need TLT even if not in blogs
    if args.benchmark or args.full_robustness:
        if "TLT" not in symbols:
            symbols.append("TLT")

    print(f"Loading data for {len(symbols)} symbols: {', '.join(sorted(symbols))}", file=sys.stderr)
    data_provider.load_etf_data(symbols, config.start, end)

    # Phase B always needs FMP data; cost-matrix runs all modes including B
    if args.phase == "B" or args.cost_matrix or args.full_robustness:
        data_provider.load_fmp_data(config.start, end)

    output_dir = config.output_dir or Path("results/robustness")

    # --- Full robustness ---
    if args.full_robustness:
        _run_full_robustness(config, timeline, data_provider, symbols, output_dir)
        return

    # --- Cost matrix ---
    if args.cost_matrix:
        _run_cost_matrix(config, timeline, data_provider, output_dir)
        return

    # --- Walk-forward validation ---
    if args.walk_forward:
        _run_walk_forward(config, timeline, data_provider, output_dir, args)
        return

    # --- Normal run (with optional benchmark) ---
    if args.phase == "A":
        engine = PhaseAEngine(config, timeline, data_provider)
    else:
        engine = PhaseBEngine(config, timeline, data_provider)

    result = engine.run()
    print_terminal_report(result)

    if args.benchmark:
        _run_benchmark(config, data_provider, symbols, {result.phase: result}, output_dir)

    if config.output_dir:
        write_csv_reports(result, config.output_dir)
        print(f"\nCSV reports written to {config.output_dir}/", file=sys.stderr)


def _run_cost_matrix(
    config: BacktestConfig,
    timeline: StrategyTimeline,
    data_provider: DataProvider,
    output_dir: Path,
) -> None:
    from trading.backtest.robustness import (
        find_breakeven,
        run_cost_matrix,
        write_cost_matrix_csv,
    )

    print("\n=== Running Cost Sensitivity Matrix ===", file=sys.stderr)
    results = run_cost_matrix(timeline, data_provider, config)

    be = find_breakeven(results)
    print(f"\nBreakeven: {be['details']}", file=sys.stderr)

    csv_path = output_dir / "cost_matrix.csv"
    write_cost_matrix_csv(results, csv_path)
    print(f"Cost matrix written to {csv_path}", file=sys.stderr)


def _run_benchmark(
    config: BacktestConfig,
    data_provider: DataProvider,
    symbols: list[str],
    strategy_results: dict,
    output_dir: Path,
) -> None:
    from trading.backtest.benchmark import BenchmarkEngine

    print("\n=== Running Benchmarks ===", file=sys.stderr)
    bench_engine = BenchmarkEngine(
        data_provider, config.start, config.end,
        config.initial_capital, config.cost_model,
    )
    bench_results = bench_engine.run_all(symbols)

    print_comparison_table(strategy_results, bench_results)


def _run_full_robustness(
    config: BacktestConfig,
    timeline: StrategyTimeline,
    data_provider: DataProvider,
    symbols: list[str],
    output_dir: Path,
) -> None:
    from trading.backtest.benchmark import BenchmarkEngine
    from trading.backtest.robustness import (
        find_breakeven,
        generate_robustness_report,
        run_cost_matrix,
        write_cost_matrix_csv,
    )

    print("\n=== Full Robustness Analysis ===", file=sys.stderr)

    # 1. Cost matrix (20 cases)
    print("\n--- Phase 1: Cost Sensitivity Matrix ---", file=sys.stderr)
    matrix_results = run_cost_matrix(timeline, data_provider, config)

    csv_path = output_dir / "cost_matrix.csv"
    write_cost_matrix_csv(matrix_results, csv_path)
    print(f"Cost matrix: {csv_path}", file=sys.stderr)

    breakeven = find_breakeven(matrix_results)
    print(f"Breakeven: {breakeven['details']}", file=sys.stderr)

    # 2. Benchmarks
    print("\n--- Phase 2: Benchmarks ---", file=sys.stderr)
    bench_engine = BenchmarkEngine(
        data_provider, config.start, config.end,
        config.initial_capital, config.cost_model,
    )
    bench_results = bench_engine.run_all(symbols)

    # Collect strategy results at default spread for comparison
    strategy_results = {}
    for r in matrix_results:
        if r["cost_bps"] == config.cost_model.spread_bps:
            strategy_results[r["mode"]] = r["result"]
    # Fallback: use 0 bps results if no match
    if not strategy_results:
        for r in matrix_results:
            if r["cost_bps"] == 0:
                strategy_results[r["mode"]] = r["result"]

    print_comparison_table(strategy_results, bench_results)

    # 3. Report
    print("\n--- Phase 3: Report Generation ---", file=sys.stderr)
    report_path = output_dir / "backtest_robustness.md"
    generate_robustness_report(
        strategy_results, matrix_results, bench_results,
        breakeven, report_path,
    )
    print(f"Report: {report_path}", file=sys.stderr)
    print("\nDone.", file=sys.stderr)


def _run_walk_forward(
    config: BacktestConfig,
    timeline: StrategyTimeline,
    data_provider: DataProvider,
    output_dir: Path,
    args,
) -> None:
    from trading.backtest.walk_forward import (
        WalkForwardConfig,
        WalkForwardValidator,
        write_walk_forward_report,
    )

    wf_config = WalkForwardConfig(
        window_weeks=args.window_weeks,
        step_weeks=args.step_weeks,
    )

    print("\n=== Walk-Forward Validation ===", file=sys.stderr)
    validator = WalkForwardValidator(config, wf_config, timeline, data_provider)
    result = validator.run()

    # Print full period results
    print_terminal_report(result.full_period)

    # Print walk-forward summary
    wins = sum(1 for w in result.weekly_excess if w.excess_pct > 0)
    total = len(result.weekly_excess)
    pos_win = sum(1 for w in result.rolling_windows if w.excess_return_pct > 0)
    total_win = len(result.rolling_windows)

    print(f"\n=== Walk-Forward Summary ===")
    print(f"Verdict: {result.verdict}")
    print(f"  {result.verdict_detail}")
    print(f"Weekly Win Rate: {result.win_rate:.0%} ({wins}/{total})")
    print(f"Mean Weekly Excess: {result.mean_weekly_excess:+.2f}%")
    print(f"t-statistic: {result.t_statistic:.2f}, p-value: {result.p_value:.4f}")
    print(f"Information Ratio: {result.information_ratio:.2f}")
    print(f"Rolling: {pos_win}/{total_win} windows positive")

    # Write report
    report_path = output_dir / "walk_forward_report.md"
    write_walk_forward_report(result, report_path)
    print(f"\nReport: {report_path}", file=sys.stderr)
    print("Done.", file=sys.stderr)
