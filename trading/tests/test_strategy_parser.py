"""Tests for the strategy_parser module.

Verifies that the parser correctly extracts structured data from the
Japanese-language weekly strategy blog markdown.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from trading.layer2.tools.strategy_parser import (
    _normalize_scenario_name_d,
    _parse_category_allocation,
    _parse_scenario_cash_pct,
    _parse_scenario_etf_detail,
    _parse_scenarios,
    _parse_vix_triggers,
    find_latest_blog,
    parse_blog,
)
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

    def test_sector_allocation_section_is_prioritized_over_scenarios(self) -> None:
        """Scenario ETF percentages must not overwrite current allocation values."""
        from trading.layer2.tools.strategy_parser import _parse_sector_allocation

        text = """
### セクター配分（4本柱）
| カテゴリ | 配分 | 具体的ETF/銘柄 |
|---------|------|---------------|
| **コア指数** | 38% | SPY 24%、QQQ 6%、DIA 8% |
| **防御セクター** | 22% | XLV 12%、XLP 10% |
| **テーマ/ヘッジ** | 16% | GLD 10%、XLE 6% |
| **現金・短期債** | 24% | BIL、MMF |

### シナリオ別プラン
### Bull Case: テスト (20%)
**アクション（合計100%）**:
- コア: 38% → **42%**
- 防御: 22% → **20%**
- テーマ: 16% → **18%**（内訳: GLD 10%、XLE 4%、COPX 4%）
- 現金: 24% → **20%**
"""
        alloc = _parse_sector_allocation(text)
        assert alloc["SPY"] == pytest.approx(24.0, abs=0.1)
        assert alloc["XLE"] == pytest.approx(6.0, abs=0.1)
        assert alloc["BIL"] == pytest.approx(24.0, abs=0.1)

    def test_real_blog_keeps_sector_table_xle_value(self) -> None:
        """Real blog: XLE should come from セクター配分 table, not scenario sub-lines."""
        blog_path = Path(__file__).parent.parent.parent / "blogs" / "2026-02-23-weekly-strategy.md"
        if not blog_path.exists():
            pytest.skip("Blog file not available")
        parsed = parse_blog(blog_path)
        assert parsed.current_allocation["XLE"] == pytest.approx(6.0, abs=0.1)
        assert parsed.current_allocation["BIL"] == pytest.approx(24.0, abs=0.1)

    def test_lot_table_transition_values(self) -> None:
        """2026-08-03 format: no セクター配分 section; per-ETF values live in
        the ロット管理 table as "old%→**new%**" transitions plus bolded 維持.
        The new (bolded) value must win, QQQ **1%維持** must be captured, and
        the cash row must take the bolded 今週 cell (33%), not 前週 (37%)."""
        from trading.layer2.tools.strategy_parser import _parse_sector_allocation

        text = """
### ロット管理

| カテゴリ | 前週 (7/27) | 今週 (8/3) | 変化 | 実行タイミング | 根拠 |
|---------|-----------|-----------|------|-------------|------|
| **コア指数** | 25% | **29%** | **+4%** | 月曜寄り | SPY 15%→**18%** (+3%)、QQQ **1%維持** (観測枠)、DIA 9%→**10%** (+1%) |
| **防御セクター** | 21% | **21%** | **±0%** | 維持 | XLV **10%維持**、XLP **11%維持** |
| **テーマ/ヘッジ** | 17% | **17%** | **±0%** | 月曜寄り | GLD 13%→**12%** (-1%)、XLE 4%→**5%** (+1%) |
| **現金・短期債** | 37% | **33%** | **-4%** | 段階的 | Stress 4条件不成立ぶんを戻す |

