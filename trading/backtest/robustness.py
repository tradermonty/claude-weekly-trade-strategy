"""Cost sensitivity matrix and robustness report generation."""

from __future__ import annotations

import csv
import logging
from dataclasses import replace
from pathlib import Path

from trading.backtest.config import BacktestConfig, CostModel
from trading.backtest.data_provider import DataProvider
from trading.backtest.engine import PhaseAEngine, PhaseBEngine
from trading.backtest.metrics import BacktestResult
from trading.backtest.strategy_timeline import StrategyTimeline

logger = logging.getLogger(__name__)


def run_cost_matrix(
    timeline: StrategyTimeline,
    data_provider: DataProvider,
    base_config: BacktestConfig,
    cost_levels_bps: list[float] | None = None,
) -> list[dict]:
    """Run 4 modes x N cost levels. Returns list of {mode, cost_bps, result}."""
    if cost_levels_bps is None:
        cost_levels_bps = [0, 2, 5, 10, 20]

    modes = [
        ("A-transition", "A", "transition"),
        ("A-friday", "A", "week_end"),
        ("B-transition", "B", "transition"),
        ("B-friday", "B", "week_end"),
    ]

    results: list[dict] = []

    for mode_name, phase, timing in modes:
        for cost_bps in cost_levels_bps:
            config = replace(
                base_config,
                phase=phase,
                rebalance_timing=timing,
                cost_model=CostModel(spread_bps=cost_bps),
            )

            if phase == "A":
                engine = PhaseAEngine(config, timeline, data_provider)
            else:
                engine = PhaseBEngine(config, timeline, data_provider)

            result = engine.run()
            results.append({
                "mode": mode_name,
                "cost_bps": cost_bps,
                "result": result,
            })
            logger.info(
                "%s @ %d bps: net=%.2f%%, gross=%.2f%%",
                mode_name, cost_bps,
                result.total_return_pct, result.gross_return_pct,
            )

    return results


def find_breakeven(results: list[dict]) -> dict:
    """Find cost level where B-transition net return falls below A-transition.

    Returns {breakeven_bps, b_at_zero, a_at_zero, details}.
    """
    b_results = {r["cost_bps"]: r["result"] for r in results if r["mode"] == "B-transition"}
    a_results = {r["cost_bps"]: r["result"] for r in results if r["mode"] == "A-transition"}

    if not b_results or not a_results:
        return {"breakeven_bps": None, "b_at_zero": None, "a_at_zero": None, "details": "Missing mode data"}

    common_costs = sorted(set(b_results.keys()) & set(a_results.keys()))
    if not common_costs:
        return {"breakeven_bps": None, "b_at_zero": None, "a_at_zero": None, "details": "No common cost levels"}

    b_zero = b_results.get(0)
    a_zero = a_results.get(0)

    # Find crossover: B net_return < A net_return
    breakeven_bps = None
    for i in range(len(common_costs) - 1):
        c1, c2 = common_costs[i], common_costs[i + 1]
        diff1 = b_results[c1].total_return_pct - a_results[c1].total_return_pct
        diff2 = b_results[c2].total_return_pct - a_results[c2].total_return_pct

        if diff1 >= 0 and diff2 < 0:
            # Linear interpolation
            if diff1 != diff2:
                breakeven_bps = c1 + (c2 - c1) * (diff1 / (diff1 - diff2))
            else:
                breakeven_bps = c1
            break

    # If B never falls below A, breakeven is beyond tested range
    if breakeven_bps is None:
        last_diff = b_results[common_costs[-1]].total_return_pct - a_results[common_costs[-1]].total_return_pct
        if last_diff >= 0:
            details = f"B-transition still ahead at {common_costs[-1]} bps (diff: {last_diff:.2f}%)"
        else:
            details = f"B-transition already behind at {common_costs[0]} bps"
    else:
        details = f"Crossover at ~{breakeven_bps:.1f} bps"

    return {
        "breakeven_bps": breakeven_bps,
        "b_at_zero": b_zero.total_return_pct if b_zero else None,
        "a_at_zero": a_zero.total_return_pct if a_zero else None,
        "details": details,
    }


