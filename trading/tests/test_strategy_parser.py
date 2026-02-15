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
        """Known event dates from the sample blog should be present (YYYY-MM-DD)."""
        # The blog lists: 2/16, 2/17, 2/18, 2/19, 2/20 → converted to YYYY-MM-DD
        assert "2026-02-16" in spec.pre_event_dates
        assert "2026-02-18" in spec.pre_event_dates
        assert "2026-02-19" in spec.pre_event_dates
        assert "2026-02-20" in spec.pre_event_dates

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


# ---------------------------------------------------------------------------
# ETF range format (Fix 2)
# ---------------------------------------------------------------------------

class TestRangeAllocation:
    """Test that range-format allocations (e.g. 'SPY 25-30%') are parsed."""

    def test_midpoint_is_used(self) -> None:
        """SPY 25-30% should produce midpoint 27.5%."""
        from trading.layer2.tools.strategy_parser import _midpoint
        assert _midpoint(25.0, "30") == 27.5

    def test_midpoint_no_range(self) -> None:
        """Single value (no range) returns value as-is."""
        from trading.layer2.tools.strategy_parser import _midpoint
        assert _midpoint(22.0, None) == 22.0

    def test_range_etf_regex_matches(self) -> None:
        """_ETF_SYMBOLS regex should capture range format."""
        from trading.layer2.tools.strategy_parser import _ETF_SYMBOLS
        text = "SPY 25-30%、QQQ 10-12%、DIA 5%"
        matches = list(_ETF_SYMBOLS.finditer(text))
        assert len(matches) == 3
        # SPY: group(2)=25, group(3)=30
        assert matches[0].group(1) == "SPY"
        assert matches[0].group(2) == "25"
        assert matches[0].group(3) == "30"
        # DIA: no range
        assert matches[2].group(1) == "DIA"
        assert matches[2].group(2) == "5"
        assert matches[2].group(3) is None

    def test_range_cash_row_regex(self) -> None:
        """_CASH_ROW regex should capture range format."""
        from trading.layer2.tools.strategy_parser import _CASH_ROW
        text = "| **現金・短期債** | 25-30% | BIL、MMF |"
        m = _CASH_ROW.search(text)
        assert m is not None
        assert m.group(1) == "25"
        assert m.group(2) == "30"

    def test_real_blog_with_range(self) -> None:
        """2025-11-24 blog uses range format and should parse successfully."""
        blog_path = Path(__file__).parent.parent.parent / "blogs" / "2025-11-24-weekly-strategy.md"
        if not blog_path.exists():
            pytest.skip("Blog file not available")
        spec = parse_blog(blog_path)
        assert len(spec.current_allocation) > 0
        total = sum(spec.current_allocation.values())
        assert 90 <= total <= 110, f"Total allocation {total}% outside 90-110%"

    def test_normalization_over_105(self) -> None:
        """When midpoints push total > 105%, normalization to 100% occurs."""
        from trading.layer2.tools.strategy_parser import _parse_sector_allocation
        # Construct text with ranges that sum > 105%
        text = """
### セクター配分(4本柱)

| カテゴリ | 配分 | 具体的ETF/銘柄 |
|---------|------|---------------|
| **コア指数** | 45-55% | SPY 30-40%、QQQ 10-15%、DIA 5-8% |
| **防御セクター** | 20-25% | XLV 15-18%、XLP 5-7% |
| **テーマ/ヘッジ** | 15-20% | GLD 10-12%、XLE 5-8% |
| **現金・短期債** | 25-30% | BIL、MMF |
"""
        alloc = _parse_sector_allocation(text)
        total = sum(alloc.values())
        assert 95 <= total <= 105, f"Total after normalization: {total}%"


# ---------------------------------------------------------------------------
# Category-level fallback (Fix 3)
# ---------------------------------------------------------------------------

