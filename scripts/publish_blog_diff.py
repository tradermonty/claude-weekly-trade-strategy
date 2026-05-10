#!/usr/bin/env python3
"""Publish-blog diff verifier (Step 5.7).

Compares the detailed weekly strategy blog (source of truth) and the published
version, verifying that all P0 critical facts are preserved.

Phase 1 (current): P0 facts only — see CLAUDE.md Step 5.7.
Phase 2 (future): P1 important facts.
Phase 3 (future): P2 + quality metrics (parens density, bold density, AI label).

Usage:
    python3 scripts/publish_blog_diff.py --date 2026-05-11
    python3 scripts/publish_blog_diff.py --date 2026-05-11 --output reports/2026-05-11/publish-diff.md
    python3 scripts/publish_blog_diff.py --detailed PATH --published PATH

Exit codes:
    0 = PASS  (no P0 violations)
    1 = FAIL  (at least one P0 violation)
    2 = ERROR (input file missing)

Reference: CLAUDE.md Step 5.7, .claude/agents/blog-publisher.md R10.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    severity: str  # "high" / "medium" / "low"
    category: str
    message: str

    def render(self) -> str:
        return f"  [{self.severity.upper()}] [{self.category}] {self.message}"


@dataclass
class DiffReport:
    date: str
    detailed_lines: int
    published_lines: int
    findings: list[Finding] = field(default_factory=list)
    p0_results: dict[str, str] = field(default_factory=dict)  # check name → "PASS" or "FAIL: …"
    p1_results: dict[str, str] = field(default_factory=dict)  # P1 (Medium severity) check results

    @property
    def verdict(self) -> str:
        # P0 violations → FAIL. P1 violations → PASS WITH NOTES (do not block publication).
        if any(f.severity == "high" for f in self.findings):
            return "FAIL"
        if any(f.severity == "medium" for f in self.findings):
            return "PASS WITH NOTES"
        return "PASS"


# ---------------------------------------------------------------------------
# Extractors (P0 facts)
# ---------------------------------------------------------------------------

# ETF / index symbols whose spot prices are P0.
# Limited to symbols that are conventionally written with spot prices in the body.
# Other ETFs (DIA, XLE, XLP, XLV, BIL, TLT, URA, SH, SDS, Cu, etc.) appear
# primarily in allocation tables (XX%) or portfolio examples ($XK), not as spot
# prices, so requiring their spot in published would create false positives.
TRACKED_SYMBOLS = [
    "SPY", "QQQ", "GLD",        # core ETFs always quoted with spot price
    "SPX", "NDX", "VIX",        # major indices
    "WTI", "GC",                # commodity futures
]


def extract_prices(text: str) -> dict[str, set[str]]:
    """Extract symbol → set of price strings.

    Matches price-context patterns only (not allocation %). To qualify as a
    price reference, the number must either:
      - have a $ prefix (e.g., 'SPY $737.62'), or
      - be ≥ 3 digits with a decimal or comma (e.g., 'NDX 29,224', 'VIX 17.18'),
        and NOT followed by '%' (which would indicate an allocation).
    """
    prices: dict[str, set[str]] = {}
    for sym in TRACKED_SYMBOLS:
        # Pattern A: SYMBOL $NUMBER
        pat_dollar = re.compile(rf"\b{sym}\b\s*\$\s*(\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)")
        for m in pat_dollar.finditer(text):
            prices.setdefault(sym, set()).add(m.group(1))
        # Pattern B: SYMBOL NUMBER (no $) — number must be ≥ 3 digits or have decimal,
        # and must NOT be followed by % (allocation context)
        pat_plain = re.compile(rf"\b{sym}\b\s+(\d{{1,3}}(?:,\d{{3}})+|\d+\.\d+)(?!\s*%)")
        for m in pat_plain.finditer(text):
            prices.setdefault(sym, set()).add(m.group(1))
    return prices


def extract_allocations(text: str) -> dict[str, set[str]]:
    """Extract category → set of percentage strings.

    Captures both detailed and published table formats. We pick ALL percentages
    on the line; the canonical 'this week' value is selected later via
    Bold (`**XX%**`) preference.
    """
    allocations: dict[str, set[str]] = {}
    categories = ["コア指数", "防御セクター", "テーマ/ヘッジ", "テーマ", "現金・短期債", "現金"]
    for cat in categories:
        pat = re.compile(rf"\|[^\|]*{re.escape(cat)}[^\|]*?\|([^\|\n]+)\|", re.MULTILINE)
        for m in pat.finditer(text):
            line_segment = m.group(1)
            pct = re.findall(r"(\d{1,2})\s*%", line_segment)
            if pct:
                allocations.setdefault(cat, set()).update(pct)
    return allocations


def extract_current_week_allocation(text: str) -> dict[str, int]:
    """Pick the bolded (this-week) allocation per category.

    Two patterns are supported:
    1. Table rows: '| コア指数 | 28% | **26%** | -2% | ...' (detailed-version style)
    2. Inline summary: 'コア 26% / 防御 20% / テーマ 17% / 現金 37%' (R12 published-version
       style after merging model-allocation and sector-allocation tables)

    For (1), prefer **XX%** as 'this week'. For (2), the first matching summary line
    is used as authoritative.
    """
    canonical: dict[str, int] = {}

    # Pattern 2 (preferred): inline 'コア XX% / 防御 XX% / テーマ XX% / 現金 XX%'
    # This is the R12 published-version style and is the most reliable signal.
    # Multiple inline summaries may exist (e.g., 「カテゴリ合計」 + Base scenario);
    # we use the first match as authoritative for "this week".
    inline_pat = re.compile(
        r"コア\s*(\d{1,2})\s*%[^\d]*?防御\s*(\d{1,2})\s*%[^\d]*?テーマ\s*(\d{1,2})\s*%[^\d]*?現金\s*(\d{1,2})\s*%"
    )
    m = inline_pat.search(text)
    if m:
        canonical["core"] = int(m.group(1))
        canonical["defensive"] = int(m.group(2))
        canonical["theme"] = int(m.group(3))
        canonical["cash"] = int(m.group(4))
        return canonical

    # Pattern 1 (fallback): detailed-version style, full category names in table rows
    cat_to_canonical = {
        "コア指数": "core",
        "防御セクター": "defensive",
        "テーマ/ヘッジ": "theme",
        "テーマ": "theme",
        "現金・短期債": "cash",
        "現金": "cash",
    }
    for cat, canon in cat_to_canonical.items():
        pat = re.compile(rf"\|[^\|]*{re.escape(cat)}[^\|]*?\|([^\n]+?)\|\s*$", re.MULTILINE)
        for m in pat.finditer(text):
            row = m.group(1)
            bold_pcts = re.findall(r"\*\*(\d{1,2})\s*%\*\*", row)
            plain_pcts = re.findall(r"(\d{1,2})\s*%", row)
            chosen = bold_pcts[0] if bold_pcts else (plain_pcts[1] if len(plain_pcts) >= 2 else (plain_pcts[0] if plain_pcts else None))
            if chosen is not None and canon not in canonical:
                canonical[canon] = int(chosen)

    return canonical


def extract_scenario_probabilities(text: str) -> dict[str, str]:
    """Extract scenario name → probability string.

    Handles both detailed format (### シナリオ 1 (Base): ... -- 筆者推定 **45%**)
    and published format (### Base: ... \n **筆者推定: 45%**).
    """
    probs: dict[str, str] = {}
    scenarios = {
        "Base": [r"Base", r"シナリオ\s*1"],
        "Risk-On": [r"Risk-?On", r"シナリオ\s*2"],
        "Caution": [r"Caution", r"シナリオ\s*3"],
        "Tail Risk": [r"Tail Risk", r"Tail-?Risk", r"シナリオ\s*4"],
    }
    # Find scenario sections
    headings = list(re.finditer(r"^###\s+(.+)$", text, re.MULTILINE))
    for i, h in enumerate(headings):
        title = h.group(1)
        section_end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        section = text[h.start():section_end]
        for name, patterns in scenarios.items():
            if any(re.search(p, title, re.IGNORECASE) for p in patterns):
                # Look for probability in heading or first 300 chars of section
                pmatch = re.search(r"筆者推定[:\s]*\**\s*(\d{1,3})\s*%", section[:500])
                if pmatch:
                    probs[name] = pmatch.group(1)
                break
    return probs


def extract_event_times(text: str) -> set[str]:
    """Extract event date/time identifiers (e.g., '5/12 21:30 JST', 'CPI 5/12').

    Returns a set of normalized 'M/D' or 'M/D HH:MM' strings to compare.
    """
    events: set[str] = set()
    # Pattern: M/D (optionally followed by time HH:MM)
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})(?:\s*\([日月火水木金土]\))?(?:\s+(\d{1,2}):(\d{2}))?", text):
        month, day = m.group(1), m.group(2)
        if int(month) > 12 or int(day) > 31:
            continue
        key = f"{month}/{day}"
        if m.group(3) and m.group(4):
            key = f"{key} {m.group(3)}:{m.group(4)}"
        events.add(key)
    return events


def extract_option_expiries(text: str) -> set[str]:
    """Extract option expiry dates (e.g., '6/18 満期', '5/19 満期')."""
    expiries: set[str] = set()
    pat = re.compile(r"(\d{1,2})/(\d{1,2})\s*(?:\([日月火水木金土]\)\s*)?満期")
    for m in pat.finditer(text):
        expiries.add(f"{m.group(1)}/{m.group(2)}")
    # Also detect "6/18 expiry" English
    pat_en = re.compile(r"(\d{1,2})/(\d{1,2})\s*(?:expiry|expiration)", re.IGNORECASE)
    for m in pat_en.finditer(text):
        expiries.add(f"{m.group(1)}/{m.group(2)}")
    return expiries


# URL classification rules
IR_URL_PATTERNS = [
    re.compile(r"https?://(?:investors|ir|newsroom)\.[a-z0-9.-]+", re.IGNORECASE),
    re.compile(r"https?://[a-z0-9.-]+\.com/investor", re.IGNORECASE),
]
OFFICIAL_INDICATOR_PATTERNS = [
    re.compile(r"https?://(?:www\.)?bls\.gov", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?bea\.gov", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?census\.gov", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?ismworld\.org", re.IGNORECASE),
]
FED_URL_PATTERNS = [
    re.compile(r"https?://(?:www\.)?federalreserve\.gov", re.IGNORECASE),
    re.compile(r"fomc-blackout-period-calendar\.pdf", re.IGNORECASE),
]
# P0 FED URLs only (current/upcoming Fed schedule, blackout PDF, FOMC calendar).
# Past FOMC artifacts (e.g., previous press conference PDFs) are P2.
FED_URL_P2_EXCLUDES = [
    re.compile(r"mediacenter/files/FOMCpresconf\d+\.pdf", re.IGNORECASE),
    re.compile(r"mediacenter/files/FOMCprojtabl\d+\.pdf", re.IGNORECASE),
]
MARKET_DATA_PATTERNS = [
    re.compile(r"https?://[^/]*financialmodelingprep\.com", re.IGNORECASE),
    re.compile(r"https?://tradermonty\.github\.io", re.IGNORECASE),
    re.compile(r"https?://raw\.githubusercontent\.com/tradermonty", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?cboe\.com", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?macroption\.com", re.IGNORECASE),
]
# P0 MARKET URLs are core market-data feeds. Auxiliary URLs (e.g., sector_summary.csv,
# Cboe product info pages) are P1: useful but their absence is not a critical failure.
MARKET_DATA_P1_EXCLUDES = [
    re.compile(r"sector_summary\.csv", re.IGNORECASE),
    re.compile(r"cboe\.com/tradable-products", re.IGNORECASE),
]


def classify_url(url: str) -> str:
    """Return one of: 'IR', 'OFFICIAL', 'FED', 'MARKET', 'NEWS', 'P2_AUX'.

    P2_AUX is for auxiliary URLs that are explicitly downgraded from P0 (e.g.,
    past FOMC press conference PDFs, sector_summary.csv).
    """
    for p in IR_URL_PATTERNS:
        if p.search(url):
            return "IR"
    for p in OFFICIAL_INDICATOR_PATTERNS:
        if p.search(url):
            return "OFFICIAL"
    for p in FED_URL_PATTERNS:
        if p.search(url):
            for excl in FED_URL_P2_EXCLUDES:
                if excl.search(url):
                    return "P2_AUX"
            return "FED"
    for p in MARKET_DATA_PATTERNS:
        if p.search(url):
            for excl in MARKET_DATA_P1_EXCLUDES:
                if excl.search(url):
                    return "P2_AUX"
            return "MARKET"
    return "NEWS"


def extract_urls(text: str) -> dict[str, set[str]]:
    """Extract URLs grouped by classification."""
    grouped: dict[str, set[str]] = {"IR": set(), "OFFICIAL": set(), "FED": set(), "MARKET": set(), "NEWS": set(), "P2_AUX": set()}
    for m in re.finditer(r"https?://[^\s\)\]\>]+", text):
        url = m.group(0).rstrip(".,;:")
        cat = classify_url(url)
        grouped[cat].add(url)
    return grouped


def extract_trigger_thresholds(text: str) -> set[str]:
    """Extract threshold mentions like 'VIX 16', 'VIX 23', '10Y 4.50%', 'WTI $110'."""
    thresholds: set[str] = set()
    patterns = [
        (r"VIX\s+(\d{2})\b", "VIX"),
        (r"10Y\s+(\d\.\d{1,2})\s*%", "10Y"),
        (r"WTI\s+\$?\s*(\d{2,3})\b", "WTI"),
        (r"Breadth.{0,15}(\d{2})\s*%", "Breadth"),
    ]
    for pat, name in patterns:
        for m in re.finditer(pat, text):
            thresholds.add(f"{name}={m.group(1)}")
    return thresholds


# Time criteria patterns (Issue: trigger time basis must be preserved)
TIME_CRITERIA_PATTERNS = [
    re.compile(r"終値.{0,8}2\s*[日営業]"),
    re.compile(r"2\s*[日営業].{0,8}終値"),
    re.compile(r"終値ベース"),
    re.compile(r"週足終値"),
    re.compile(r"日次終値"),
    re.compile(r"ザラ場"),
    re.compile(r"intraday", re.IGNORECASE),
    re.compile(r"closing\s*basis", re.IGNORECASE),
]


def extract_time_criteria_count(text: str) -> int:
    """Count occurrences of trigger time-criteria phrases."""
    total = 0
    for pat in TIME_CRITERIA_PATTERNS:
        total += len(pat.findall(text))
    return total


# Disclaimer 4 elements
DISCLAIMER_ELEMENTS = {
    "model_allocation": re.compile(r"モデル配分例|モデル配分"),
    "not_advice": re.compile(r"個別投資助言ではない|個別投資助言ではありません|個別の投資助言"),
    "user_judgment": re.compile(r"各自|ご自身|読者ご自身"),
    "author_estimate": re.compile(r"筆者推定|筆者個人の推定"),
}


def extract_disclaimer_elements(text: str) -> dict[str, bool]:
    """Return mapping of disclaimer element name → present (bool)."""
    return {name: bool(pat.search(text)) for name, pat in DISCLAIMER_ELEMENTS.items()}


# Scenario structure check
SCENARIO_NAMES = ["Base", "Risk-On", "Caution", "Tail Risk"]


def extract_scenario_structure(text: str) -> dict[str, dict[str, bool]]:
    """For each scenario, check: heading present, trigger present, action present.

    Trigger detection is lenient: any of (a) explicit 'トリガー/trigger/条件' keyword,
    (b) VIX/10Y/WTI threshold mention, (c) time-criteria phrase (終値/ザラ場/2日連続)
    qualifies as a trigger.

    Action detection accepts allocation-change verbs or scenario stance adjectives.
    """
    result: dict[str, dict[str, bool]] = {}
    headings = list(re.finditer(r"^###\s+(.+)$", text, re.MULTILINE))
    trigger_pat = re.compile(
        r"トリガー|trigger|条件|"
        r"VIX\s*\d|10Y\s*\d|WTI\s*\$?\d|CPI|PPI|AMAT|"
        r"終値|ザラ場|intraday|closing\s*basis|"
        r"\d\s*日連続|"
        r"想定内|無難|崩れず|ケース|場合|シナリオ",
        re.IGNORECASE,
    )
    action_pat = re.compile(
        r"アクション|action|対応|執行|実行|"
        r"減らす|増やす|縮小|拡大|維持|戻す|追加|削減|"
        r"強める|抑える|落とす|高める|防御|ヘッジ|"
        r"配分|モデル",
        re.IGNORECASE,
    )
    for name in SCENARIO_NAMES:
        pat_name = re.compile(re.escape(name).replace("Risk\\-On", "Risk-?On"), re.IGNORECASE)
        section = ""
        for i, h in enumerate(headings):
            if pat_name.search(h.group(1)):
                section_end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
                section = text[h.start():section_end]
                break
        present = bool(section)
        has_trigger = bool(trigger_pat.search(section)) if present else False
        has_action = bool(action_pat.search(section)) if present else False
        result[name] = {"heading": present, "trigger": has_trigger, "action": has_action}
    return result


# ---------------------------------------------------------------------------
# Extractors (P1 facts — Phase 2)
# ---------------------------------------------------------------------------


def extract_uptrend_freshness_note(text: str) -> bool:
    """R1 exception: Uptrend Ratio freshness must appear in body once.

    Pattern: 'Uptrend Ratio ... 5/X CSV ...' (date + CSV/時点/更新 keyword nearby).
    """
    return bool(re.search(r"Uptrend\s*Ratio[^\n]{0,80}?(CSV|時点|更新)", text, re.IGNORECASE))


def extract_100k_portfolio(text: str) -> dict[str, str]:
    """Extract '$100K' example rows: ETF/category → dollar amount string."""
    portfolio: dict[str, str] = {}
    pat = re.compile(r"\|\s*(SPY|QQQ|DIA|XLV|XLP|XLE|GLD|BIL\s*/\s*Cash)\s*\|.*?\$([0-9,]+)")
    for m in pat.finditer(text):
        portfolio[m.group(1).strip()] = m.group(2)
    return portfolio


P1_INDICATOR_PATTERNS = {
    "VIX": re.compile(r"VIX\s+\d+\.\d+"),
    "10Y": re.compile(r"10Y\s+\d+\.\d+\s*%"),
    "WTI": re.compile(r"WTI\s+\$\s*\d"),
    "GC":  re.compile(r"GC\s+\$\s*\d"),
}


def extract_p1_indicator_values(text: str) -> dict[str, bool]:
    """Check whether P1 indicator current values appear in text."""
    return {name: bool(pat.search(text)) for name, pat in P1_INDICATOR_PATTERNS.items()}


def extract_trading_levels(text: str) -> int:
    """Count distinct trading-level lines (support/resistance + defensive).

    A trading-level table row typically has format:
        | 対象 | 買いレベル | 上値目安 | 防衛ライン |
        |---|---:|---:|---:|
    We count lines under '## 売買レベル' that have ≥ 2 numeric columns.
    """
    m = re.search(r"##\s*売買レベル.*?(?=\n## |\Z)", text, re.DOTALL)
    if not m:
        return 0
    section = m.group(0)
    count = 0
    for line in section.splitlines():
        if line.startswith("|") and not line.startswith("|---") and not re.search(r"対象\s*\|", line):
            # Count cells with numbers (price levels)
            number_cells = len(re.findall(r"\$?\d{2,}", line))
            if number_cells >= 2:
                count += 1
    return count


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------


def compare_p0_facts(detailed_text: str, published_text: str) -> tuple[list[Finding], dict[str, str]]:
    """Run all P0 checks. Return (findings, p0_results).

    p0_results maps check name → "PASS" or short FAIL message.
    """
    findings: list[Finding] = []
    p0: dict[str, str] = {}

    # 1. ETF/index spot prices
    d_prices = extract_prices(detailed_text)
    p_prices = extract_prices(published_text)
    missing_prices: list[str] = []
    for sym, prices in d_prices.items():
        if not prices:
            continue
        # The published version is allowed to drop minor numbers; we focus on the
        # most-commonly-mentioned spot (any single match is enough).
        if not p_prices.get(sym):
            missing_prices.append(sym)
    if missing_prices:
        findings.append(Finding(
            "high", "P0 ETF/Index Spot Missing",
            f"Symbols missing from published: {', '.join(missing_prices)}",
        ))
        p0["ETF/index spot"] = f"FAIL ({len(missing_prices)} symbols missing)"
    else:
        p0["ETF/index spot"] = f"PASS ({len(d_prices)} symbols)"

    # 2. Allocation percentages (must total 100% in published)
    pub_pcts = extract_current_week_allocation(published_text)
    if len(pub_pcts) >= 4:
        total = sum(pub_pcts.values())
        if total != 100:
            findings.append(Finding(
                "high", "P0 Allocation Total Mismatch",
                f"published allocation totals {total}% (core+defensive+theme+cash), expected 100%. Values: {pub_pcts}",
            ))
            p0["Allocation totals"] = f"FAIL ({total}% ≠ 100%)"
        else:
            p0["Allocation totals"] = f"PASS (合計 100%)"
    else:
        findings.append(Finding(
            "high", "P0 Allocation Categories Incomplete",
            f"published has only {len(pub_pcts)} of 4 expected categories: {pub_pcts}",
        ))
        p0["Allocation totals"] = f"FAIL (missing categories)"

    # 3. Scenario probabilities
    d_probs = extract_scenario_probabilities(detailed_text)
    p_probs = extract_scenario_probabilities(published_text)
    if len(p_probs) != 4:
        findings.append(Finding(
            "high", "P0 Scenario Probability Count",
            f"published has {len(p_probs)} scenarios with probabilities, expected 4. Got: {list(p_probs.keys())}",
        ))
        p0["Scenario probabilities"] = f"FAIL ({len(p_probs)}/4 scenarios)"
    else:
        total = sum(int(v) for v in p_probs.values())
        if total != 100:
            findings.append(Finding(
                "high", "P0 Scenario Probability Sum",
                f"published probabilities sum to {total}%, expected 100%. Values: {p_probs}",
            ))
            p0["Scenario probabilities"] = f"FAIL (sum={total}%)"
        elif d_probs and d_probs != p_probs:
            findings.append(Finding(
                "high", "P0 Scenario Probability Mismatch",
                f"detailed={d_probs}, published={p_probs}",
            ))
            p0["Scenario probabilities"] = f"FAIL (drift from detailed)"
        else:
            p0["Scenario probabilities"] = f"PASS ({'+'.join(p_probs.values())}=100%)"

    # 4. P0 URL preservation (IR / OFFICIAL / FED / MARKET)
    d_urls = extract_urls(detailed_text)
    p_urls = extract_urls(published_text)
    for cat in ("IR", "OFFICIAL", "FED", "MARKET"):
        missing = d_urls[cat] - p_urls[cat]
        if missing:
            sample = next(iter(missing))
            findings.append(Finding(
                "high", f"P0 {cat} URL Missing",
                f"{len(missing)} {cat} URL(s) missing in published. Example: {sample}",
            ))
            p0[f"{cat} URLs"] = f"FAIL ({len(missing)} missing)"
        else:
            p0[f"{cat} URLs"] = f"PASS ({len(d_urls[cat])} preserved)"

    # 5. Trigger thresholds
    d_thr = extract_trigger_thresholds(detailed_text)
    p_thr = extract_trigger_thresholds(published_text)
    missing_thr = d_thr - p_thr
    # Drop thresholds that are clearly P2 (e.g., Breadth secondary numbers); for Phase 1
    # we only require a non-empty intersection.
    if not p_thr:
        findings.append(Finding(
            "high", "P0 Trigger Thresholds Missing",
            "no trigger thresholds (VIX/10Y/WTI/Breadth) detected in published",
        ))
        p0["Trigger thresholds"] = "FAIL (none detected)"
    else:
        p0["Trigger thresholds"] = f"PASS ({len(p_thr)} detected)"

    # 6. Time criteria preservation (count comparison; published may have slightly fewer)
    d_count = extract_time_criteria_count(detailed_text)
    p_count = extract_time_criteria_count(published_text)
    if p_count == 0 and d_count > 0:
        findings.append(Finding(
            "high", "P0 Time Criteria Erosion",
            f"detailed has {d_count} time-criteria phrases (終値2日連続/ザラ場 etc.), published has 0",
        ))
        p0["Time criteria"] = f"FAIL ({d_count} → 0)"
    else:
        p0["Time criteria"] = f"PASS ({p_count}/{d_count} preserved)"

    # 7. Option expiries
    d_exp = extract_option_expiries(detailed_text)
    p_exp = extract_option_expiries(published_text)
    missing_exp = d_exp - p_exp
    if missing_exp:
        findings.append(Finding(
            "high", "P0 Option Expiry Missing",
            f"expiries missing from published: {sorted(missing_exp)}",
        ))
        p0["Option expiries"] = f"FAIL ({len(missing_exp)} missing)"
    else:
        p0["Option expiries"] = f"PASS ({len(p_exp)} preserved)"

    # 8. Event datetimes (loose: at least 5 distinct events should remain)
    d_events = extract_event_times(detailed_text)
    p_events = extract_event_times(published_text)
    if len(p_events) < 5:
        findings.append(Finding(
            "high", "P0 Event Datetime Sparse",
            f"published has only {len(p_events)} event date references; expected at least 5",
        ))
        p0["Event datetimes"] = f"FAIL ({len(p_events)} < 5)"
    else:
        p0["Event datetimes"] = f"PASS ({len(p_events)} events)"

    # 9. Disclaimer 4 elements
    p_disc = extract_disclaimer_elements(published_text)
    missing_disc = [k for k, v in p_disc.items() if not v]
    if missing_disc:
        findings.append(Finding(
            "high", "P0 Disclaimer Element Missing",
            f"missing elements: {missing_disc}",
        ))
        p0["Disclaimer elements"] = f"FAIL ({len(missing_disc)}/4 missing)"
    else:
        p0["Disclaimer elements"] = "PASS (4/4 elements)"

    # 10. Scenario structure (heading + trigger + action for each of 4 scenarios)
    p_struct = extract_scenario_structure(published_text)
    struct_failures: list[str] = []
    for name, parts in p_struct.items():
        if not parts["heading"]:
            struct_failures.append(f"{name}: heading missing")
        elif not (parts["trigger"] and parts["action"]):
            missing_parts = [k for k in ("trigger", "action") if not parts[k]]
            struct_failures.append(f"{name}: missing {missing_parts}")
    if struct_failures:
        findings.append(Finding(
            "high", "P0 Scenario Structure",
            "; ".join(struct_failures),
        ))
        p0["Scenario structure"] = f"FAIL ({len(struct_failures)} issues)"
    else:
        p0["Scenario structure"] = "PASS (4 headings + each trigger/action)"

    return findings, p0


def compare_p1_facts(detailed_text: str, published_text: str) -> tuple[list[Finding], dict[str, str]]:
    """Phase 2: P1 facts (Medium severity, REVIEW not FAIL).

    These are valuable but not critical. Their absence triggers PASS WITH NOTES.
    """
    findings: list[Finding] = []
    p1: dict[str, str] = {}

    # P1.1: Uptrend Ratio freshness note (R1 exception — must appear in body once)
    if extract_uptrend_freshness_note(detailed_text):
        if extract_uptrend_freshness_note(published_text):
            p1["Uptrend freshness note"] = "PASS"
        else:
            findings.append(Finding(
                "medium", "P1 Uptrend Freshness Note Missing",
                "Detailed mentions Uptrend Ratio CSV freshness in body, but published does not (R1 exception requires 1 in-body mention)",
            ))
            p1["Uptrend freshness note"] = "REVIEW (missing)"
    else:
        p1["Uptrend freshness note"] = "N/A (not in detailed)"

    # P1.2: $100K portfolio example
    d_port = extract_100k_portfolio(detailed_text)
    p_port = extract_100k_portfolio(published_text)
    if d_port:
        missing_port = set(d_port.keys()) - set(p_port.keys())
        if missing_port:
            findings.append(Finding(
                "medium", "P1 $100K Portfolio Example Incomplete",
                f"detailed has {len(d_port)} entries, published has {len(p_port)}. Missing: {sorted(missing_port)}",
            ))
            p1["$100K portfolio example"] = f"REVIEW ({len(p_port)}/{len(d_port)} entries)"
        else:
            p1["$100K portfolio example"] = f"PASS ({len(p_port)} entries)"
    else:
        p1["$100K portfolio example"] = "N/A (not in detailed)"

    # P1.3: P1 indicator current values (VIX/10Y/WTI/GC)
    d_ind = extract_p1_indicator_values(detailed_text)
    p_ind = extract_p1_indicator_values(published_text)
    missing_ind = [k for k in d_ind if d_ind[k] and not p_ind[k]]
    if missing_ind:
        findings.append(Finding(
            "medium", "P1 Indicator Current Value Missing",
            f"published lacks current values for: {missing_ind}",
        ))
        p1["P1 indicators (VIX/10Y/WTI/GC)"] = f"REVIEW ({len(missing_ind)} missing)"
    else:
        present = [k for k in d_ind if p_ind[k]]
        p1["P1 indicators (VIX/10Y/WTI/GC)"] = f"PASS ({len(present)} preserved)"

    # P1.4: Trading levels
    d_levels = extract_trading_levels(detailed_text)
    p_levels = extract_trading_levels(published_text)
    if d_levels >= 3 and p_levels < d_levels // 2:
        findings.append(Finding(
            "medium", "P1 Trading Levels Sparse",
            f"detailed has {d_levels} trading-level entries, published has {p_levels} (less than half)",
        ))
        p1["Trading levels"] = f"REVIEW ({p_levels}/{d_levels})"
    else:
        p1["Trading levels"] = f"PASS ({p_levels} entries)"

    return findings, p1


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def render_report(report: DiffReport) -> str:
    lines: list[str] = []
    lines.append(f"# Publish Diff Report — {report.date}")
    lines.append("")
    lines.append(f"## Verdict")
    lines.append(report.verdict)
    lines.append("")
    lines.append("## Stats")
    lines.append(f"- Detailed lines: {report.detailed_lines}")
    lines.append(f"- Published lines: {report.published_lines}")
    lines.append("")
    lines.append("## P0 Critical Facts")
    for name, status in report.p0_results.items():
        marker = "✓" if status.startswith("PASS") else "✗"
        lines.append(f"- {marker} {name}: {status}")
    lines.append("")
    if report.p1_results:
        lines.append("## P1 Important Facts (REVIEW, non-blocking)")
        for name, status in report.p1_results.items():
            if status.startswith("PASS"):
                marker = "✓"
            elif status.startswith("N/A"):
                marker = "—"
            else:
                marker = "△"
            lines.append(f"- {marker} {name}: {status}")
        lines.append("")
    if report.findings:
        high = [f for f in report.findings if f.severity == "high"]
        med = [f for f in report.findings if f.severity == "medium"]
        if high:
            lines.append("## HIGH severity (FAIL)")
            for f in high:
                lines.append(f.render())
            lines.append("")
        if med:
            lines.append("## MEDIUM severity (REVIEW)")
            for f in med:
                lines.append(f.render())
            lines.append("")
    else:
        lines.append("## Findings")
        lines.append("None.")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description="Publish-blog diff verifier (Step 5.7, Phase 1)")
    p.add_argument("--date", help="Target date YYYY-MM-DD (uses default paths)")
    p.add_argument("--detailed", help="Path to detailed blog (overrides --date)")
    p.add_argument("--published", help="Path to published blog (overrides --date)")
    p.add_argument("--output", help="Path to write publish-diff.md (default: reports/<date>/publish-diff.md)")
    args = p.parse_args()

    if args.detailed and args.published:
        detailed_path = Path(args.detailed)
        published_path = Path(args.published)
        date_str = args.date or detailed_path.stem.split("-weekly")[0]
    elif args.date:
        date_str = args.date
        detailed_path = PROJECT_ROOT / "blogs" / f"{date_str}-weekly-strategy.md"
        published_path = PROJECT_ROOT / "blogs" / "published" / f"{date_str}-weekly-strategy.md"
    else:
        print("ERROR: --date or both --detailed and --published required", file=sys.stderr)
        return 2

    if not detailed_path.exists():
        print(f"ERROR: detailed blog not found: {detailed_path}", file=sys.stderr)
        return 2
    if not published_path.exists():
        print(f"ERROR: published blog not found: {published_path}", file=sys.stderr)
        return 2

    detailed_text = detailed_path.read_text()
    published_text = published_path.read_text()

    p0_findings, p0_results = compare_p0_facts(detailed_text, published_text)
    p1_findings, p1_results = compare_p1_facts(detailed_text, published_text)

    report = DiffReport(
        date=date_str,
        detailed_lines=detailed_text.count("\n"),
        published_lines=published_text.count("\n"),
        findings=p0_findings + p1_findings,
        p0_results=p0_results,
        p1_results=p1_results,
    )

    output_text = render_report(report)
    print(output_text)

    output_path = Path(args.output) if args.output else PROJECT_ROOT / "reports" / date_str / "publish-diff.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text)

    return 0 if report.verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
