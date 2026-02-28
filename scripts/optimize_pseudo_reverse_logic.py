#!/usr/bin/env python3
"""Optimize pseudo blog reverse-generation logic and re-run validation.

Workflow:
1) Generate candidate pseudo blogs with different regime/allocation parameters.
2) Evaluate on train period (2019-2023) with walk-forward metrics.
3) Select top-k on train objective.
4) Re-evaluate top-k on holdout (2024-2026), choose best holdout candidate.
5) Run full-period evaluation for the selected best candidate.
"""

from __future__ import annotations

import argparse
import csv
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from scripts.generate_pseudo_historical_blogs import (
    ETF_SYMBOLS,
    GenerationParams,
    generate_pseudo_blogs,
)
from trading.backtest.config import BacktestConfig, CostModel
from trading.backtest.data_provider import DataProvider
from trading.backtest.strategy_timeline import StrategyTimeline
from trading.backtest.walk_forward import WalkForwardConfig, WalkForwardValidator
from trading.config import AlpacaConfig, FMPConfig


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    profile: str
    sensitivity: str
    tilt_scale: float
    params: GenerationParams


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Optimize pseudo reverse-generation logic")
    p.add_argument("--start", type=date.fromisoformat, default=date(2019, 7, 8))
    p.add_argument("--end", type=date.fromisoformat, default=date(2026, 2, 20))
    p.add_argument("--train-end", type=date.fromisoformat, default=date(2023, 12, 29))
    p.add_argument("--holdout-start", type=date.fromisoformat, default=date(2024, 1, 1))
    p.add_argument("--top-k", type=int, default=5, help="Top candidates selected from train phase")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/pseudo_generation_optimization"),
    )
    return p.parse_args()


def build_profiles() -> dict[str, dict[str, dict[str, float]]]:
    return {
        "balanced": {
            "bull": {"SPY": 30, "QQQ": 20, "DIA": 7, "XLV": 9, "XLP": 5, "GLD": 8, "XLE": 11, "BIL": 10},
            "base": {"SPY": 28, "QQQ": 14, "DIA": 8, "XLV": 11, "XLP": 9, "GLD": 10, "XLE": 8, "BIL": 12},
            "bear": {"SPY": 21, "QQQ": 8, "DIA": 9, "XLV": 14, "XLP": 13, "GLD": 12, "XLE": 7, "BIL": 16},
            "tail_risk": {"SPY": 14, "QQQ": 4, "DIA": 8, "XLV": 16, "XLP": 16, "GLD": 14, "XLE": 6, "BIL": 22},
        },
        "pro_risk": {
            "bull": {"SPY": 33, "QQQ": 24, "DIA": 7, "XLV": 7, "XLP": 4, "GLD": 7, "XLE": 10, "BIL": 8},
            "base": {"SPY": 31, "QQQ": 18, "DIA": 9, "XLV": 9, "XLP": 7, "GLD": 8, "XLE": 9, "BIL": 9},
            "bear": {"SPY": 24, "QQQ": 11, "DIA": 10, "XLV": 13, "XLP": 11, "GLD": 12, "XLE": 7, "BIL": 12},
            "tail_risk": {"SPY": 17, "QQQ": 6, "DIA": 9, "XLV": 15, "XLP": 15, "GLD": 14, "XLE": 6, "BIL": 18},
        },
        "defensive": {
            "bull": {"SPY": 27, "QQQ": 16, "DIA": 8, "XLV": 11, "XLP": 8, "GLD": 10, "XLE": 10, "BIL": 10},
            "base": {"SPY": 24, "QQQ": 11, "DIA": 9, "XLV": 14, "XLP": 12, "GLD": 12, "XLE": 8, "BIL": 10},
            "bear": {"SPY": 18, "QQQ": 6, "DIA": 9, "XLV": 17, "XLP": 15, "GLD": 14, "XLE": 7, "BIL": 14},
            "tail_risk": {"SPY": 11, "QQQ": 3, "DIA": 8, "XLV": 18, "XLP": 18, "GLD": 16, "XLE": 6, "BIL": 20},
        },
    }


