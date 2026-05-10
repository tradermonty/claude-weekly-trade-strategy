"""Tests for publish_blog_diff.py (Step 5.7, Phase 1).

Uses the 2026-05-11 detailed/clean fixture pair as the gold standard. Verifies:
- Extractors return expected values on the fixture pair
- compare_p0_facts produces PASS verdict on the gold-standard pair
- Mutations to the published version trigger expected FAIL findings

Run with:
    python3 -m pytest scripts/tests/test_publish_blog_diff.py -v
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
spec = importlib.util.spec_from_file_location(
    "publish_blog_diff",
    PROJECT_ROOT / "scripts" / "publish_blog_diff.py",
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules["publish_blog_diff"] = module
spec.loader.exec_module(module)

extract_prices = module.extract_prices
extract_current_week_allocation = module.extract_current_week_allocation
extract_scenario_probabilities = module.extract_scenario_probabilities
extract_event_times = module.extract_event_times
extract_option_expiries = module.extract_option_expiries
extract_urls = module.extract_urls
extract_trigger_thresholds = module.extract_trigger_thresholds
extract_time_criteria_count = module.extract_time_criteria_count
extract_disclaimer_elements = module.extract_disclaimer_elements
extract_scenario_structure = module.extract_scenario_structure
classify_url = module.classify_url
compare_p0_facts = module.compare_p0_facts
# Phase 2 (P1 facts)
extract_uptrend_freshness_note = module.extract_uptrend_freshness_note
extract_100k_portfolio = module.extract_100k_portfolio
extract_p1_indicator_values = module.extract_p1_indicator_values
extract_trading_levels = module.extract_trading_levels
compare_p1_facts = module.compare_p1_facts

FIXTURE_DIR = PROJECT_ROOT / "scripts" / "tests" / "fixtures" / "publish"
DETAILED_PATH = FIXTURE_DIR / "2026-05-11-detailed.md"
CLEAN_PATH = FIXTURE_DIR / "2026-05-11-clean.md"


def _load() -> tuple[str, str]:
    return DETAILED_PATH.read_text(), CLEAN_PATH.read_text()


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------


def test_extract_prices_finds_core_etfs() -> None:
    detailed, clean = _load()
    d_prices = extract_prices(detailed)
    p_prices = extract_prices(clean)
    # SPY/QQQ/GLD spot prices must appear in both versions
    for sym in ("SPY", "QQQ", "GLD", "VIX", "SPX", "NDX"):
        assert d_prices.get(sym), f"detailed missing spot for {sym}"
        assert p_prices.get(sym), f"clean missing spot for {sym}"


def test_extract_prices_excludes_allocation_percentages() -> None:
    """Numbers followed by % must not be picked up as prices."""
    text = "QQQ 1% to 3% rebalance, but QQQ $711.23 spot"
    prices = extract_prices(text)
    assert "711.23" in prices.get("QQQ", set())
    # The "1" in "QQQ 1%" should not appear as a price
    assert "1" not in prices.get("QQQ", set())


def test_extract_current_week_allocation_picks_bold() -> None:
    """When 'last week 28% | this week **26%**', should pick 26."""
    text = "| コア指数 | 28% | **26%** | -2% | 月曜寄り | xyz |\n"
    alloc = extract_current_week_allocation(text)
    assert alloc.get("core") == 26


def test_extract_scenario_probabilities_4_scenarios() -> None:
    detailed, clean = _load()
    d_probs = extract_scenario_probabilities(detailed)
    p_probs = extract_scenario_probabilities(clean)
    assert set(d_probs.keys()) == {"Base", "Risk-On", "Caution", "Tail Risk"}
    assert set(p_probs.keys()) == {"Base", "Risk-On", "Caution", "Tail Risk"}
    assert sum(int(v) for v in p_probs.values()) == 100


def test_extract_option_expiries_includes_juneteenth_shifted() -> None:
    detailed, clean = _load()
    d_exp = extract_option_expiries(detailed)
    p_exp = extract_option_expiries(clean)
    # 6/18 (Juneteenth-shifted from 6/19) must be present
    assert "6/18" in d_exp
    assert "6/18" in p_exp


def test_classify_url_categories() -> None:
    assert classify_url("https://investors.cisco.com/news") == "IR"
    assert classify_url("https://www.bls.gov/cpi/") == "OFFICIAL"
    assert classify_url("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm") == "FED"
    assert classify_url("https://financialmodelingprep.com/api/") == "MARKET"
    assert classify_url("https://www.reuters.com/article/abc") == "NEWS"


def test_classify_url_p2_excludes() -> None:
    """Past FOMC press conferences and Cboe product pages should be P2_AUX."""
    assert classify_url(
        "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20260429.pdf"
    ) == "P2_AUX"
    assert classify_url("https://www.cboe.com/tradable-products/vix/") == "P2_AUX"


def test_extract_disclaimer_4_elements() -> None:
    _, clean = _load()
    elements = extract_disclaimer_elements(clean)
    for k, v in elements.items():
        assert v, f"clean version missing disclaimer element: {k}"


def test_extract_scenario_structure_lenient_trigger() -> None:
    """Base scenario without explicit '条件' keyword should still pass via fallback patterns."""
    text = """## シナリオ別プラン

