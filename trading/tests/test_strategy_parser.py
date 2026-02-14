"""Tests for the strategy_parser module.

Verifies that the parser correctly extracts structured data from the
Japanese-language weekly strategy blog markdown.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from trading.layer2.tools.strategy_parser import find_latest_blog, parse_blog
from trading.data.models import StrategySpec, ScenarioSpec, TradingLevel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent / "fixtures"
SAMPLE_BLOG_SRC = FIXTURE_DIR / "sample_blog.md"

# parse_blog extracts the date from the filename, so we must give it a
# properly named file (YYYY-MM-DD-weekly-strategy.md).
PROPER_BLOG_NAME = "2026-02-16-weekly-strategy.md"


@pytest.fixture
def blog_path(tmp_path: Path) -> Path:
    """Copy the sample blog to a temp directory with the canonical filename."""
    dest = tmp_path / PROPER_BLOG_NAME
    shutil.copy(SAMPLE_BLOG_SRC, dest)
    return dest


@pytest.fixture
def spec(blog_path: Path) -> StrategySpec:
    """Parse the sample blog fixture once and reuse across tests."""
    return parse_blog(blog_path)


# ---------------------------------------------------------------------------
# find_latest_blog
# ---------------------------------------------------------------------------

class TestFindLatestBlog:

    def test_returns_latest_file(self, tmp_path: Path) -> None:
        """Given two blog files, the one with the later date is returned."""
        (tmp_path / "2026-02-09-weekly-strategy.md").write_text("old")
        (tmp_path / "2026-02-16-weekly-strategy.md").write_text("new")
        result = find_latest_blog(tmp_path)
        assert result is not None
        assert result.name == "2026-02-16-weekly-strategy.md"

    def test_empty_directory_returns_none(self, tmp_path: Path) -> None:
        """An empty directory yields None."""
        result = find_latest_blog(tmp_path)
        assert result is None

    def test_ignores_non_matching_files(self, tmp_path: Path) -> None:
        """Files that don't match the naming pattern are ignored."""
        (tmp_path / "notes.md").write_text("not a blog")
        (tmp_path / "2026-02-16-weekly-strategy.md").write_text("blog")
        result = find_latest_blog(tmp_path)
        assert result is not None
        assert result.name == "2026-02-16-weekly-strategy.md"


# ---------------------------------------------------------------------------
# Date extraction
# ---------------------------------------------------------------------------

class TestExtractDate:

    def test_extract_date_from_filename(self, spec: StrategySpec) -> None:
        """The blog_date field should match the filename date."""
        assert spec.blog_date == "2026-02-16"


# ---------------------------------------------------------------------------
# Current allocation
# ---------------------------------------------------------------------------

class TestCurrentAllocation:

    def test_contains_expected_etfs(self, spec: StrategySpec) -> None:
        """All standard ETF symbols should be present in the allocation."""
        expected_symbols = {"SPY", "QQQ", "DIA", "XLV", "XLP", "GLD", "XLE", "BIL"}
        assert expected_symbols.issubset(set(spec.current_allocation.keys()))

    def test_total_approximately_100(self, spec: StrategySpec) -> None:
        """The sum of all allocations should be approximately 100%."""
        total = sum(spec.current_allocation.values())
        assert 98.0 <= total <= 102.0, f"Total allocation is {total}%, expected ~100%"

    def test_spy_allocation(self, spec: StrategySpec) -> None:
        """SPY should be 22% per the sample blog."""
        assert spec.current_allocation["SPY"] == 22.0

    def test_qqq_allocation(self, spec: StrategySpec) -> None:
        """QQQ should be 4% per the sample blog."""
        assert spec.current_allocation["QQQ"] == 4.0

    def test_dia_allocation(self, spec: StrategySpec) -> None:
        """DIA should be 8% per the sample blog."""
        assert spec.current_allocation["DIA"] == 8.0

    def test_xlv_allocation(self, spec: StrategySpec) -> None:
        """XLV should be 12% per the sample blog."""
        assert spec.current_allocation["XLV"] == 12.0

    def test_xlp_allocation(self, spec: StrategySpec) -> None:
        """XLP should be 12% per the sample blog."""
        assert spec.current_allocation["XLP"] == 12.0

    def test_gld_allocation(self, spec: StrategySpec) -> None:
        """GLD should be 9% per the sample blog."""
        assert spec.current_allocation["GLD"] == 9.0

    def test_xle_allocation(self, spec: StrategySpec) -> None:
        """XLE should be 5% per the sample blog."""
        assert spec.current_allocation["XLE"] == 5.0

    def test_bil_allocation(self, spec: StrategySpec) -> None:
        """BIL (cash) should be 28% per the sample blog."""
        assert spec.current_allocation["BIL"] == 28.0


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