def build_candidates() -> list[Candidate]:
    profiles = build_profiles()
    sensitivities = [
        ("base", -2, 4, 7),
        ("risk_sensitive", -2, 3, 6),
        ("risk_slow", -1, 5, 8),
        ("bull_friendly", -3, 4, 7),
    ]
    tilt_scales = [0.75, 1.0, 1.25]

    candidates: list[Candidate] = []
    idx = 1
    for profile_name, alloc in profiles.items():
        for sens_name, cut_bull, cut_bear, cut_tail in sensitivities:
            for scale in tilt_scales:
                params = GenerationParams(
                    name=f"{profile_name}_{sens_name}_x{scale:.2f}",
                    regime_allocations=deepcopy(alloc),
                    score_cut_bull=cut_bull,
                    score_cut_bear=cut_bear,
                    score_cut_tail=cut_tail,
                    tech_rel_threshold=0.03,
                    tech_tilt=2.0 * scale,
                    energy_rel_threshold=0.02,
                    energy_tilt=2.0 * scale,
                    gold_strength_threshold=0.04,
                    gold_tilt=2.0 * scale,
                    bear_cash_boost=2.0,
                )
                candidates.append(
                    Candidate(
                        candidate_id=f"cand_{idx:02d}",
                        profile=profile_name,
                        sensitivity=sens_name,
                        tilt_scale=scale,
                        params=params,
                    )
                )
                idx += 1
    return candidates


def build_provider(start: date, end: date) -> DataProvider:
    alpaca = AlpacaConfig.from_env()
    fmp = FMPConfig.from_env()
    provider = DataProvider(alpaca, fmp, Path(".backtest_cache"))
    buffer_start = start - timedelta(days=420)
    provider.load_etf_data(ETF_SYMBOLS, buffer_start, end)
    provider.load_fmp_data(buffer_start, end)
    return provider


def evaluate_candidate(
    blogs_dir: Path,
    provider: DataProvider,
    start: date,
    end: date,
) -> dict[str, float | str]:
    timeline = StrategyTimeline()
    timeline.build(blogs_dir)
    if not timeline.entries or not timeline.effective_start:
        return {
            "status": "invalid",
            "p_value": 1.0,
            "win_rate": 0.0,
            "mean_weekly_excess": 0.0,
            "information_ratio": 0.0,
            "strategy_return": 0.0,
            "spy_return": 0.0,
            "trading_days": 0.0,
        }

    run_start = max(start, timeline.effective_start)
    if run_start >= end:
        return {
            "status": "too_short",
            "p_value": 1.0,
            "win_rate": 0.0,
            "mean_weekly_excess": 0.0,
            "information_ratio": 0.0,
            "strategy_return": 0.0,
            "spy_return": 0.0,
            "trading_days": 0.0,
        }

    config = BacktestConfig(
        start=run_start,
        end=end,
        initial_capital=100_000,
        phase="B",
        blogs_dir=blogs_dir,
        cost_model=CostModel(spread_bps=1.0),
    )
    wf = WalkForwardValidator(config, WalkForwardConfig(), timeline, provider)
    result = wf.run()

    return {
        "status": "ok",
        "p_value": float(result.p_value),
        "win_rate": float(result.win_rate),
        "mean_weekly_excess": float(result.mean_weekly_excess),
        "information_ratio": float(result.information_ratio),
        "strategy_return": float(result.full_period.total_return_pct),
        "spy_return": float(result.full_spy.total_return_pct),
        "trading_days": float(result.full_period.trading_days),
    }


def train_objective(m: dict[str, float | str]) -> float:
    if m["status"] != "ok":
        return -999.0
    mean_excess = float(m["mean_weekly_excess"])
    win_rate = float(m["win_rate"])
    p_value = float(m["p_value"])
    # Higher excess + better win rate + lower p-value
    return (mean_excess * 100.0) + ((win_rate - 0.5) * 20.0) - (p_value * 5.0)


