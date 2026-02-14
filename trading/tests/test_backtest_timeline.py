"""Tests for StrategyTimeline."""

from datetime import date
from pathlib import Path
from textwrap import dedent

import pytest

from trading.backtest.strategy_timeline import (
    StrategyTimeline,
    _validate_strategy,
    _first_trading_day_on_or_after,
)
from trading.data.models import ScenarioSpec, StrategySpec


# --- Helpers ---

def _make_spec(
    blog_date: str = "2026-01-05",
    allocation: dict | None = None,
    scenarios: dict | None = None,
) -> StrategySpec:
    if allocation is None:
        allocation = {"SPY": 40.0, "QQQ": 20.0, "BIL": 20.0, "GLD": 20.0}
    if scenarios is None:
        scenarios = {
            "base": ScenarioSpec("base", 50, [], allocation),
        }
    return StrategySpec(
        blog_date=blog_date,
        current_allocation=allocation,
        scenarios=scenarios,
        trading_levels={},
        stop_losses={},
        vix_triggers={},
        yield_triggers={},
    )


def _write_valid_blog(tmp_path: Path, date_str: str) -> Path:
    """Write a minimal valid blog file."""
    blog = tmp_path / f"{date_str}-weekly-strategy.md"
    content = dedent(f"""\
        # Weekly Strategy {date_str}

        ## セクター配分

        | カテゴリ | 比率 | 内訳 |
        |---------|------|------|
        | コア指数 | 40% | SPY 25%、QQQ 10%、DIA 5% |
        | 防御セクター | 20% | XLV 15%、XLP 5% |
        | テーマ・ヘッジ | 15% | GLD 8%、XLE 7% |
        | **現金・短期債** | 25% | BIL、MMF |

        ## シナリオ別プラン

        ### Base Case (50%)

        **トリガー**: VIX 17-20 + S&P 5,800台維持

        - **コア指数**: 40%
        - **防御セクター**: 20%
        - **テーマ**: 15%
        - **現金**: 25%

        ### Bull Case (25%)

        **トリガー**: VIX 17割れ + S&P 6,000突破

        - **コア指数**: 50%
        - **防御セクター**: 15%
        - **テーマ**: 20%
        - **現金**: 15%

        ### Bear Case (20%)

        **トリガー**: VIX 20超 + S&P 5,700割れ

        - **コア指数**: 30%
        - **防御セクター**: 25%
        - **テーマ**: 15%
        - **現金**: 30%

        ### Tail Risk (5%)

        **トリガー**: VIX 23超 + S&P 5,500割れ

        - **コア指数**: 20%
        - **防御セクター**: 25%
        - **テーマ**: 15%
        - **現金**: 40%
    """)
    blog.write_text(content, encoding="utf-8")
    return blog


def _write_invalid_blog(tmp_path: Path, date_str: str) -> Path:
    """Write a blog that will fail validation (early format, no matching patterns)."""
    blog = tmp_path / f"{date_str}-weekly-strategy.md"
    content = dedent(f"""\
        # Weekly Strategy {date_str}

        ## シナリオ

        ### シナリオA: 上昇継続
        レンジ 40-50% 株式配分

        ### シナリオB: 横ばい
        レンジ 30-40% 株式配分
    """)
    blog.write_text(content, encoding="utf-8")
    return blog


# --- Tests ---

class TestValidateStrategy:
    def test_valid_strategy(self):
        spec = _make_spec()
        assert _validate_strategy(spec) is None

    def test_empty_allocation(self):
        spec = _make_spec(allocation={})
        reason = _validate_strategy(spec)
        assert "empty" in reason

    def test_allocation_sum_too_low(self):
        spec = _make_spec(allocation={"SPY": 40.0})
        reason = _validate_strategy(spec)
        assert "outside 90-110% range" in reason

    def test_allocation_sum_too_high(self):
        spec = _make_spec(allocation={"SPY": 60.0, "QQQ": 60.0})
        reason = _validate_strategy(spec)
        assert "outside 90-110% range" in reason

    def test_allocation_sum_110_ok(self):
        spec = _make_spec(allocation={"SPY": 55.0, "QQQ": 55.0})
        assert _validate_strategy(spec) is None

    def test_no_scenarios(self):
        spec = _make_spec(scenarios={})
        reason = _validate_strategy(spec)
        assert "scenarios empty" in reason


