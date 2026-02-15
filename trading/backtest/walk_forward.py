"""Walk-forward validation: sub-period consistency + statistical significance."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from trading.backtest.metrics import BacktestResult


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward validation."""

    window_weeks: int = 6
    step_weeks: int = 2
    min_weeks: int = 4


@dataclass
class WeeklyExcess:
    """Per-week excess return vs SPY."""

    week_date: date
    strategy_return_pct: float
    spy_return_pct: float
    excess_pct: float


@dataclass
class WindowResult:
    """Metrics for one rolling/expanding window."""

    start_date: date
    end_date: date
    weeks: int
    strategy_return_pct: float
    spy_return_pct: float
    excess_return_pct: float
    sharpe: float
    max_dd_pct: float


@dataclass
class WalkForwardResult:
    """Complete walk-forward validation result."""

    # Full period
    full_period: BacktestResult
    full_spy: BacktestResult
    # Weekly
    weekly_excess: list[WeeklyExcess] = field(default_factory=list)
    win_rate: float = 0.0
    mean_weekly_excess: float = 0.0
    # Rolling
    rolling_windows: list[WindowResult] = field(default_factory=list)
    # Expanding
    expanding_windows: list[WindowResult] = field(default_factory=list)
    # Statistical tests
    t_statistic: float = 0.0
    p_value: float = 1.0
    information_ratio: float = 0.0
    # Verdict
    verdict: str = "NOT_SIGNIFICANT"
    verdict_detail: str = ""


class WalkForwardValidator:
    """Run walk-forward validation on a backtest strategy."""

    def __init__(
        self,
        config,  # BacktestConfig
        wf_config: WalkForwardConfig,
        timeline,  # StrategyTimeline
        data_provider,  # DataProvider
    ) -> None:
        self._config = config
        self._wf_config = wf_config
        self._timeline = timeline
        self._data = data_provider

    def run(self) -> WalkForwardResult:
        """Run all validation steps."""
        from trading.backtest.benchmark import BenchmarkEngine
        from trading.backtest.engine import PhaseAEngine, PhaseBEngine

        # 1. Full period strategy
        if self._config.phase == "B":
            engine = PhaseBEngine(self._config, self._timeline, self._data)
        else:
            engine = PhaseAEngine(self._config, self._timeline, self._data)
        full_result = engine.run()

        # 2. Full period SPY B&H
        bench = BenchmarkEngine(
            self._data, self._config.start, self._config.end,
            self._config.initial_capital,
        )
        spy_result = bench.run_buy_and_hold("SPY")

        # 3. Build snapshot value maps
        strat_values = {s.date: s.total_value for s in full_result.daily_snapshots}
        spy_values = {s.date: s.total_value for s in spy_result.daily_snapshots}

        # Transition days within backtest period
        all_trans = self._timeline.get_all_transition_days()
        trans = [d for d in all_trans if self._config.start <= d <= self._config.end]

        # 4. Weekly excess
        weekly = compute_weekly_excess(
            strat_values, spy_values, trans, self._config.end,
        )
        win_rate = compute_win_rate(weekly)
        mean_excess = compute_mean_excess(weekly)

        # 5. Rolling windows
        rolling = compute_rolling_windows(
            strat_values, spy_values, trans,
            self._wf_config.window_weeks,
            self._wf_config.step_weeks,
            self._config.end,
        )

        # 6. Expanding windows
        expanding = compute_expanding_windows(
            strat_values, spy_values, trans,
            self._wf_config.min_weeks,
            self._wf_config.step_weeks,
            self._config.end,
        )

        # 7. Statistical tests on daily excess returns
        daily_excess = extract_daily_excess(strat_values, spy_values)
        t_stat, p_val = paired_t_test(daily_excess)
        ir = information_ratio(daily_excess)

        # 8. Verdict
        verdict, detail = determine_verdict(
            p_val, win_rate, rolling, len(daily_excess),
        )

        return WalkForwardResult(
            full_period=full_result,
            full_spy=spy_result,
            weekly_excess=weekly,
            win_rate=win_rate,
            mean_weekly_excess=mean_excess,
            rolling_windows=rolling,
            expanding_windows=expanding,
            t_statistic=t_stat,
            p_value=p_val,
            information_ratio=ir,
            verdict=verdict,
            verdict_detail=detail,
        )