### 今週の売買レベル
| 指数 | 買い | 売り |
"""
        alloc = _parse_sector_allocation(text)
        assert alloc == {
            "SPY": 18.0,
            "QQQ": 1.0,
            "DIA": 10.0,
            "XLV": 10.0,
            "XLP": 11.0,
            "GLD": 12.0,
            "XLE": 5.0,
            "BIL": 33.0,
        }
        assert sum(alloc.values()) == 100.0


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
# Scenario header dash variants (regression: 2026-05-18 em-dash)
# ---------------------------------------------------------------------------

class TestScenarioHeaderDashVariants:
    """Format D headers must parse whether the dash before 筆者推定 is the
    ASCII double-hyphen ``--`` (through 2026-05-11) or the em/en/horizontal
    dash ``—/–/―`` (2026-05-18 onward). Regression for the parser artifact
    that zeroed scenario probabilities in the 2026-05-18 daily action plan.
    """

    @staticmethod
    def _blog_with_dash(dash: str) -> str:
        return (
            "# 週次戦略\n\n"
            "## シナリオ別プラン\n\n"
            f"### シナリオ 1 (Base): NVDA まちまち {dash} 筆者推定 **45%**\n\n"
            "**トリガー**: 原油 $95-110 レンジ\n\n"
            "**アクション**: コア 23% / 防御 22% / テーマ 18% / 現金 37%\n\n"
            f"### シナリオ 2 (Risk-On 復帰): NVDA 強い {dash} 筆者推定 **22%**\n\n"
            "**トリガー**: Uptrend 赤→緑\n\n"
            "**アクション**: コア 30% / 防御 18% / テーマ 17% / 現金 35%\n\n"
            f"### シナリオ 3 (Caution 深化): NVDA 弱含み {dash} 筆者推定 **26%**\n\n"
            "**トリガー**: 10Y 4.50% 超\n\n"
            "**アクション**: コア 16% / 防御 24% / テーマ 20% / 現金 40%\n\n"
            f"### シナリオ 4 (Tail Risk): ホルムズ完全封鎖 {dash} 筆者推定 **7%**\n\n"
            "**トリガー**: VIX 26 ザラ場\n\n"
            "**アクション**: コア 16% / 防御 24% / テーマ 20% / 現金 40%\n"
        )

    @pytest.mark.parametrize(
        "dash",
        ["--", "—", "–", "―"],  # --, em, en, horizontal bar
    )
    def test_probabilities_sum_to_100_regardless_of_dash(
        self, tmp_path: Path, dash: str
    ) -> None:
        blog = tmp_path / "2026-05-18-weekly-strategy.md"
        blog.write_text(self._blog_with_dash(dash), encoding="utf-8")
        spec = parse_blog(blog)
        # Four scenario blocks must be extracted (the bug left this empty).
        assert len(spec.scenarios) == 4, (
            f"dash={dash!r} -> scenarios={set(spec.scenarios)}"
        )
        total = sum(s.probability for s in spec.scenarios.values())
        assert total == 100, f"dash={dash!r} -> probs did not sum to 100"
        probs = sorted(s.probability for s in spec.scenarios.values())
        assert probs == [7, 22, 26, 45], f"dash={dash!r} -> {probs}"


# ---------------------------------------------------------------------------
# Trigger splitting (regression: 2026-07-27 daily action plan)
# ---------------------------------------------------------------------------

class TestTriggerSplitting:
    """Trigger lines must survive parenthesised qualifiers and OR groups.

    Regression for the 2026-07-27 plan_state, where
    "VIX **26超 (ザラ場、即時)**" was torn at the 、 into "VIX 26超 (ザラ場" +
    "即時)", and "10年債 4.806%" inherited the indicator of the preceding leg
    (becoming "WTI 10年債 ..." / "VIX 10年債 ...") because 10年債/SPX/NDX were
    missing from the indicator keyword list.
    """

    @staticmethod
    def _blog(trigger_line: str) -> str:
        return (
            "# 週次戦略\n\n"
            "## シナリオ別プラン\n\n"
            "### シナリオ 1 (Base): レンジ — 筆者推定 **60%**\n\n"
            f"**トリガー**: {trigger_line}\n\n"
            "**アクション**: コア 25% / 防御 21% / テーマ 17% / 現金 37%\n\n"
            "### シナリオ 4 (Tail Risk): 供給ショック — 筆者推定 **40%**\n\n"
            "**トリガー**: VIX **26超 (ザラ場、即時)**\n\n"
            "**アクション**: コア 14% / 防御 25% / テーマ 17% / 現金 44%\n"
        )

    def _triggers(self, tmp_path: Path, trigger_line: str) -> list[str]:
        blog = tmp_path / "2026-07-27-weekly-strategy.md"
        blog.write_text(self._blog(trigger_line), encoding="utf-8")
        return parse_blog(blog).scenarios["base"].triggers

    def test_comma_inside_parens_does_not_split(self, tmp_path: Path) -> None:
        triggers = self._triggers(tmp_path, "VIX **26超 (ザラ場、即時)**")
        assert triggers == ["VIX 26超 (ザラ場、即時)"]

    def test_top_level_comma_still_splits(self, tmp_path: Path) -> None:
        triggers = self._triggers(tmp_path, "VIX **20-23 圏**、SPX **7,232.1 維持**")
        assert triggers == ["VIX 20-23 圏", "SPX 7,232.1 維持"]

    def test_or_group_brackets_are_stripped(self, tmp_path: Path) -> None:
        triggers = self._triggers(
            tmp_path,
            "[WTI **100ドル終値上抜け** or 10年債 **4.806% 終値上抜け**]",
        )
        assert triggers == ["WTI 100ドル終値上抜け", "10年債 4.806% 終値上抜け"]

    def test_yield_leg_does_not_inherit_previous_indicator(
        self, tmp_path: Path
    ) -> None:
        triggers = self._triggers(
            tmp_path,
            "VIX **20-23 圏 (終値)** + SPX **7,232.1 維持 (終値)** + "
            "NDX **26,233 を割らず 28,245.3 を挟んで推移** + "
            "10年債 **4.501%〜4.806% レンジ (終値)**",
        )
        assert triggers == [
            "VIX 20-23 圏 (終値)",
            "SPX 7,232.1 維持 (終値)",
            "NDX 26,233 を割らず 28,245.3 を挟んで推移",
            "10年債 4.501%〜4.806% レンジ (終値)",
        ]

    def test_bare_number_leg_still_inherits_indicator(
        self, tmp_path: Path
    ) -> None:
        """The inheritance path itself must keep working for bare price legs."""
        triggers = self._triggers(
            tmp_path, "WTI **$105 終値上抜け** + **$110 終値 2日連続**",
        )
        assert triggers == ["WTI $105 終値上抜け", "WTI $110 終値 2日連続"]


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

    def test_arrow_sell_level_and_futures_gold_label(self) -> None:
        """Parser should accept arrow sell levels and 金先物(GC) row names."""
        from trading.layer2.tools.strategy_parser import _parse_trading_levels

        text = """