def main() -> None:
    args = parse_args()
    out_dir = args.output_dir
    cand_dir = out_dir / "candidates"
    cand_dir.mkdir(parents=True, exist_ok=True)

    provider = build_provider(args.start, args.end)
    candidates = build_candidates()
    rows: list[dict[str, object]] = []

    print(f"Candidates: {len(candidates)}")
    for cand in candidates:
        run_dir = cand_dir / cand.candidate_id
        gen_count, skip_count = generate_pseudo_blogs(
            start=args.start,
            end=args.end,
            output_dir=run_dir,
            overwrite=True,
            warmup_days=120,
            params=cand.params,
        )
        train_metrics = evaluate_candidate(run_dir, provider, args.start, args.train_end)
        score = train_objective(train_metrics)
        row: dict[str, object] = {
            "candidate_id": cand.candidate_id,
            "profile": cand.profile,
            "sensitivity": cand.sensitivity,
            "tilt_scale": cand.tilt_scale,
            "generated": gen_count,
            "skipped": skip_count,
            "train_score": score,
            **{f"train_{k}": v for k, v in train_metrics.items()},
            "params": cand.params,
            "blogs_dir": run_dir.as_posix(),
        }
        rows.append(row)
        print(
            f"{cand.candidate_id} train: score={score:.4f}, "
            f"p={float(train_metrics['p_value']):.4f}, "
            f"excess={float(train_metrics['mean_weekly_excess']):+.4f}%"
        )

    rows_sorted = sorted(rows, key=lambda r: float(r["train_score"]), reverse=True)
    top = rows_sorted[: max(1, args.top_k)]

    print(f"Top-{len(top)} candidates -> holdout evaluation")
    for row in top:
        holdout_metrics = evaluate_candidate(
            Path(str(row["blogs_dir"])),
            provider,
            args.holdout_start,
            args.end,
        )
        row.update({f"holdout_{k}": v for k, v in holdout_metrics.items()})
        print(
            f"{row['candidate_id']} holdout: p={float(holdout_metrics['p_value']):.4f}, "
            f"excess={float(holdout_metrics['mean_weekly_excess']):+.4f}%"
        )

    top_ok = [r for r in top if r.get("holdout_status") == "ok"]
    if not top_ok:
        raise SystemExit("No valid holdout candidates")

    best = sorted(
        top_ok,
        key=lambda r: (
            float(r["holdout_mean_weekly_excess"]),
            -float(r["holdout_p_value"]),
            float(r["holdout_win_rate"]),
        ),
        reverse=True,
    )[0]

    best_dir = Path(str(best["blogs_dir"]))
    full_metrics = evaluate_candidate(best_dir, provider, args.start, args.end)
    best.update({f"full_{k}": v for k, v in full_metrics.items()})

    # Persist summary artifacts
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_csv = out_dir / "optimization_summary.csv"
    fieldnames = [
        "candidate_id",
        "profile",
        "sensitivity",
        "tilt_scale",
        "generated",
        "skipped",
        "train_score",
        "train_status",
        "train_p_value",
        "train_win_rate",
        "train_mean_weekly_excess",
        "train_information_ratio",
        "train_strategy_return",
        "train_spy_return",
        "holdout_status",
        "holdout_p_value",
        "holdout_win_rate",
        "holdout_mean_weekly_excess",
        "holdout_information_ratio",
        "holdout_strategy_return",
        "holdout_spy_return",
        "blogs_dir",
    ]
    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows_sorted:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    best_json = out_dir / "best_candidate.json"
    best_payload = {
        "candidate_id": best["candidate_id"],
        "profile": best["profile"],
        "sensitivity": best["sensitivity"],
        "tilt_scale": best["tilt_scale"],
        "blogs_dir": best["blogs_dir"],
        "train": {
            "p_value": best["train_p_value"],
            "win_rate": best["train_win_rate"],
            "mean_weekly_excess": best["train_mean_weekly_excess"],
            "strategy_return": best["train_strategy_return"],
            "spy_return": best["train_spy_return"],
        },
        "holdout": {
            "p_value": best.get("holdout_p_value"),
            "win_rate": best.get("holdout_win_rate"),
            "mean_weekly_excess": best.get("holdout_mean_weekly_excess"),
            "strategy_return": best.get("holdout_strategy_return"),
            "spy_return": best.get("holdout_spy_return"),
        },
        "full": {
            "p_value": best.get("full_p_value"),
            "win_rate": best.get("full_win_rate"),
            "mean_weekly_excess": best.get("full_mean_weekly_excess"),
            "strategy_return": best.get("full_strategy_return"),
            "spy_return": best.get("full_spy_return"),
        },
        "params": {
            "name": best["params"].name,
            "score_cut_bull": best["params"].score_cut_bull,
            "score_cut_bear": best["params"].score_cut_bear,
            "score_cut_tail": best["params"].score_cut_tail,
            "tech_rel_threshold": best["params"].tech_rel_threshold,
            "tech_tilt": best["params"].tech_tilt,
            "energy_rel_threshold": best["params"].energy_rel_threshold,
            "energy_tilt": best["params"].energy_tilt,
            "gold_strength_threshold": best["params"].gold_strength_threshold,
            "gold_tilt": best["params"].gold_tilt,
            "bear_cash_boost": best["params"].bear_cash_boost,
            "regime_allocations": best["params"].regime_allocations,
        },
    }
    best_json.write_text(json.dumps(best_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report_md = out_dir / "optimization_report.md"
    report_md.write_text(
        "\n".join(
            [
                "# Pseudo Reverse Logic Optimization",
                "",
                f"- Search candidates: {len(candidates)}",
                f"- Train period: {args.start} -> {args.train_end}",
                f"- Holdout period: {args.holdout_start} -> {args.end}",
                "",
                "## Best Candidate",
                "",
                f"- ID: {best['candidate_id']}",
                f"- Profile: {best['profile']}",
                f"- Sensitivity: {best['sensitivity']}",
                f"- Tilt scale: {best['tilt_scale']}",
                f"- Blogs dir: `{best['blogs_dir']}`",
                "",
                "## Train Metrics",
                "",
                f"- p-value: {float(best['train_p_value']):.4f}",
                f"- Win rate: {float(best['train_win_rate']):.2%}",
                f"- Mean weekly excess: {float(best['train_mean_weekly_excess']):+.4f}%",
                f"- Strategy return: {float(best['train_strategy_return']):+.2f}%",
                f"- SPY return: {float(best['train_spy_return']):+.2f}%",
                "",
                "## Holdout Metrics",
                "",
                f"- p-value: {float(best.get('holdout_p_value', 1.0)):.4f}",
                f"- Win rate: {float(best.get('holdout_win_rate', 0.0)):.2%}",
                f"- Mean weekly excess: {float(best.get('holdout_mean_weekly_excess', 0.0)):+.4f}%",
                f"- Strategy return: {float(best.get('holdout_strategy_return', 0.0)):+.2f}%",
                f"- SPY return: {float(best.get('holdout_spy_return', 0.0)):+.2f}%",
                "",
                "## Full Period Metrics",
                "",
                f"- p-value: {float(best.get('full_p_value', 1.0)):.4f}",
                f"- Win rate: {float(best.get('full_win_rate', 0.0)):.2%}",
                f"- Mean weekly excess: {float(best.get('full_mean_weekly_excess', 0.0)):+.4f}%",
                f"- Strategy return: {float(best.get('full_strategy_return', 0.0)):+.2f}%",
                f"- SPY return: {float(best.get('full_spy_return', 0.0)):+.2f}%",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Best candidate: {best['candidate_id']}")
    print(f"Summary CSV: {summary_csv}")
    print(f"Best JSON: {best_json}")
    print(f"Report: {report_md}")


if __name__ == "__main__":
    main()