def write_cost_matrix_csv(results: list[dict], path: Path) -> None:
    """Write cost matrix results to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "mode", "cost_bps", "gross_return", "net_return",
            "max_dd", "sharpe", "trades", "turnover", "total_cost",
        ])
        for r in results:
            res: BacktestResult = r["result"]
            writer.writerow([
                r["mode"], r["cost_bps"],
                round(res.gross_return_pct, 4),
                round(res.total_return_pct, 4),
                round(res.max_drawdown_pct, 4),
                round(res.sharpe_ratio, 4),
                res.total_trades,
                round(res.turnover, 4),
                round(res.total_cost, 2),
            ])


def generate_robustness_report(
    strategy_results: dict[str, BacktestResult],
    cost_matrix_results: list[dict],
    benchmark_results: dict[str, BacktestResult],
    breakeven: dict,
    output_path: Path,
) -> None:
    """Generate the final robustness assessment report as Markdown."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine judgment
    judgment = _determine_judgment(strategy_results, benchmark_results, breakeven)

    lines: list[str] = []

    # 1. Executive Summary
    lines.append("# Backtest Robustness Report")
    lines.append("")
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append(f"**Judgment: {judgment['verdict']}**")
    lines.append("")
    for reason in judgment["reasons"]:
        lines.append(f"- {reason}")
    lines.append("")

    # 2. Strategy Comparison (0 bps + 5 bps)
    lines.append("## 2. Strategy Comparison")
    lines.append("")
    lines.append("### At 0 bps (gross)")
    lines.append("")
    _append_result_table(lines, {
        r["mode"]: r["result"] for r in cost_matrix_results if r["cost_bps"] == 0
    })

    cost_5 = {r["mode"]: r["result"] for r in cost_matrix_results if r["cost_bps"] == 5}
    if cost_5:
        lines.append("### At 5 bps spread")
        lines.append("")
        _append_result_table(lines, cost_5)

    # 3. Cost Sensitivity
    lines.append("## 3. Cost Sensitivity")
    lines.append("")
    lines.append(f"- Breakeven: {breakeven['details']}")
    if breakeven.get("breakeven_bps") is not None:
        lines.append(f"- Breakeven spread: {breakeven['breakeven_bps']:.1f} bps")
    lines.append("")

    # Cost matrix table
    lines.append("| Mode | 0 bps | 2 bps | 5 bps | 10 bps | 20 bps |")
    lines.append("|------|-------|-------|-------|--------|--------|")
    modes_seen: dict[str, dict[float, float]] = {}
    for r in cost_matrix_results:
        mode = r["mode"]
        if mode not in modes_seen:
            modes_seen[mode] = {}
        modes_seen[mode][r["cost_bps"]] = r["result"].total_return_pct

    for mode, costs in modes_seen.items():
        row = f"| {mode} |"
        for bps in [0, 2, 5, 10, 20]:
            val = costs.get(bps)
            if val is not None:
                row += f" {val:+.2f}% |"
            else:
                row += " N/A |"
        lines.append(row)
    lines.append("")

    # 4. Benchmark Comparison
    lines.append("## 4. Benchmark Comparison")
    lines.append("")
    _append_result_table(lines, benchmark_results)

    # Best strategy (B-transition at 5 bps or first available)
    best_strat = next(
        (r["result"] for r in cost_matrix_results
         if r["mode"] == "B-transition" and r["cost_bps"] == 5),
        next((r["result"] for r in cost_matrix_results if r["cost_bps"] == 5), None),
    )
    if best_strat:
        lines.append(f"**B-transition (5 bps)**: net {best_strat.total_return_pct:+.2f}%, "
                     f"Sharpe {best_strat.sharpe_ratio:.2f}, "
                     f"MaxDD {best_strat.max_drawdown_pct:.2f}%")
        lines.append("")

    # 5. Robustness Assessment
    lines.append("## 5. Robustness Assessment")
    lines.append("")
    lines.append("### Strengths")
    for s in judgment.get("strengths", []):
        lines.append(f"- {s}")
    lines.append("")
    lines.append("### Weaknesses")
    for w in judgment.get("weaknesses", []):
        lines.append(f"- {w}")
    lines.append("")

    # 6. Recommendation
    lines.append("## 6. Recommendation")
    lines.append("")
    for rec in judgment.get("recommendations", []):
        lines.append(f"- {rec}")
    lines.append("")

    # 7. Data Limitation
    lines.append("## 7. Data Limitation")
    lines.append("")
    lines.append("- Backtest period: ~15 weeks (statistically limited)")
    lines.append("- No out-of-sample validation (insufficient data for split)")
    lines.append("- Results may not generalize to different market regimes")
    lines.append("- Transaction costs are estimated (actual may vary by time of day, liquidity)")
    lines.append("")

    output_path.write_text("\n".join(lines))
    logger.info("Robustness report written to %s", output_path)