### 今週の売買レベル
| 指数 | 買いレベル | 売りレベル | ストップロス |
|------|-----------|-----------|-------------|
| **S&P 500** | 6,771（20週MA） | 7,018（ATH） | 6,685（50週MA） |
| **Nasdaq 100** | 24,270（20週MA） | 25,067（直近抵抗）→26,233（ATH） | 23,758（50週MA） |
| **金先物(GC)** | $4,900（短期サポート） | $5,155（上値レジスタンス）→$5,300（拡張） | $4,634（20週MA） |
| **Oil (WTI)** | $61.22（水平サポート） | $67.16（抵抗）→$70.74（50週MA） | $55（長期サポート） |
"""
        levels = _parse_trading_levels(text)
        assert levels["nasdaq"].buy_level == pytest.approx(24270.0, abs=1.0)
        assert levels["nasdaq"].sell_level == pytest.approx(25067.0, abs=1.0)
        assert levels["nasdaq"].stop_loss == pytest.approx(23758.0, abs=1.0)

        assert levels["gold"].buy_level == pytest.approx(4900.0, abs=1.0)
        assert levels["gold"].sell_level == pytest.approx(5155.0, abs=1.0)
        assert levels["gold"].stop_loss == pytest.approx(4634.0, abs=1.0)

        assert levels["oil"].buy_level == pytest.approx(61.22, abs=0.01)
        assert levels["oil"].sell_level == pytest.approx(67.16, abs=0.01)
        assert levels["oil"].stop_loss == pytest.approx(55.0, abs=0.01)


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

    def test_four_level_slash_row(self) -> None:
        text = "| **VIX** | **18.20** (8/14終値) | 17 / **20突破** / **23** / 26 | note |"

        assert _parse_vix_triggers(text) == {
            "risk_on": 17.0,
            "caution": 20.0,
            "stress": 23.0,
            "panic": 26.0,
        }

    def test_annotation_level_does_not_shift_ladder(self) -> None:
        """2026-08-17 blog prepended a hand-drawn floor to the threshold cell.

        Reading the cell positionally mapped stress to 20 and panic to 23,
        one rung below the standard ladder.
        """
        text = (
            "| **VIX** | **14.25** (8/14終値。週足 OHLC 15.40/15.72/14.18/14.26) "
            "| **14.00 (手描き下限)** / **17 (Risk-On 境界)** / 20 / 23 / 26 "
            "| 6ヶ月最安終値を更新 |"
        )

        assert _parse_vix_triggers(text) == {
            "risk_on": 17.0,
            "caution": 20.0,
            "stress": 23.0,
            "panic": 26.0,
        }

    def test_partial_ladder_maps_by_value(self) -> None:
        text = "| **VIX** | **21.40** | 20 / 23 / 26 | note |"

        assert _parse_vix_triggers(text) == {
            "caution": 20.0,
            "stress": 23.0,
            "panic": 26.0,
        }


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

    def test_combined_10y_30y_row_header(self) -> None:
        """2026-08-03 blog uses a combined '10Y / 30Y 利回り' row; thresholds
        must come from the 3rd cell, not the combined current-value cell."""
        from trading.layer2.tools.strategy_parser import _parse_yield_triggers

        text = (
            "| **10Y / 30Y 利回り** | **4.750% / 5.270%** (7/31、30年はサイクル高値) "
            "| 4.11 / 4.36 / 4.50 / **4.60% 極限 (突破済)** | 今週も主役 |\n"
        )
        triggers = _parse_yield_triggers(text)
        assert triggers == {
            "lower": 4.11,
            "warning": 4.36,
            "red_line": 4.50,
            "extreme": 4.60,
        }


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

# `blogs/**` is gitignored, so a clean checkout — and CI — has none of the
# weekly articles. Asserting a corpus size that only exists on a developer
# machine turned the suite red on every clean clone, which is a fixture problem
# and not a parser problem. Use the real corpus when it is present and the
# tracked fixtures otherwise; either way the parser is exercised end to end.
_ROOT = Path(__file__).parent.parent.parent
_FIXTURE_BLOGS = _ROOT / "scripts/tests/fixtures/plan_state"
_LIVE_BLOGS = _ROOT / "blogs"
_FULL_CORPUS_MIN = 16


def _blog_corpus() -> tuple[Path, int]:
    """(directory to build the timeline from, minimum entries to expect)."""
    if _LIVE_BLOGS.is_dir():
        articles = [
            p for p in _LIVE_BLOGS.iterdir()
            if p.is_file() and p.suffix == ".md"
        ]
        if len(articles) >= _FULL_CORPUS_MIN:
            return _LIVE_BLOGS, _FULL_CORPUS_MIN
    tracked = sorted(_FIXTURE_BLOGS.glob("*-weekly-strategy.md"))
    if not tracked:
        pytest.skip("no blog corpus and no tracked fixtures")
    return _FIXTURE_BLOGS, len(tracked)


class TestAllBlogsParse:
    """Verify the available blog corpus parses successfully."""

    def test_all_blogs_valid_via_timeline(self) -> None:
        """StrategyTimeline should report 0 skipped blogs."""
        from trading.backtest.strategy_timeline import StrategyTimeline
        blogs_dir, minimum = _blog_corpus()

        tl = StrategyTimeline()
        tl.build(blogs_dir)
        skipped_info = [(s.blog_date, s.reason) for s in tl.skipped]
        assert len(tl.skipped) == 0, f"Skipped blogs: {skipped_info}"
        assert len(tl.entries) >= minimum, (
            f"Expected >={minimum} entries from {blogs_dir.name}, "
            f"got {len(tl.entries)}"
        )

    def test_each_blog_has_allocation_and_scenarios(self) -> None:
        """Every parsed blog should have non-empty allocation and scenarios."""
        from trading.backtest.strategy_timeline import StrategyTimeline
        blogs_dir, _ = _blog_corpus()

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


class TestScenarioAllocationFormats:
    """Regression tests for the 2026-07-20 scenario allocation formats.

    That week's blog dropped the colon after the category label and the "%" on
    the arrow target, which made every non-base scenario fall back to the base
    allocation and produced totals of 98 / 102 / 109 percent.
    """

    def test_category_line_without_colon(self) -> None:
        """"- コア 28% → **33%**" (no colon) parses to the post-arrow value."""
        block = (
            "**アクション (合計 100%)**:\n"
            "- コア 28% → **33%** (SPY 17→19 (+2%)、QQQ 2→4 (+2%)、DIA 9→10 (+1%))\n"
            "- 防御 21% → **19%** (XLV 10→9 (-1%)、XLP 11→10 (-1%))\n"
            "- テーマ 16% → **15%** (GLD 12→11 (-1%)、XLE 4%維持)\n"
            "- 現金 35% → **33%** (-2%)\n"
        )
        assert _parse_category_allocation(block) == {
            "core": 33, "defensive": 19, "theme": 15, "cash": 33,
        }

    def test_category_line_with_colon_still_parses(self) -> None:
        """The older "- コア: 40% → **45%**" form must keep working."""
        block = (
            "**アクション**:\n"
            "- コア: 40% → **45%**\n"
            "- 防御: 18% → **17%**\n"
            "- テーマ: 12% → **13%**\n"
            "- 現金: 30% → **25%**\n"
        )
        assert _parse_category_allocation(block) == {
            "core": 45, "defensive": 17, "theme": 13, "cash": 25,
        }

    def test_dollar_example_lines_are_not_allocations(self) -> None:
        """"- コア指数: $40K" carries no percentage and must not match."""
        block = (
            "**アクション**:\n"
            "- コア指数: $40K\n"
            "- 防御: $20K\n"
            "- 現金: $25K\n"
        )
        assert _parse_category_allocation(block) is None

    def test_inline_category_form_used_by_tail_risk(self) -> None:
        """Tail Risk writes all four categories inline, the first after "(" ."""
        block = (
            "**アクション (合計 100%)**: 上記推奨配分を**据え置き** "
            "(コア 28% / 防御 21% / テーマ 16% / 現金 35%)\n"
        )
        assert _parse_category_allocation(block) == {
            "core": 28, "defensive": 21, "theme": 16, "cash": 35,
        }

    def test_etf_arrow_target_without_percent_sign(self) -> None:
        """"SPY 17→19 (+2%)" yields 19, not the pre-arrow 17."""
        block = (
            "**アクション (合計 100%)**:\n"
            "- コア 28% → **33%** (SPY 17→19 (+2%)、QQQ 2→4 (+2%)、DIA 9→10 (+1%))\n"
            "- テーマ 16% → **15%** (GLD 12→11 (-1%)、XLE 4%維持)\n"
        )
        detail = _parse_scenario_etf_detail(block)
        assert detail["SPY"] == 19.0
        assert detail["QQQ"] == 4.0
        assert detail["DIA"] == 10.0
        assert detail["GLD"] == 11.0
        assert detail["XLE"] == 4.0

    def test_price_levels_are_not_read_as_allocations(self) -> None:
        """A quoted level above 100% must not be taken for a weight."""
        block = "**アクション**: SPY 660→670 で追随、GLD 12→14%\n"
        detail = _parse_scenario_etf_detail(block)
        assert "SPY" not in detail
        assert detail["GLD"] == 14.0

    def test_cash_pct_ignores_unrelated_later_arrow(self) -> None:
        """現金 **44%** followed by "XLEは4%→2%" must yield 44, not 2."""
        line = (
            "**アクション (合計 100%)**: コア **15%** / 現金 **44%**。"
            "**注: 原油急騰局面でもXLEは4%→2%へ削減**。\n"
        )
        assert _parse_scenario_cash_pct(line) == 44.0

    def test_cash_pct_takes_arrow_target_when_it_is_the_cash_change(self) -> None:
        """"現金 35% → **33%**" still resolves to the post-arrow 33."""
        assert _parse_scenario_cash_pct("- 現金 35% → **33%** (-2%)\n") == 33.0


# ---------------------------------------------------------------------------
# 2026-08-10 blog format regressions
# ---------------------------------------------------------------------------

class TestQualifiedTriggerLabel:
    """The bold trigger label may carry a qualifier inside the asterisks."""

    def test_trigger_with_parenthetical_qualifier_is_parsed(self) -> None:
        """"**トリガー (いずれか1つの成立で発動)**:" must not yield an empty list.

        An empty trigger list is silent: Layer 2 reads it as "no conditions"
        rather than as a parse failure.
        """
        text = (
            "### シナリオ 2 (Risk-On): 全面加速 — 筆者推定 **25%**\n\n"
            "**トリガー (下記のうち2つ以上が終値ベースで成立)**: "
            "NDX **30,839.1 終値上抜け** / VIX **14.00 終値割れ**\n\n"
            "**アクション (合計 100%)**:\n"
            "- コア 36% → **42%** (SPY 21→23、QQQ 5→9、DIA 10%維持)\n"
            "- 現金 24% → **20%**\n"
        )
        scenarios = _parse_scenarios(text)
        assert "bull" in scenarios
        assert scenarios["bull"].triggers, "qualified trigger label produced no triggers"

    def test_plain_trigger_label_still_parses(self) -> None:
        text = (
            "### シナリオ 1 (Base): 消化 — 筆者推定 **47%**\n\n"
            "**トリガー**: SPX **7,636.4 を終値で維持**\n\n"
            "**アクション (合計 100%)**: コア **36%** / 現金 **24%**\n"
        )
        scenarios = _parse_scenarios(text)
        assert scenarios["base"].triggers


class TestScenarioNameNormalization:
    """Only base/bull/bear/tail_risk are valid downstream (strategy_intent)."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Base", "base"),
            ("Risk-On", "bull"),
            ("risk on", "bull"),
            ("リスクオン", "bull"),
            ("警戒", "bear"),
            ("Caution", "bear"),
            ("Tail Risk", "tail_risk"),
        ],
    )
    def test_writer_names_map_to_canonical(self, raw: str, expected: str) -> None:
        assert _normalize_scenario_name_d(raw) == expected


