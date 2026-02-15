"""Report output formatters for backtest results."""

from __future__ import annotations

import csv
from pathlib import Path

from trading.backtest.metrics import BacktestResult


def print_terminal_report(result: BacktestResult) -> str:
    """Format backtest results for terminal display. Returns the string."""
    lines: list[str] = []

    lines.append(f"=== Backtest Results (Phase {result.phase}) ===")
    lines.append(f"Period:          {result.start_date} -> {result.end_date} ({result.trading_days} trading days)")
    lines.append(f"Blogs Used:      {result.blogs_used} of {result.blogs_used + result.blogs_skipped} ({result.blogs_skipped} skipped)")
    lines.append(f"Initial Capital: ${result.initial_capital:,.2f}")
    lines.append(f"Final Value:     ${result.final_value:,.2f}")

    sign = "+" if result.total_return_pct >= 0 else ""
    gross_sign = "+" if result.gross_return_pct >= 0 else ""
    lines.append(f"Net Return:      {sign}{result.total_return_pct:.2f}%")
    lines.append(f"Gross Return:    {gross_sign}{result.gross_return_pct:.2f}%")
    lines.append(f"Total Costs:     ${result.total_cost:,.2f}")
    lines.append(f"Max Drawdown:    {result.max_drawdown_pct:.2f}%")
    lines.append(f"Sharpe Ratio:    {result.sharpe_ratio:.2f}")
    lines.append(f"Total Trades:    {result.total_trades}")
    lines.append(f"Turnover:        {result.turnover:.2f}")
    lines.append("")

    if result.weekly_performance:
        lines.append("=== Weekly Performance ===")
        lines.append(f"{'Blog Week':<12}| {'Start':>12} | {'End':>12} | {'Return':>8} | {'Trades':>6} | Scenario")
        lines.append("-" * 78)
        for wp in result.weekly_performance:
            ret_sign = "+" if wp.return_pct >= 0 else ""
            lines.append(
                f"{wp.blog_date:<12}| ${wp.start_value:>10,.0f} | ${wp.end_value:>10,.0f} | "
                f"{ret_sign}{wp.return_pct:>6.2f}% | {wp.trades:>6} | {wp.scenario}"
            )
        lines.append("")

    if result.skipped_reasons:
        lines.append("=== Skipped Blogs (parse validation failed) ===")
        for blog_date, reason in result.skipped_reasons:
            lines.append(f"{blog_date}: {reason}")
        lines.append("")

    output = "\n".join(lines)
    print(output)
    return output


def write_csv_reports(result: BacktestResult, output_dir: Path) -> None:
    """Write CSV files: summary.csv, daily.csv, trades.csv."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # summary.csv
    summary_path = output_dir / "summary.csv"
    with open(summary_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "phase", "start_date", "end_date", "trading_days",
            "blogs_used", "blogs_skipped", "initial_capital",
            "final_value", "total_return_pct", "gross_return_pct",
            "total_cost", "max_drawdown_pct",
            "sharpe_ratio", "total_trades", "turnover",
        ])
        writer.writerow([
            result.phase, result.start_date, result.end_date,
            result.trading_days, result.blogs_used, result.blogs_skipped,
            result.initial_capital, result.final_value,
            round(result.total_return_pct, 4),
            round(result.gross_return_pct, 4),
            round(result.total_cost, 2),
            round(result.max_drawdown_pct, 4),
            round(result.sharpe_ratio, 4),
            result.total_trades,
            round(result.turnover, 4),
        ])

    # daily.csv
    daily_path = output_dir / "daily.csv"
    with open(daily_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "date", "total_value", "cash", "positions_value",
            "scenario", "trades_today",
        ])
        for snap in result.daily_snapshots:
            writer.writerow([
                snap.date, round(snap.total_value, 2),
                round(snap.cash, 2), round(snap.positions_value, 2),
                snap.scenario, snap.trades_today,
            ])

    # trades.csv (all individual trade records)
    trades_path = output_dir / "trades.csv"
    with open(trades_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "date", "symbol", "side", "shares", "price", "value", "cost", "reason",
        ])
        for tr in result.trade_records:
            writer.writerow([
                tr.date, tr.symbol, tr.side,
                round(tr.shares, 6), round(tr.price, 4),
                round(tr.value, 2), round(tr.cost, 4), tr.reason,
            ])


def print_comparison_table(
    strategy_results: dict[str, BacktestResult],
    benchmark_results: dict[str, BacktestResult],
) -> str:
    """Print a comparison table of strategies vs benchmarks. Returns the string."""
    all_results = {**strategy_results, **benchmark_results}

    lines: list[str] = []
    lines.append("=== Strategy vs Benchmarks ===")
    header = f"{'Name':<20}| {'Gross':>7} | {'Net':>7} | {'Max DD':>7} | {'Sharpe':>6} | {'Trades':>6} | {'Turnover':>8} | {'Costs':>8}"
    lines.append(header)
    lines.append("-" * len(header))

    for name, r in all_results.items():
        g_sign = "+" if r.gross_return_pct >= 0 else ""
        n_sign = "+" if r.total_return_pct >= 0 else ""
        lines.append(
            f"{name:<20}| {g_sign}{r.gross_return_pct:>5.2f}% | {n_sign}{r.total_return_pct:>5.2f}% | "
            f"{r.max_drawdown_pct:>6.2f}% | {r.sharpe_ratio:>6.2f} | {r.total_trades:>6} | "
            f"{r.turnover:>8.2f} | ${r.total_cost:>7.2f}"
        )

    lines.append("")
    output = "\n".join(lines)
    print(output)
    return output