class TestCategoryFallback:
    """Test category-level parsing for early blogs lacking ETF-level data."""

    def test_category_table_row_regex(self) -> None:
        """_CATEGORY_TABLE_ROW should match bold percentage values."""
        from trading.layer2.tools.strategy_parser import _CATEGORY_TABLE_ROW
        text = "| **コア指数** | 50-55% | **30-35%** | -20% | Death Cross |"
        m = _CATEGORY_TABLE_ROW.search(text)
        assert m is not None
        assert m.group("cat") == "コア指数"
        assert m.group("lo") == "30"
        assert m.group("hi") == "35"

    def test_distribute_categories_to_etfs(self) -> None:
        """Category percentages should distribute to ETFs correctly."""
        from trading.layer2.tools.strategy_parser import _distribute_categories_to_etfs
        cat_alloc = {
            "コア指数": 40.0,
            "ヘルスケア": 10.0,
            "コモディティ": 10.0,
            "現金": 25.0,
        }
        result = _distribute_categories_to_etfs(cat_alloc)
        # コア指数: SPY 65% of 40 = 26, QQQ 25% of 40 = 10, DIA 10% of 40 = 4
        assert result["SPY"] == pytest.approx(26.0, abs=0.1)
        assert result["QQQ"] == pytest.approx(10.0, abs=0.1)
        assert result["DIA"] == pytest.approx(4.0, abs=0.1)
        assert result["XLV"] == pytest.approx(10.0, abs=0.1)
        assert result["GLD"] == pytest.approx(10.0, abs=0.1)
        assert result["BIL"] == pytest.approx(25.0, abs=0.1)

    def test_real_blog_category_only(self) -> None:
        """2025-11-03 blog (category-only) should parse via fallback."""
        blog_path = Path(__file__).parent.parent.parent / "blogs" / "2025-11-03-weekly-strategy.md"
        if not blog_path.exists():
            pytest.skip("Blog file not available")
        spec = parse_blog(blog_path)
        assert len(spec.current_allocation) > 0
        total = sum(spec.current_allocation.values())
        assert 90 <= total <= 110, f"Total allocation {total}% outside 90-110%"
        # Should contain standard ETFs from distribution
        assert "SPY" in spec.current_allocation

    def test_real_blog_2025_11_10(self) -> None:
        """2025-11-10 blog should also parse via category fallback."""
        blog_path = Path(__file__).parent.parent.parent / "blogs" / "2025-11-10-weekly-strategy.md"
        if not blog_path.exists():
            pytest.skip("Blog file not available")
        spec = parse_blog(blog_path)
        assert len(spec.current_allocation) > 0
        total = sum(spec.current_allocation.values())
        assert 90 <= total <= 110, f"Total allocation {total}% outside 90-110%"


# ---------------------------------------------------------------------------
# Scenario header formats (Fix 1)
# ---------------------------------------------------------------------------

class TestScenarioHeaderFormats:
    """Test all three scenario header formats."""

    def test_format_a_english_only(self) -> None:
        """Format A: ### Base Case: desc (55%) — no prefix."""
        from trading.layer2.tools.strategy_parser import _SCENARIO_HEADER_EN
        text = "### Base Case: サンタラリー小幅上昇 (55%)"
        m = _SCENARIO_HEADER_EN.search(text)
        assert m is not None
        assert m.group(1) == "Base Case"
        assert m.group(2) == "55"

    def test_format_b_with_prefix(self) -> None:
        """Format B: ### シナリオA) Base Case: desc (55%) — with prefix."""
        from trading.layer2.tools.strategy_parser import _SCENARIO_HEADER_EN
        text = "### シナリオA) Base Case: 慎重な横ばい (55%)"
        m = _SCENARIO_HEADER_EN.search(text)
        assert m is not None
        assert m.group(1) == "Base Case"
        assert m.group(2) == "55"

    def test_format_b_fullwidth_paren(self) -> None:
        """Format B with fullwidth parenthesis: ### シナリオA）Base Case (55%)."""
        from trading.layer2.tools.strategy_parser import _SCENARIO_HEADER_EN
        text = "### シナリオA）Base Case: テスト (55%)"
        m = _SCENARIO_HEADER_EN.search(text)
        assert m is not None
        assert m.group(1) == "Base Case"

    def test_format_c_japanese_only(self) -> None:
        """Format C: ### シナリオA）悪化継続（確率：45%）— Japanese only."""
        from trading.layer2.tools.strategy_parser import _SCENARIO_HEADER_JP
        text = "### シナリオA）悪化継続（確率：45%）— 採用ベースケース"
        m = _SCENARIO_HEADER_JP.search(text)
        assert m is not None
        assert m.group(1) == "A"
        assert m.group(2) == "悪化継続"
        assert m.group(3) == "45"

    def test_format_c_half_paren(self) -> None:
        """Format C with half-width paren: ### シナリオB)反発回復(確率:30%)."""
        from trading.layer2.tools.strategy_parser import _SCENARIO_HEADER_JP
        text = "### シナリオB)反発回復(確率:30%)"
        m = _SCENARIO_HEADER_JP.search(text)
        assert m is not None
        assert m.group(1) == "B"
        assert m.group(3) == "30"

    def test_real_blog_format_b_scenarios(self) -> None:
        """2025-12-08 blog (Format B) should parse all scenarios."""
        blog_path = Path(__file__).parent.parent.parent / "blogs" / "2025-12-08-weekly-strategy.md"
        if not blog_path.exists():
            pytest.skip("Blog file not available")
        spec = parse_blog(blog_path)
        assert len(spec.scenarios) >= 3, f"Expected >=3 scenarios, got {len(spec.scenarios)}"
        assert "base" in spec.scenarios

    def test_real_blog_format_c_scenarios(self) -> None:
        """2025-11-03 blog (Format C) should parse all scenarios."""
        blog_path = Path(__file__).parent.parent.parent / "blogs" / "2025-11-03-weekly-strategy.md"
        if not blog_path.exists():
            pytest.skip("Blog file not available")
        spec = parse_blog(blog_path)
        assert len(spec.scenarios) >= 3, f"Expected >=3 scenarios, got {len(spec.scenarios)}"
        assert "base" in spec.scenarios