class TestCategoryParenBreakdown:
    """The one-line Tail Risk action omits "%" inside the category parens."""

    def test_bare_numbers_inside_category_parens(self) -> None:
        block = (
            "**アクション (合計 100%)**: **Tail Risk Defensive Mode** — "
            "コア **18%** (SPY 12 / QQQ 0 / DIA 6) / 防御 **23%** (XLV 13 / XLP 10) / "
            "テーマ **16%** (GLD 14 / XLE 2) / 現金 **43%**。\n"
        )
        detail = _parse_scenario_etf_detail(block)
        assert detail == {
            "SPY": 12.0, "QQQ": 0.0, "DIA": 6.0,
            "XLV": 13.0, "XLP": 10.0, "GLD": 14.0, "XLE": 2.0, "BIL": 43.0,
        }
        assert sum(detail.values()) == 100.0

    def test_footnotes_do_not_overwrite_the_action(self) -> None:
        """Conditional variants in **注N** lines must stay out of the allocation."""
        block = (
            "**アクション (合計 100%)**: コア **18%** (SPY 12 / QQQ 0 / DIA 6) / "
            "防御 **23%** (XLV 13 / XLP 10) / テーマ **16%** (GLD 14 / XLE 2) / "
            "現金 **43%**。\n"
            "*実行タイミング: 2脚成立を終値で確認後、翌営業日の寄りで分割執行。*\n"
            "**注3**: (b) 供給ショック経路では XLE は 5% 据え置きとし、"
            "テーマ **19%** (GLD 14 / XLE 5) / 現金 **40%**。\n"
            "\n"
            "次の段落。\n"
        )
        detail = _parse_scenario_etf_detail(block)
        assert detail["XLE"] == 2.0, "footnote branch leaked into the action"
        assert detail["BIL"] == 43.0