# --- Pure functions (testable without engine) ---


def compute_weekly_excess(
    strat_values: dict[date, float],
    spy_values: dict[date, float],
    transition_days: list[date],
    end_date: date,
) -> list[WeeklyExcess]:
    """Compute per-week strategy vs SPY excess returns."""
    results: list[WeeklyExcess] = []
    sorted_strat_dates = sorted(strat_values.keys())

    for i, td in enumerate(transition_days):
        if i + 1 < len(transition_days):
            next_td = transition_days[i + 1]
            week_days = [d for d in sorted_strat_dates if td <= d < next_td]
        else:
            week_days = [d for d in sorted_strat_dates if td <= d <= end_date]

        if len(week_days) < 2:
            continue

        first_day = week_days[0]
        last_day = week_days[-1]

        s_start = strat_values.get(first_day)
        s_end = strat_values.get(last_day)
        spy_start = spy_values.get(first_day)
        spy_end = spy_values.get(last_day)

        if all(v is not None and v > 0 for v in [s_start, s_end, spy_start, spy_end]):
            s_ret = (s_end / s_start - 1) * 100
            spy_ret = (spy_end / spy_start - 1) * 100
            results.append(WeeklyExcess(
                week_date=td,
                strategy_return_pct=round(s_ret, 4),
                spy_return_pct=round(spy_ret, 4),
                excess_pct=round(s_ret - spy_ret, 4),
            ))

    return results


def compute_win_rate(weekly: list[WeeklyExcess]) -> float:
    """Fraction of weeks with positive excess return."""
    if not weekly:
        return 0.0
    wins = sum(1 for w in weekly if w.excess_pct > 0)
    return wins / len(weekly)


def compute_mean_excess(weekly: list[WeeklyExcess]) -> float:
    """Mean weekly excess return."""
    if not weekly:
        return 0.0
    return sum(w.excess_pct for w in weekly) / len(weekly)


def compute_rolling_windows(
    strat_values: dict[date, float],
    spy_values: dict[date, float],
    transition_days: list[date],
    window_weeks: int,
    step_weeks: int,
    end_date: date,
) -> list[WindowResult]:
    """Compute rolling window metrics."""
    results: list[WindowResult] = []
    n_trans = len(transition_days)

    for i in range(0, n_trans - window_weeks + 1, step_weeks):
        win_start = transition_days[i]
        if i + window_weeks < n_trans:
            next_trans = transition_days[i + window_weeks]
            win_end = _last_date_before(strat_values, next_trans)
        else:
            win_end = end_date

        if win_end is None or win_end <= win_start:
            continue

        wr = _compute_window_metrics(
            strat_values, spy_values, win_start, win_end, window_weeks,
        )
        if wr:
            results.append(wr)

    return results


def compute_expanding_windows(
    strat_values: dict[date, float],
    spy_values: dict[date, float],
    transition_days: list[date],
    min_weeks: int,
    step_weeks: int,
    end_date: date,
) -> list[WindowResult]:
    """Compute expanding window metrics (start fixed, end grows)."""
    if not transition_days:
        return []

    results: list[WindowResult] = []
    start = transition_days[0]
    n_trans = len(transition_days)

    for n_weeks in range(min_weeks, n_trans + 1, step_weeks):
        if n_weeks < n_trans:
            next_trans = transition_days[n_weeks]
            win_end = _last_date_before(strat_values, next_trans)
        else:
            win_end = end_date

        if win_end is None or win_end <= start:
            continue

        wr = _compute_window_metrics(
            strat_values, spy_values, start, win_end, n_weeks,
        )
        if wr:
            results.append(wr)

    return results