### Base: 指標は想定内
**筆者推定: 45%**

CPI、PPI が大きく崩れず、AMAT のガイダンスも無難なケース。
この場合は配分を維持する。

### Risk-On: VIX 16 未満を維持
**筆者推定: 25%**

VIX が 16 未満を 2 日連続で維持し、SPX が 7,500 を超えるなら QQQ を増やす。

### Caution: 10Y 4.50% 突破
**筆者推定: 25%**

10Y が 4.50% を終値で超える場合は防御を強める。

### Tail Risk: 三重ショック
**筆者推定: 5%**

VIX 26 超なら現金を増やす。
"""
    struct = extract_scenario_structure(text)
    for name in ("Base", "Risk-On", "Caution", "Tail Risk"):
        assert struct[name]["heading"], f"{name}: heading not detected"
        assert struct[name]["trigger"], f"{name}: trigger not detected"
        assert struct[name]["action"], f"{name}: action not detected"


# ---------------------------------------------------------------------------
# End-to-end compare_p0_facts tests
# ---------------------------------------------------------------------------


def test_compare_p0_facts_passes_on_gold_fixture() -> None:
    """The detailed/clean pair shipped as fixtures must produce PASS."""
    detailed, clean = _load()
    findings, p0 = compare_p0_facts(detailed, clean)
    high = [f for f in findings if f.severity == "high"]
    assert not high, f"expected no high findings, got: {[f.message for f in high]}"


def test_compare_p0_facts_detects_missing_etf_spot() -> None:
    """Removing a P0 spot price must trigger a high finding."""
    detailed, clean = _load()
    mutated = clean.replace("SPY $737.62", "SPY removed-here").replace(
        "$737.62", "REMOVED"
    )
    findings, _ = compare_p0_facts(detailed, mutated)
    high = [f for f in findings if f.severity == "high"]
    assert any("SPY" in f.message and "Spot" in f.category for f in high), (
        f"expected SPY missing finding, got: {[f.message for f in high]}"
    )


def test_compare_p0_facts_detects_allocation_imbalance() -> None:
    """Breaking the allocation total to ≠100% must FAIL.

    The clean (R12) version uses inline 'コア XX% / 防御 XX% / テーマ XX% / 現金 XX%'
    summaries; we mutate the *first* such summary (which is treated as authoritative).
    """
    import re
    detailed, clean = _load()
    inline_pat = re.compile(
        r"(コア\s*\d{1,2}\s*%[^\d]*?防御\s*\d{1,2}\s*%[^\d]*?テーマ\s*\d{1,2}\s*%[^\d]*?現金)\s*\d{1,2}\s*%"
    )
    # Replace the first match's cash percentage to 30%
    mutated = inline_pat.sub(lambda m: f"{m.group(1)} 30%", clean, count=1)
    findings, _ = compare_p0_facts(detailed, mutated)
    high = [f for f in findings if f.severity == "high"]
    assert any("Allocation Total" in f.category for f in high), (
        f"expected allocation imbalance finding, got: {[f.message for f in high]}"
    )


def test_compare_p0_facts_detects_missing_scenario() -> None:
    """Removing a scenario must FAIL on probability count and structure."""
    detailed, clean = _load()
    # Strip Tail Risk section
    import re
    mutated = re.sub(r"### Tail Risk.*?(?=\n## |\Z)", "", clean, flags=re.DOTALL)
    findings, _ = compare_p0_facts(detailed, mutated)
    high = [f for f in findings if f.severity == "high"]
    assert any("Probability" in f.category or "Structure" in f.category for f in high), (
        f"expected scenario removal finding, got: {[f.message for f in high]}"
    )


def test_compare_p0_facts_detects_missing_disclaimer() -> None:
    """Removing a disclaimer element ('個別投資助言') must FAIL.

    We pick an element that is unique to the disclaimer block so the mutation
    doesn't accidentally break scenario probability detection.
    """
    detailed, clean = _load()
    mutated = clean.replace("個別投資助言ではありません", "REMOVED-PHRASE").replace(
        "個別投資助言ではない", "REMOVED-PHRASE"
    ).replace("個別の投資助言", "REMOVED-PHRASE")
    findings, _ = compare_p0_facts(detailed, mutated)
    high = [f for f in findings if f.severity == "high"]
    assert any("Disclaimer" in f.category for f in high), (
        f"expected disclaimer missing finding, got: {[f.message for f in high]}"
    )


# ---------------------------------------------------------------------------
# Phase 2 (P1 facts) tests
# ---------------------------------------------------------------------------


def test_extract_uptrend_freshness_note_detects_in_body() -> None:
    text = "Uptrend Ratio は 5/7 CSV 時点。日次更新のため、次回更新で 25% 割れを確認する。"
    assert extract_uptrend_freshness_note(text)


def test_extract_uptrend_freshness_note_absent() -> None:
    text = "Uptrend Ratio はとても弱い。" # no CSV/時点/更新 keyword
    assert not extract_uptrend_freshness_note(text)


def test_extract_100k_portfolio_picks_dollar_amounts() -> None:
    text = """| SPY | 15% | $15,000 |