class TestJapaneseScenarioRules:
    """Each Japanese scenario must keep its OWN satisfaction rule.

    The rule used to be read after the collection loop had finished, so `block`
    still held the LAST scenario's text and every scenario inherited that
    scenario's rule: a closing "いずれか1つ" turned an opening "すべて満たす"
    into an OR, and a base case that needs five legs looked satisfied by one.
    """

    TEXT = """### シナリオA) 平常（確率:60%）
**トリガー (すべて満たす)**: SPX 7,700 超 + VIX 17 未満

**アクション (合計 100%)**:
- コア: 30%
- 現金: 70%

### シナリオB) 警戒（確率:40%）
**トリガー (いずれか1つ)**: SPX 7,000 割れ + VIX 23 超

**アクション (合計 100%)**:
- コア: 10%
- 現金: 90%
"""

    def test_first_scenario_keeps_all_when_last_scenario_is_any(self) -> None:
        from trading.layer2.tools.strategy_parser import _parse_scenarios
        scenarios = _parse_scenarios(self.TEXT)
        first = [s for s in scenarios.values() if s.probability == 60][0]
        assert first.satisfaction_rule == "all", (
            "the 60% scenario says すべて満たす; it must not inherit "
            "いずれか1つ from the scenario below it"
        )

    def test_last_scenario_keeps_its_own_any(self) -> None:
        from trading.layer2.tools.strategy_parser import _parse_scenarios
        scenarios = _parse_scenarios(self.TEXT)
        last = [s for s in scenarios.values() if s.probability == 40][0]
        assert last.satisfaction_rule == "any"

    def test_at_least_is_not_leaked_to_the_others(self) -> None:
        from trading.layer2.tools.strategy_parser import _parse_scenarios
        text = self.TEXT.replace("**トリガー (いずれか1つ)**", "**トリガー (2つ以上)**")
        scenarios = _parse_scenarios(text)
        by_prob = {s.probability: s for s in scenarios.values()}
        assert by_prob[60].satisfaction_rule == "all"
        assert by_prob[40].satisfaction_rule == "at_least"
        assert by_prob[40].min_legs == 2