def extract_daily_excess(
    strat_values: dict[date, float],
    spy_values: dict[date, float],
) -> list[float]:
    """Extract daily excess returns (strategy - SPY)."""
    common_dates = sorted(set(strat_values.keys()) & set(spy_values.keys()))
    excess: list[float] = []

    for i in range(1, len(common_dates)):
        d_prev = common_dates[i - 1]
        d = common_dates[i]
        s_prev = strat_values[d_prev]
        s_curr = strat_values[d]
        spy_prev = spy_values[d_prev]
        spy_curr = spy_values[d]

        if s_prev > 0 and spy_prev > 0:
            s_ret = (s_curr / s_prev) - 1
            spy_ret = (spy_curr / spy_prev) - 1
            excess.append(s_ret - spy_ret)

    return excess


def paired_t_test(excess_returns: list[float]) -> tuple[float, float]:
    """One-sample t-test: H0 mean(excess) = 0. Returns (t_stat, p_value).

    Uses normal approximation for p-value via math.erfc (valid for n >= 30).
    """
    n = len(excess_returns)
    if n < 2:
        return 0.0, 1.0

    mean = sum(excess_returns) / n
    var = sum((r - mean) ** 2 for r in excess_returns) / (n - 1)
    se = math.sqrt(var / n) if var > 0 else 0.0

    if se == 0:
        return 0.0, 1.0

    t_stat = mean / se
    # Two-tailed p-value: P(|Z| > |t|) = erfc(|t| / sqrt(2))
    p_value = math.erfc(abs(t_stat) / math.sqrt(2))

    return t_stat, min(max(p_value, 0.0), 1.0)


def information_ratio(daily_excess: list[float]) -> float:
    """Annualized Information Ratio = mean(excess) / std(excess) * sqrt(252)."""
    n = len(daily_excess)
    if n < 2:
        return 0.0

    mean = sum(daily_excess) / n
    var = sum((r - mean) ** 2 for r in daily_excess) / n
    std = math.sqrt(var)

    if std == 0:
        return 0.0

    return (mean / std) * math.sqrt(252)


def determine_verdict(
    p_value: float,
    win_rate: float,
    rolling: list[WindowResult],
    n_days: int,
) -> tuple[str, str]:
    """Determine statistical verdict.

    SIGNIFICANT:     p < 0.05 AND win_rate >= 60%
    INCONCLUSIVE:    p < 0.10 OR win_rate >= 55%
    NOT_SIGNIFICANT: otherwise
    """
    positive_windows = sum(1 for w in rolling if w.excess_return_pct > 0)
    total_windows = len(rolling)

    if p_value < 0.05 and win_rate >= 0.60:
        detail = (
            f"p={p_value:.4f} < 0.05, win_rate={win_rate:.0%} >= 60%. "
            f"Rolling: {positive_windows}/{total_windows} windows positive."
        )
        return "SIGNIFICANT", detail

    if p_value < 0.10 or win_rate >= 0.55:
        detail = (
            f"p={p_value:.4f}, win_rate={win_rate:.0%}. "
            f"n={n_days} days insufficient for definitive conclusion. "
            f"Rolling: {positive_windows}/{total_windows} windows positive."
        )
        return "INCONCLUSIVE", detail

    detail = (
        f"p={p_value:.4f} >= 0.10, win_rate={win_rate:.0%} < 55%. "
        f"No evidence of consistent outperformance."
    )
    return "NOT_SIGNIFICANT", detail