# ---------------------------------------------------------------------------
# Japanese scenario name mapping (Fix 1)
# ---------------------------------------------------------------------------

class TestJapaneseScenarioNameMapping:
    """Test mapping of Japanese scenario descriptions to standard names."""

    def test_highest_prob_is_base(self) -> None:
        """Highest probability scenario should map to 'base'."""
        from trading.layer2.tools.strategy_parser import _map_jp_scenarios_to_names
        scenarios = [
            ("A", "悪化継続", 45),
            ("B", "反発回復", 30),
            ("C", "急落", 25),
        ]
        result = _map_jp_scenarios_to_names(scenarios)
        assert result["A"] == "base"

    def test_bull_keyword_detected(self) -> None:
        """Scenarios containing bull keywords should map to 'bull'."""
        from trading.layer2.tools.strategy_parser import _map_jp_scenarios_to_names
        scenarios = [
            ("A", "横ばい継続", 45),
            ("B", "反発回復", 30),
            ("C", "調整深化", 25),
        ]
        result = _map_jp_scenarios_to_names(scenarios)
        assert result["A"] == "base"
        assert result["B"] == "bull"
        assert result["C"] == "bear"

    def test_bear_keyword_detected(self) -> None:
        """Scenarios containing bear keywords should map to 'bear'."""
        from trading.layer2.tools.strategy_parser import _map_jp_scenarios_to_names
        scenarios = [
            ("A", "継続", 50),
            ("B", "悪化シナリオ", 30),
            ("C", "上昇加速", 20),
        ]
        result = _map_jp_scenarios_to_names(scenarios)
        assert result["A"] == "base"
        assert result["B"] == "bear"
        assert result["C"] == "bull"

    def test_remaining_fills_unfilled(self) -> None:
        """Unclassified scenarios fill remaining slots."""
        from trading.layer2.tools.strategy_parser import _map_jp_scenarios_to_names
        scenarios = [
            ("A", "横ばい", 50),
            ("B", "シナリオ2", 30),
            ("C", "シナリオ3", 20),
        ]
        result = _map_jp_scenarios_to_names(scenarios)
        assert result["A"] == "base"
        # B and C should fill "bull" and "bear" (or "tail_risk")
        assert set(result.values()) >= {"base", "bull", "bear"}

    def test_empty_scenarios(self) -> None:
        """Empty input returns empty mapping."""
        from trading.layer2.tools.strategy_parser import _map_jp_scenarios_to_names
        assert _map_jp_scenarios_to_names([]) == {}

    def test_four_scenarios_with_tail_risk(self) -> None:
        """Four scenarios should include tail_risk."""
        from trading.layer2.tools.strategy_parser import _map_jp_scenarios_to_names
        scenarios = [
            ("A", "継続", 45),
            ("B", "回復", 25),
            ("C", "調整", 20),
            ("D", "ブラックスワン", 10),
        ]
        result = _map_jp_scenarios_to_names(scenarios)
        assert result["A"] == "base"
        assert result["B"] == "bull"
        assert result["C"] == "bear"
        assert result["D"] == "tail_risk"


# ---------------------------------------------------------------------------
# Integration: all blogs parse successfully
# ---------------------------------------------------------------------------

class TestAllBlogsParse:
    """Verify all blog files in the blogs/ directory parse successfully."""

    def test_all_blogs_valid_via_timeline(self) -> None:
        """StrategyTimeline should report 0 skipped blogs."""
        from trading.backtest.strategy_timeline import StrategyTimeline
        blogs_dir = Path(__file__).parent.parent.parent / "blogs"
        if not blogs_dir.exists():
            pytest.skip("Blogs directory not available")

        tl = StrategyTimeline()
        tl.build(blogs_dir)
        skipped_info = [(s.blog_date, s.reason) for s in tl.skipped]
        assert len(tl.skipped) == 0, f"Skipped blogs: {skipped_info}"
        assert len(tl.entries) >= 16, f"Expected >=16 entries, got {len(tl.entries)}"

    def test_each_blog_has_allocation_and_scenarios(self) -> None:
        """Every parsed blog should have non-empty allocation and scenarios."""
        from trading.backtest.strategy_timeline import StrategyTimeline
        blogs_dir = Path(__file__).parent.parent.parent / "blogs"
        if not blogs_dir.exists():
            pytest.skip("Blogs directory not available")

        tl = StrategyTimeline()
        tl.build(blogs_dir)
        for entry in tl.entries:
            alloc_total = sum(entry.strategy.current_allocation.values())
            assert alloc_total >= 90, (
                f"{entry.blog_date}: allocation total {alloc_total}% < 90%"
            )
            assert len(entry.strategy.scenarios) >= 3, (
                f"{entry.blog_date}: only {len(entry.strategy.scenarios)} scenarios"
            )