class TestTriggerLabelVariants:
    """The legs must survive the wording the articles actually use."""

    HEAD = "### シナリオA) 平常（確率:60%）\n"
    LEGS = "SPX 7,700 超 / VIX 17 未満\n"

    def _legs(self, label_line: str) -> list:
        from trading.layer2.tools.strategy_parser import _parse_trigger_list
        return _parse_trigger_list(self.HEAD + label_line + "\n")

    def test_plain_label(self) -> None:
        assert self._legs("**トリガー**: " + self.LEGS)

    def test_label_with_qualifier(self) -> None:
        assert self._legs("**トリガー (すべて満たす)**: " + self.LEGS)

    def test_prose_between_label_and_colon(self) -> None:
        """2026-09-07 wrote two sentences between the label and the legs."""
        line = (
            "**トリガー (下記のうち2つ以上)**。**これは配分の部分復帰であり、"
            "フェーズ昇格ではありません。** 昇格条件は別に定義しています: "
            + self.LEGS
        )
        legs = self._legs(line)
        assert legs, "prose before the colon must not drop the legs"
        assert any("7,700" in leg for leg in legs)

    def test_hatsudou_jouken_label(self) -> None:
        assert self._legs("**発動条件 (すべて満たす)**: " + self.LEGS)

    def test_prose_without_a_colon_yields_nothing(self) -> None:
        """No colon means no leg list; guessing would invent triggers."""
        assert self._legs("**トリガー (すべて満たす)** の詳細は後述します\n") == []

    def test_unrelated_later_paragraph_is_not_captured(self) -> None:
        from trading.layer2.tools.strategy_parser import _parse_trigger_list
        block = (
            self.HEAD
            + "**トリガー (すべて満たす)** の詳細は後述します\n"
            + "\n"
            + "**アクション (合計 100%)**: コア 30%\n"
        )
        assert _parse_trigger_list(block) == []