def estimate_required_days(
    daily_excess: list[float],
    target_p: float = 0.05,
) -> int | None:
    """Estimate trading days needed for p < target_p, assuming stable mean/std."""
    n = len(daily_excess)
    if n < 2:
        return None

    mean = sum(daily_excess) / n
    if mean <= 0:
        return None

    var = sum((r - mean) ** 2 for r in daily_excess) / (n - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return None

    # t = mean / (std / sqrt(n)); need |t| > z for p < target_p
    z = _z_from_p(target_p)
    n_required = (z * std / mean) ** 2

    return max(int(math.ceil(n_required)), n + 1)


def write_walk_forward_report(result: WalkForwardResult, path: Path) -> None:
    """Write walk-forward validation report as Markdown."""
    path.parent.mkdir(parents=True, exist_ok=True)

    fp = result.full_period
    spy = result.full_spy

    lines: list[str] = []

    # Header
    lines.append("# Walk-Forward Validation Report")
    lines.append("")
    lines.append(
        f"Period: {fp.start_date} → {fp.end_date} "
        f"({len(result.weekly_excess)} weeks, {fp.trading_days} days)"
    )
    lines.append(f"Strategy: {fp.phase} @ ${fp.total_cost:.0f} total cost")
    lines.append("")

    # Section 1: Statistical Significance
    lines.append("## 1. Statistical Significance")
    lines.append("")

    daily_excess = extract_daily_excess(
        {s.date: s.total_value for s in fp.daily_snapshots},
        {s.date: s.total_value for s in spy.daily_snapshots},
    )
    mean_daily = sum(daily_excess) / len(daily_excess) * 100 if daily_excess else 0
    ann_excess = mean_daily * 252

    lines.append(f"- Daily excess return: {mean_daily:+.4f}% (ann. ~{ann_excess:+.1f}%)")
    lines.append(f"- t-statistic: {result.t_statistic:.2f}, p-value: {result.p_value:.4f}")
    lines.append(f"- Information Ratio: {result.information_ratio:.2f}")
    lines.append(f"- **Verdict: {result.verdict}**")
    lines.append(f"- {result.verdict_detail}")
    lines.append("")

    # Section 2: Per-Week Performance
    lines.append("## 2. Per-Week Performance")
    lines.append("")
    lines.append("| Week | Strategy | SPY | Excess | Win |")
    lines.append("|------|----------|-----|--------|-----|")
    for w in result.weekly_excess:
        win = "Y" if w.excess_pct > 0 else "N"
        lines.append(
            f"| {w.week_date} | {w.strategy_return_pct:+.2f}% | "
            f"{w.spy_return_pct:+.2f}% | {w.excess_pct:+.2f}% | {win} |"
        )
    lines.append("")
    wins = sum(1 for w in result.weekly_excess if w.excess_pct > 0)
    lines.append(
        f"Win Rate: {wins}/{len(result.weekly_excess)} ({result.win_rate:.0%})"
    )
    lines.append(f"Mean Weekly Excess: {result.mean_weekly_excess:+.2f}%")
    lines.append("")

    # Section 3: Rolling Windows
    lines.append("## 3. Rolling Windows")
    lines.append("")
    if result.rolling_windows:
        lines.append("| # | Period | Return | vs SPY | Sharpe | MaxDD |")
        lines.append("|---|--------|--------|--------|--------|-------|")
        for i, w in enumerate(result.rolling_windows, 1):
            lines.append(
                f"| {i} | {w.start_date} → {w.end_date} | "
                f"{w.strategy_return_pct:+.2f}% | {w.excess_return_pct:+.2f}% | "
                f"{w.sharpe:.2f} | {w.max_dd_pct:.2f}% |"
            )
        pos = sum(1 for w in result.rolling_windows if w.excess_return_pct > 0)
        lines.append("")
        lines.append(
            f"Consistency: {pos}/{len(result.rolling_windows)} "
            f"windows with positive excess"
        )
    else:
        lines.append("Insufficient data for rolling windows.")
    lines.append("")

    # Section 4: Expanding Window Stability
    lines.append("## 4. Expanding Window Stability")
    lines.append("")
    if result.expanding_windows:
        lines.append("| Weeks | Cum Return | Sharpe | Max DD |")
        lines.append("|-------|-----------|--------|--------|")
        for w in result.expanding_windows:
            lines.append(
                f"| {w.weeks} | {w.strategy_return_pct:+.2f}% | "
                f"{w.sharpe:.2f} | {w.max_dd_pct:.2f}% |"
            )
    else:
        lines.append("Insufficient data for expanding windows.")
    lines.append("")

    # Section 5: Required Sample Size
    lines.append("## 5. Required Sample Size")
    lines.append("")
    lines.append(f"Current: {fp.trading_days} days → p={result.p_value:.4f}")
    req = estimate_required_days(daily_excess)
    if req and req > fp.trading_days:
        extra_days = req - fp.trading_days
        extra_weeks = math.ceil(extra_days / 5)
        target_date = fp.end_date + timedelta(weeks=extra_weeks)
        lines.append(f"Estimated days for p<0.05: ~{req} days (~{req // 5} weeks)")
        lines.append(f"Target date: ~{target_date.isoformat()}")
    elif req:
        lines.append("Already at or near significance threshold.")
    else:
        lines.append("Cannot estimate (excess return non-positive or insufficient data).")
    lines.append("")

    path.write_text("\n".join(lines))


# --- Private helpers ---


def _z_from_p(p: float) -> float:
    """Approximate z-score for two-tailed p-value."""
    if p <= 0.01:
        return 2.576
    if p <= 0.05:
        return 1.960
    if p <= 0.10:
        return 1.645
    return 1.282


def _last_date_before(values: dict[date, float], boundary: date) -> date | None:
    """Find the last date in values that is strictly before boundary."""
    candidates = [d for d in values if d < boundary]
    return max(candidates) if candidates else None


def _compute_window_metrics(
    strat_values: dict[date, float],
    spy_values: dict[date, float],
    start: date,
    end: date,
    weeks: int,
) -> WindowResult | None:
    """Compute metrics for a single window period."""
    win_days = sorted(d for d in strat_values if start <= d <= end)
    if len(win_days) < 2:
        return None

    # Strategy return
    s_start = strat_values[win_days[0]]
    s_end = strat_values[win_days[-1]]
    s_ret = (s_end / s_start - 1) * 100 if s_start > 0 else 0.0

    # SPY return
    spy_start = spy_values.get(win_days[0])
    spy_end_val = spy_values.get(win_days[-1])
    spy_ret = 0.0
    if spy_start and spy_end_val and spy_start > 0:
        spy_ret = (spy_end_val / spy_start - 1) * 100

    # Sharpe
    daily_rets: list[float] = []
    for j in range(1, len(win_days)):
        prev_v = strat_values[win_days[j - 1]]
        curr_v = strat_values[win_days[j]]
        if prev_v > 0:
            daily_rets.append((curr_v / prev_v) - 1)

    sharpe = _compute_sharpe(daily_rets)

    # Max drawdown
    values_in_window = [strat_values[d] for d in win_days]
    max_dd = _compute_max_dd(values_in_window)

    return WindowResult(
        start_date=win_days[0],
        end_date=win_days[-1],
        weeks=weeks,
        strategy_return_pct=round(s_ret, 4),
        spy_return_pct=round(spy_ret, 4),
        excess_return_pct=round(s_ret - spy_ret, 4),
        sharpe=round(sharpe, 4),
        max_dd_pct=round(max_dd, 4),
    )


def _compute_sharpe(daily_returns: list[float]) -> float:
    """Annualized Sharpe ratio from daily returns."""
    if len(daily_returns) < 2:
        return 0.0
    mean = sum(daily_returns) / len(daily_returns)
    var = sum((r - mean) ** 2 for r in daily_returns) / len(daily_returns)
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(252)


def _compute_max_dd(values: list[float]) -> float:
    """Max drawdown as a negative percentage."""
    if not values:
        return 0.0
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = ((v - peak) / peak) * 100 if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
    return max_dd