class TestFirstTradingDayOnOrAfter:
    def test_weekday_returns_same(self):
        # 2026-01-05 is Monday
        assert _first_trading_day_on_or_after(date(2026, 1, 5)) == date(2026, 1, 5)

    def test_saturday_skips_to_monday(self):
        # 2026-01-10 is Saturday
        assert _first_trading_day_on_or_after(date(2026, 1, 10)) == date(2026, 1, 12)

    def test_sunday_skips_to_monday(self):
        # 2026-01-11 is Sunday
        assert _first_trading_day_on_or_after(date(2026, 1, 11)) == date(2026, 1, 12)

    def test_holiday_skips(self):
        # 2026-01-19 is MLK Day (Monday)
        assert _first_trading_day_on_or_after(date(2026, 1, 19)) == date(2026, 1, 20)


class TestStrategyTimelineBuild:
    def test_builds_from_valid_blogs(self, tmp_path):
        _write_valid_blog(tmp_path, "2026-01-05")
        _write_valid_blog(tmp_path, "2026-01-12")

        tl = StrategyTimeline()
        tl.build(tmp_path)
        assert len(tl.entries) == 2
        assert len(tl.skipped) == 0

    def test_skips_invalid_blogs(self, tmp_path):
        _write_invalid_blog(tmp_path, "2025-11-03")
        _write_valid_blog(tmp_path, "2026-01-05")

        tl = StrategyTimeline()
        tl.build(tmp_path)
        assert len(tl.entries) == 1
        assert len(tl.skipped) == 1
        assert tl.effective_start == date(2026, 1, 5)

    def test_excludes_backup_files(self, tmp_path):
        _write_valid_blog(tmp_path, "2026-01-05")
        # Create a _bk file
        bk = tmp_path / "2026-01-05-weekly-strategy_bk.md"
        bk.write_text("backup", encoding="utf-8")

        tl = StrategyTimeline()
        tl.build(tmp_path)
        assert len(tl.entries) == 1

    def test_empty_dir(self, tmp_path):
        tl = StrategyTimeline()
        tl.build(tmp_path)
        assert len(tl.entries) == 0
        assert tl.effective_start is None

    def test_nonexistent_dir(self):
        tl = StrategyTimeline()
        with pytest.raises(FileNotFoundError):
            tl.build(Path("/nonexistent/dir"))


class TestStrategyTimelineGetStrategy:
    def test_returns_active_strategy(self, tmp_path):
        _write_valid_blog(tmp_path, "2026-01-05")
        _write_valid_blog(tmp_path, "2026-01-12")

        tl = StrategyTimeline()
        tl.build(tmp_path)

        # Between first and second transition: first strategy
        strat = tl.get_strategy(date(2026, 1, 7))
        assert strat is not None
        assert strat.blog_date == "2026-01-05"

        # After second transition: second strategy
        strat = tl.get_strategy(date(2026, 1, 14))
        assert strat is not None
        assert strat.blog_date == "2026-01-12"

    def test_before_any_blog_returns_none(self, tmp_path):
        _write_valid_blog(tmp_path, "2026-01-12")

        tl = StrategyTimeline()
        tl.build(tmp_path)

        assert tl.get_strategy(date(2026, 1, 5)) is None


class TestStrategyTimelineTransitionDay:
    def test_is_transition_day(self, tmp_path):
        _write_valid_blog(tmp_path, "2026-01-05")

        tl = StrategyTimeline()
        tl.build(tmp_path)

        assert tl.is_transition_day(date(2026, 1, 5))
        assert not tl.is_transition_day(date(2026, 1, 6))

    def test_holiday_transition(self, tmp_path):
        # 2026-01-19 is MLK Day -> transition should be 2026-01-20
        _write_valid_blog(tmp_path, "2026-01-19")

        tl = StrategyTimeline()
        tl.build(tmp_path)

        assert not tl.is_transition_day(date(2026, 1, 19))
        assert tl.is_transition_day(date(2026, 1, 20))