class TestScenarios:

    def test_four_scenarios_parsed(self, spec: StrategySpec) -> None:
        """All four scenario types should be present."""
        assert "base" in spec.scenarios
        assert "bull" in spec.scenarios
        assert "bear" in spec.scenarios
        assert "tail_risk" in spec.scenarios

    def test_base_probability(self, spec: StrategySpec) -> None:
        """Base case probability should be 45%."""
        assert spec.scenarios["base"].probability == 45

    def test_bull_probability(self, spec: StrategySpec) -> None:
        """Bull case probability should be 20%."""
        assert spec.scenarios["bull"].probability == 20

    def test_bear_probability(self, spec: StrategySpec) -> None:
        """Bear case probability should be 25%."""
        assert spec.scenarios["bear"].probability == 25

    def test_tail_risk_probability(self, spec: StrategySpec) -> None:
        """Tail risk probability should be 10%."""
        assert spec.scenarios["tail_risk"].probability == 10

    def test_probabilities_sum_to_100(self, spec: StrategySpec) -> None:
        """All scenario probabilities should sum to 100%."""
        total = sum(s.probability for s in spec.scenarios.values())
        assert total == 100

    def test_base_scenario_has_allocation(self, spec: StrategySpec) -> None:
        """Base scenario allocation should have ETF-level entries."""
        alloc = spec.scenarios["base"].allocation
        assert len(alloc) > 0
        total = sum(alloc.values())
        assert 98.0 <= total <= 102.0

    def test_bear_scenario_has_allocation(self, spec: StrategySpec) -> None:
        """Bear scenario should have a different allocation with higher cash."""
        alloc = spec.scenarios["bear"].allocation
        assert len(alloc) > 0
        total = sum(alloc.values())
        assert 98.0 <= total <= 102.0

    def test_bear_scenario_has_triggers(self, spec: StrategySpec) -> None:
        """Bear scenario should have parsed trigger strings."""
        triggers = spec.scenarios["bear"].triggers
        assert len(triggers) > 0

    def test_bull_scenario_has_triggers(self, spec: StrategySpec) -> None:
        """Bull scenario should have parsed trigger strings."""
        triggers = spec.scenarios["bull"].triggers
        assert len(triggers) > 0

    def test_scenario_names_are_normalized(self, spec: StrategySpec) -> None:
        """Scenario names should be lowercase normalized keys."""
        for name in spec.scenarios:
            assert name == name.lower()
            assert " " not in name


# ---------------------------------------------------------------------------
# Trading levels
# ---------------------------------------------------------------------------

class TestTradingLevels:

    def test_sp500_present(self, spec: StrategySpec) -> None:
        """S&P 500 trading levels should be parsed."""
        assert "sp500" in spec.trading_levels

    def test_nasdaq_present(self, spec: StrategySpec) -> None:
        """Nasdaq trading levels should be parsed."""
        assert "nasdaq" in spec.trading_levels

    def test_dow_present(self, spec: StrategySpec) -> None:
        """Dow trading levels should be parsed."""
        assert "dow" in spec.trading_levels

    def test_sp500_buy_level(self, spec: StrategySpec) -> None:
        """S&P 500 buy level should be 6,771."""
        level = spec.trading_levels["sp500"]
        assert level.buy_level == pytest.approx(6771.0, abs=1.0)

    def test_sp500_sell_level(self, spec: StrategySpec) -> None:
        """S&P 500 sell level should be 7,000."""
        level = spec.trading_levels["sp500"]
        assert level.sell_level == pytest.approx(7000.0, abs=1.0)

    def test_sp500_stop_loss(self, spec: StrategySpec) -> None:
        """S&P 500 stop loss should be 6,685."""
        level = spec.trading_levels["sp500"]
        assert level.stop_loss == pytest.approx(6685.0, abs=1.0)

    def test_nasdaq_buy_level(self, spec: StrategySpec) -> None:
        """Nasdaq buy level should be 24,270."""
        level = spec.trading_levels["nasdaq"]
        assert level.buy_level == pytest.approx(24270.0, abs=1.0)

    def test_nasdaq_sell_level(self, spec: StrategySpec) -> None:
        """Nasdaq sell level should be 25,067."""
        level = spec.trading_levels["nasdaq"]
        assert level.sell_level == pytest.approx(25067.0, abs=1.0)

    def test_nasdaq_stop_loss(self, spec: StrategySpec) -> None:
        """Nasdaq stop loss should be 23,758."""
        level = spec.trading_levels["nasdaq"]
        assert level.stop_loss == pytest.approx(23758.0, abs=1.0)

    def test_gold_present(self, spec: StrategySpec) -> None:
        """Gold trading levels should be parsed."""
        assert "gold" in spec.trading_levels

    def test_oil_present(self, spec: StrategySpec) -> None:
        """Oil trading levels should be parsed."""
        assert "oil" in spec.trading_levels

    def test_all_levels_have_three_values(self, spec: StrategySpec) -> None:
        """Every parsed trading level should have buy, sell, and stop values."""
        for name, level in spec.trading_levels.items():
            assert level.buy_level is not None, f"{name} missing buy_level"
            assert level.sell_level is not None, f"{name} missing sell_level"
            assert level.stop_loss is not None, f"{name} missing stop_loss"