def _determine_judgment(
    strategy_results: dict[str, BacktestResult],
    benchmark_results: dict[str, BacktestResult],
    breakeven: dict,
) -> dict:
    """Determine Adopt/Conditional/Reject verdict."""
    b_trans = strategy_results.get("B-transition")
    spy = benchmark_results.get("SPY B&H")

    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []
    reasons: list[str] = []

    # Check if strategy beats all benchmarks on Sharpe
    if b_trans:
        beats_all_sharpe = all(
            b_trans.sharpe_ratio > bm.sharpe_ratio
            for bm in benchmark_results.values()
        )
        beats_spy_return = spy and b_trans.total_return_pct > spy.total_return_pct

        if beats_all_sharpe:
            strengths.append("B-transition Sharpe exceeds all benchmarks")
        if beats_spy_return:
            strengths.append("B-transition net return exceeds SPY B&H")

        be_bps = breakeven.get("breakeven_bps")
        if be_bps is not None and be_bps >= 5:
            strengths.append(f"Cost-robust up to {be_bps:.0f} bps spread")
        elif be_bps is not None and be_bps < 5:
            weaknesses.append(f"Cost-sensitive: breakeven at {be_bps:.1f} bps")

        better_dd = spy and abs(b_trans.max_drawdown_pct) < abs(spy.max_drawdown_pct)
        if better_dd:
            strengths.append("Lower max drawdown than SPY")
        elif spy:
            weaknesses.append("Larger max drawdown than SPY")

    weaknesses.append("Limited backtest period (~15 weeks)")

    # Verdict
    if b_trans and all([
        all(b_trans.sharpe_ratio > bm.sharpe_ratio for bm in benchmark_results.values()),
        breakeven.get("breakeven_bps") is None or breakeven.get("breakeven_bps", 0) >= 5,
    ]):
        verdict = "ADOPT"
        reasons.append("B-transition outperforms all benchmarks on risk-adjusted basis")
        reasons.append("Cost-robust at realistic spread levels (<=5 bps)")
        recommendations.append("Deploy B-transition with spread_bps=1 (SPY/QQQ typical)")
        recommendations.append("Monitor turnover and actual costs monthly")
    elif b_trans and spy and b_trans.total_return_pct > spy.total_return_pct:
        verdict = "CONDITIONAL ADOPT"
        reasons.append("Strategy outperforms SPY but with caveats")
        recommendations.append("Use with caution; monitor cost sensitivity")
        recommendations.append("Consider A-transition if costs exceed breakeven")
    else:
        verdict = "REJECT"
        reasons.append("Strategy does not outperform SPY B&H on risk-adjusted basis")
        recommendations.append("Review strategy logic and triggers")
        recommendations.append("Consider simplifying to reduce trading costs")

    return {
        "verdict": verdict,
        "reasons": reasons,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
    }


def _append_result_table(lines: list[str], results: dict[str, BacktestResult]) -> None:
    """Append a Markdown table of results."""
    lines.append("| Name | Net Return | Gross Return | Max DD | Sharpe | Trades | Turnover |")
    lines.append("|------|-----------|-------------|--------|--------|--------|----------|")
    for name, r in results.items():
        lines.append(
            f"| {name} | {r.total_return_pct:+.2f}% | {r.gross_return_pct:+.2f}% | "
            f"{r.max_drawdown_pct:.2f}% | {r.sharpe_ratio:.2f} | "
            f"{r.total_trades} | {r.turnover:.2f} |"
        )
    lines.append("")