| QQQ | 1% | $1,000 |
| BIL / Cash | 37% | $37,000 |"""
    portfolio = extract_100k_portfolio(text)
    assert portfolio.get("SPY") == "15,000"
    assert portfolio.get("QQQ") == "1,000"
    assert portfolio.get("BIL / Cash") == "37,000"


def test_extract_p1_indicator_values_present() -> None:
    text = "VIX 17.18, 10Y 4.36%, WTI $94.67, GC $4,730.7"
    indicators = extract_p1_indicator_values(text)
    assert indicators["VIX"] is True
    assert indicators["10Y"] is True
    assert indicators["WTI"] is True
    assert indicators["GC"] is True


def test_compare_p1_facts_passes_on_gold_fixture() -> None:
    """Gold-standard pair should produce no Medium findings."""
    detailed, clean = _load()
    findings, _ = compare_p1_facts(detailed, clean)
    medium = [f for f in findings if f.severity == "medium"]
    assert not medium, f"expected no P1 findings, got: {[f.message for f in medium]}"


def test_compare_p1_facts_detects_missing_uptrend_freshness() -> None:
    """If clean version drops the Uptrend freshness body line, P1 must REVIEW."""
    import re
    detailed, clean = _load()
    # Remove the Uptrend Ratio freshness body sentence
    mutated = re.sub(r"Uptrend\s*Ratio[^\n]*?(CSV|時点|更新)[^\n]*?\n", "", clean)
    findings, _ = compare_p1_facts(detailed, mutated)
    medium = [f for f in findings if f.severity == "medium"]
    assert any("Uptrend Freshness" in f.category for f in medium), (
        f"expected uptrend freshness finding, got: {[f.message for f in medium]}"
    )


def test_compare_p0_facts_detects_ir_url_loss() -> None:
    """Removing an IR URL must FAIL."""
    detailed, clean = _load()
    # Find first IR URL in detailed and remove from clean (or never include)
    import re
    ir_urls = [m.group(0) for m in re.finditer(r"https?://(?:investors|ir|newsroom)\.[^\s\)\]]+", detailed, re.IGNORECASE)]
    if not ir_urls:
        return  # no IR URLs to test against
    mutated = clean
    for url in ir_urls:
        mutated = mutated.replace(url.rstrip(".,;:"), "REMOVED-URL")
    findings, _ = compare_p0_facts(detailed, mutated)
    high = [f for f in findings if f.severity == "high"]
    assert any("IR URL" in f.category for f in high), (
        f"expected IR URL missing finding, got: {[f.message for f in high]}"
    )