# ---------------------------------------------------------------------------
# VIX triggers
# ---------------------------------------------------------------------------

class TestVixTriggers:

    def test_risk_on(self, spec: StrategySpec) -> None:
        assert spec.vix_triggers["risk_on"] == 17.0

    def test_caution(self, spec: StrategySpec) -> None:
        assert spec.vix_triggers["caution"] == 20.0

    def test_stress(self, spec: StrategySpec) -> None:
        assert spec.vix_triggers["stress"] == 23.0

    def test_all_three_present(self, spec: StrategySpec) -> None:
        assert set(spec.vix_triggers.keys()) == {"risk_on", "caution", "stress"}


# ---------------------------------------------------------------------------
# Yield triggers
# ---------------------------------------------------------------------------

class TestYieldTriggers:

    def test_lower(self, spec: StrategySpec) -> None:
        assert spec.yield_triggers["lower"] == 4.11

    def test_warning(self, spec: StrategySpec) -> None:
        assert spec.yield_triggers["warning"] == 4.36

    def test_red_line(self, spec: StrategySpec) -> None:
        assert spec.yield_triggers["red_line"] == 4.50

    def test_all_three_present(self, spec: StrategySpec) -> None:
        assert set(spec.yield_triggers.keys()) == {"lower", "warning", "red_line"}


# ---------------------------------------------------------------------------
# Breadth
# ---------------------------------------------------------------------------

class TestBreadth:

    def test_breadth_200ma_parsed(self, spec: StrategySpec) -> None:
        """Breadth 200MA should be parsed from the blog (60.7% in sample)."""
        assert spec.breadth_200ma is not None
        assert spec.breadth_200ma == pytest.approx(60.7, abs=0.5)

    def test_uptrend_ratio_parsed(self, spec: StrategySpec) -> None:
        """Uptrend ratio should be parsed from the blog (~32-34 in sample)."""
        assert spec.uptrend_ratio is not None
        # The regex picks the first number after "Uptrend Ratio", which is 32
        assert 30.0 <= spec.uptrend_ratio <= 35.0


# ---------------------------------------------------------------------------
# Bubble score
# ---------------------------------------------------------------------------

class TestBubbleScore:

    def test_bubble_score_parsed(self, spec: StrategySpec) -> None:
        """Bubble score should be 9 (from 'バブルスコア9/15点')."""
        assert spec.bubble_score is not None
        assert spec.bubble_score == 9

    def test_bubble_score_is_integer(self, spec: StrategySpec) -> None:
        """Bubble score must be an integer."""
        assert isinstance(spec.bubble_score, int)


# ---------------------------------------------------------------------------
# Pre-event dates
# ---------------------------------------------------------------------------

class TestPreEventDates:

    def test_event_dates_parsed(self, spec: StrategySpec) -> None:
        """Event dates should be extracted from the important events table."""
        assert len(spec.pre_event_dates) > 0

    def test_contains_specific_dates(self, spec: StrategySpec) -> None:
        """Known event dates from the sample blog should be present."""
        # The blog lists: 2/16, 2/17, 2/18, 2/19, 2/20
        assert "2/16" in spec.pre_event_dates
        assert "2/18" in spec.pre_event_dates
        assert "2/19" in spec.pre_event_dates
        assert "2/20" in spec.pre_event_dates

    def test_no_duplicate_dates(self, spec: StrategySpec) -> None:
        """Each date should appear only once."""
        assert len(spec.pre_event_dates) == len(set(spec.pre_event_dates))


# ---------------------------------------------------------------------------
# Stop losses
# ---------------------------------------------------------------------------

class TestStopLosses:

    def test_sp500_stop_loss(self, spec: StrategySpec) -> None:
        """S&P 500 stop loss from the blog should be 6,685."""
        assert "sp500" in spec.stop_losses
        assert spec.stop_losses["sp500"] == pytest.approx(6685.0, abs=1.0)
