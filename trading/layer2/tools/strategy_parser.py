"""Parse the weekly strategy blog markdown into a StrategySpec.

This is the most critical module in the trading system. It extracts
structured data (allocations, scenarios, trading levels, triggers)
from the Japanese-language weekly blog so the automated system can
act on the strategy.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from trading.data.models import ScenarioSpec, StrategySpec, TradingLevel


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_latest_blog(blogs_dir: str | Path) -> Optional[Path]:
    """Return the most recent ``YYYY-MM-DD-weekly-strategy.md`` file, or None."""
    blogs_dir = Path(blogs_dir)
    candidates = sorted(blogs_dir.glob("????-??-??-weekly-strategy.md"))
    return candidates[-1] if candidates else None


def parse_blog(blog_path: str | Path) -> StrategySpec:
    """Parse a weekly strategy blog file into a :class:`StrategySpec`."""
    blog_path = Path(blog_path)
    text = blog_path.read_text(encoding="utf-8")
    blog_date = _extract_date_from_filename(blog_path.name)

    return StrategySpec(
        blog_date=blog_date,
        current_allocation=_parse_sector_allocation(text),
        scenarios=_parse_scenarios(text),
        trading_levels=_parse_trading_levels(text),
        stop_losses=_parse_stop_losses(text),
        vix_triggers=_parse_vix_triggers(text),
        yield_triggers=_parse_yield_triggers(text),
        breadth_200ma=_parse_breadth_200ma(text),
        uptrend_ratio=_parse_uptrend_ratio(text),
        bubble_score=_parse_bubble_score(text),
        phase=_parse_phase(text),
        pre_event_dates=_parse_pre_event_dates(text, blog_date),
    )


# ---------------------------------------------------------------------------
# Internal parsers
# ---------------------------------------------------------------------------

def _extract_date_from_filename(filename: str) -> str:
    """Extract ``YYYY-MM-DD`` from a filename like ``2026-02-16-weekly-strategy.md``."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", filename)
    if not m:
        raise ValueError(f"Cannot extract date from filename: {filename}")
    return m.group(1)


# --- Sector allocation ---------------------------------------------------

# Fix 2: Support range format (e.g. "SPY 25-30%") — use midpoint
_VALID_ETFS = frozenset({
    "SPY", "QQQ", "DIA", "XLV", "XLP", "GLD", "XLE",
    "BIL", "TLT", "URA", "SH", "SDS", "IWM", "COPX",
})

_ETF_SYMBOLS = re.compile(
    r"(SPY|QQQ|DIA|XLV|XLP|GLD|XLE|BIL|TLT|URA|SH|SDS|IWM|COPX)\s*"
    r"(?:\*\*)?\s*"  # tolerate bold between symbol and value ("QQQ **1%維持**")
    r"(\d+(?:\.\d+)?)"
    r"(?:\s*-\s*(\d+(?:\.\d+)?))?"
    r"\s*%"
)

# Transition notation "15%→**18%**": drop the old value so inline scans pick
# the new (bolded) allocation instead of the pre-transition one.
_PCT_TRANSITION = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s*→\s*\*?\*?(\d+(?:\.\d+)?)\s*%"
)

# Fix 2: Support range format for cash row
_CASH_ROW = re.compile(
    r"\|\s*\*?\*?現金[・&]?短期債\*?\*?\s*\|\s*"
    r"(?:\*?\*?)?\s*(\d+)(?:\s*-\s*(\d+))?\s*%"
)

# Lot-management table cash row "| **現金・短期債** | 37% | **33%** |":
# the bolded 今週 cell takes priority over the 前週 cell.
_CASH_ROW_BOLD = re.compile(
    r"\|\s*\*?\*?現金[・&]?短期債\*?\*?\s*\|[^|\n]*\|\s*"
    r"\*\*(\d+)(?:\s*-\s*(\d+))?\s*%"
)

# Fix 3: Category table row with bold "今週" values for fallback
_CATEGORY_TABLE_ROW = re.compile(
    r"^\|\s*\*?\*?(?:[①②③④]\s*)?(?:-\s*)?"
    r"(?P<cat>コア指数|テクノロジー|金融|ヘルスケア|エネルギー|"
    r"コモディティ|防衛/ヘッジ|防衛／ヘッジ|現金|防御セクター|テーマ/ヘッジ|現金・短期債)"
    r".*?\*\*\s*(?P<lo>\d+)(?:\s*-\s*(?P<hi>\d+))?\s*%\s*\*\*",
    re.MULTILINE,
)

# Default ETF distribution ratios for category-level fallback
_DEFAULT_CATEGORY_ETF_MAP: dict[str, dict[str, float]] = {
    "コア指数": {"SPY": 0.65, "QQQ": 0.25, "DIA": 0.10},
    "テクノロジー": {"QQQ": 1.0},
    "金融": {"SPY": 1.0},  # absorbed into SPY
    "ヘルスケア": {"XLV": 1.0},
    "防御セクター": {"XLV": 0.65, "XLP": 0.35},
    "エネルギー": {"XLE": 1.0},
    "コモディティ": {"GLD": 1.0},
    "防衛/ヘッジ": {"TLT": 0.5, "GLD": 0.5},
    "防衛／ヘッジ": {"TLT": 0.5, "GLD": 0.5},
    "テーマ/ヘッジ": {"GLD": 0.60, "XLE": 0.40},
    "現金": {"BIL": 1.0},
    "現金・短期債": {"BIL": 1.0},
}

_SECTOR_ALLOCATION_SECTION_KEYWORD = "セクター配分"
_TRADING_LEVELS_SECTION_KEYWORD = "売買レベル"


def _midpoint(lo: float, hi_str: Optional[str]) -> float:
    """Return midpoint if hi_str given, otherwise just lo."""
    if hi_str:
        return (lo + float(hi_str)) / 2.0
    return lo


def _parse_pipe_allocation_table(section: str) -> dict[str, float]:
    """Parse ``| セクター | ETF | 配分(%) | ... |`` pipe table format.

    Handles the latest blog format where each row has a separate ETF column:
        | コア | SPY | 12% | -2% | 縮小維持 |
        | 現金 | BIL/Cash | 42% | +5% | 積み増し |
    """
    alloc: dict[str, float] = {}
    for line in section.splitlines():
        cells = _split_markdown_row(line)
        if len(cells) < 3 or _is_table_separator(cells):
            continue
        # Column 2 (index 1): ETF name — handle "BIL/Cash" → "BIL", strip bold
        etf_raw = re.sub(r"\*+", "", cells[1]).strip().split("/")[0].strip().upper()
        if etf_raw not in _VALID_ETFS:
            continue
        # Column 3 (index 2): percentage
        pct_m = re.search(r"(\d+(?:\.\d+)?)\s*%", cells[2])
        if pct_m:
            alloc[etf_raw] = float(pct_m.group(1))
    return alloc


def _parse_sector_allocation(text: str) -> dict[str, float]:
    """Parse the セクター配分 table for individual ETF percentages.

    Supports multiple table formats:
      - Pipe table with ETF column: ``| コア | SPY | 12% | ...``
      - Inline ETF: ``SPY 22%、QQQ 4%``
      - Category-level fallback for early blogs

    Falls back to category-level parsing for early blogs that lack
    individual ETF percentages.
    """
    alloc: dict[str, float] = {}

    # Parse from the dedicated allocation section first so scenario blocks
    # (which can contain ETF percentages) do not overwrite current allocation.
    section = _extract_section(text, _SECTOR_ALLOCATION_SECTION_KEYWORD)
    # Blogs since 2026-08 merge per-ETF allocations into the ロット管理 table
    # (no separate セクター配分 section); scoping to that section keeps the
    # inline scan from picking stale values elsewhere in the article.
    if section is None:
        section = _extract_section(text, "ロット管理")
    parse_source = section if section else text

    # 1. Try pipe table format first (latest blogs: | セクター | ETF | 配分 |)
    alloc = _parse_pipe_allocation_table(parse_source)

    # 2. If insufficient, fall back to inline ETF regex. Normalize transition
    # notation ("15%→**18%**" → "18%") so the new value is captured.
    inline_source = _PCT_TRANSITION.sub(r"\2%", parse_source)
    if sum(alloc.values()) < 50:
        for m in _ETF_SYMBOLS.finditer(inline_source):
            symbol = m.group(1)
            pct = _midpoint(float(m.group(2)), m.group(3))
            alloc[symbol] = pct

    # Cash row: assign to BIL (only if not already parsed from pipe table).
    # The lot-table format keeps 前週/今週 in separate cells, so the bolded
    # 今週 cell takes priority over the plain 前週 cell.
    if "BIL" not in alloc or alloc.get("BIL", 0) == 0:
        cash_matches = (
            list(_CASH_ROW_BOLD.finditer(inline_source))
            or list(_CASH_ROW.finditer(inline_source))
        )
        if cash_matches:
            last = cash_matches[-1]
            alloc["BIL"] = _midpoint(float(last.group(1)), last.group(2))

    # Fix 3: Fallback to category-level parsing when ETF-level is insufficient
    total = sum(alloc.values())
    if total < 50:
        cat_alloc = _parse_category_table(parse_source)
        # Backward-compatibility fallback for older formats where the heading
        # might be missing but category rows still exist elsewhere in the text.
        if not cat_alloc and parse_source is not text:
            cat_alloc = _parse_category_table(text)
        if cat_alloc:
            alloc = _distribute_categories_to_etfs(cat_alloc)

    # Normalize if midpoints pushed total beyond 105%
    total = sum(alloc.values())
    if total > 105:
        factor = 100.0 / total
        alloc = {k: round(v * factor, 1) for k, v in alloc.items()}

    return alloc


def _parse_category_table(text: str) -> Optional[dict[str, float]]:
    """Parse category-level allocation from bold table values.

    For early blogs (2025-11-03 through 2025-11-17) that only have
    category-level tables like:
        | **コア指数** | 50-55% | **30-35%** | ...
    """
    result: dict[str, float] = {}
    for m in _CATEGORY_TABLE_ROW.finditer(text):
        cat = m.group("cat")
        lo = float(m.group("lo"))
        pct = _midpoint(lo, m.group("hi"))
        # Keep last occurrence (セクター配分 table comes after ロット管理)
        result[cat] = pct

    return result if len(result) >= 3 else None


def _distribute_categories_to_etfs(cat_alloc: dict[str, float]) -> dict[str, float]:
    """Convert category percentages to ETF allocations using default ratios."""
    etf_alloc: dict[str, float] = {}
    for cat, pct in cat_alloc.items():
        mapping = _DEFAULT_CATEGORY_ETF_MAP.get(cat)
        if mapping:
            for symbol, ratio in mapping.items():
                val = round(pct * ratio, 1)
                if symbol in etf_alloc:
                    etf_alloc[symbol] += val
                else:
                    etf_alloc[symbol] = val

    # Normalize if total exceeds 105%
    total = sum(etf_alloc.values())
    if total > 105:
        factor = 100.0 / total
        etf_alloc = {k: round(v * factor, 1) for k, v in etf_alloc.items()}

    return etf_alloc


# --- Scenarios ------------------------------------------------------------

# Fix 1: Format A (no prefix) and Format B (with シナリオX prefix)
_SCENARIO_HEADER_EN = re.compile(
    r"###\s+(?:シナリオ[A-D][）\)]\s*)?"
    r"(Base Case|Bull Case|Bear Case|Tail Risk)"
    r"[^(]*\((\d+)%\)",
    re.IGNORECASE,
)

# Fix 1: Format C — Japanese-only with 確率 notation
_SCENARIO_HEADER_JP = re.compile(
    r"###\s+シナリオ([A-D])[）\)]\s*"
    r"(.+?)"
    r"[（(]確率[：:]\s*(\d+)%",
)

# Support **トリガー**:, **トリガー条件**:, **条件**: and — from 2026-08-10 —
# a qualifier carried inside the bold label, e.g.
# "**トリガー (下記のうち2つ以上が終値ベースで成立)**:" or
# "**トリガー (いずれか1つの成立で発動)**:". Without the qualifier allowance the
# Risk-On and Caution blocks parse to an EMPTY trigger list, which Layer 2 then
# evaluates as "no conditions" instead of failing loudly.
_SCENARIO_TRIGGER = re.compile(
    r"\*\*(?:トリガー(?:条件)?|条件)[^*\n]*\*\*[：:]\s*(.+?)(?:\n\n|\n###|\n---|\Z)",
    re.DOTALL,
)

# The qualifier inside the bold trigger label states how many legs must hold.
# It is captured separately from the legs because "all 5" and "any 1" produce
# the same leg list but opposite verdicts.
_SCENARIO_TRIGGER_LABEL = re.compile(
    r"\*\*(?:トリガー(?:条件)?|条件)([^*\n]*)\*\*[：:]"
)

_RULE_AT_LEAST = re.compile(r"(\d+)\s*(?:つ|本|脚)以上")


def _parse_satisfaction_rule(block: str) -> tuple[str, int]:
    """Read the scenario's satisfaction rule from its trigger label.

    Returns (rule, min_legs) where rule is "all" / "any" / "at_least".
    Defaults to ("any", 1) when the label carries no qualifier, which matches
    how a bare "**トリガー**:" list has always been read.
    """
    m = _SCENARIO_TRIGGER_LABEL.search(block)
    if not m:
        return "any", 1
    qualifier = m.group(1)
    at_least = _RULE_AT_LEAST.search(qualifier)
    if at_least:
        return "at_least", int(at_least.group(1))
    if "すべて" in qualifier or "全て" in qualifier or "AND" in qualifier:
        return "all", 0
    if "いずれか" in qualifier or "1つ" in qualifier or "何れか" in qualifier:
        return "any", 1
    return "any", 1


_SCENARIO_ACTION_LINE = re.compile(
    r"-\s*(?:\*\*)?(?:コア|防御|テーマ|現金)[^:：]*(?:\*\*)?:\s*"
    r"(?:[\d]+%\s*→\s*)?(?:\*\*)?\s*(\d+)\s*%"
)

# Keywords for mapping Japanese scenario names to standard names
_BULL_KEYWORDS = frozenset({
    "反発", "回復", "加速", "上昇", "再開", "リスクオン", "V字",
})
_BEAR_KEYWORDS = frozenset({
    "悪化", "調整", "深化", "Caution", "下落", "弱気", "リスクオフ",
})


# The dash before "筆者推定" varies between blogs: ASCII double-hyphen "--"
# (used through 2026-05-11) and the em/en/horizontal-bar dash "—/–/―"
# (2026-05-18 onward). Accept all forms so scenario probabilities parse
# regardless of the writer's dash convention.
_SCENARIO_HEADER_D = re.compile(
    r"###\s+シナリオ\s*\d+\s*[（(]\s*(.+?)\s*[）)][：:]\s*"
    r".+?(?:--|[—–―])\s*筆者推定\s*\*{0,2}\s*(\d+)\s*%?\s*\*{0,2}",
)

# Inline Tail Risk note embedded in scenario blocks:
# "*Tail Risk（5%）: ... コア10%・防御21%(-2%)・テーマ17%・現金52%(+10%).*"
_TAIL_RISK_INLINE = re.compile(
    r"\*Tail Risk[（(]\s*(\d+)\s*%?\s*[）)]\s*[:：]"
)
_TAIL_RISK_CAT_ALLOC = re.compile(
    r"コア\s*(\d+)%[^・]*・\s*防御\s*(\d+)%[^・]*・\s*テーマ\s*(\d+)%[^・]*・\s*現金\s*(\d+)%"
)

# Inline ETF detail in scenario blocks:
# "SPY 12%→20%" → 20, "SPY 12%->20%" → 20, "QQQ 2%(復帰)" → 2, "DIA 8%維持" → 8
# The arrow form also appears without a "%" on either side (2026-07-20 onward):
# "SPY 17→19 (+2%)" → 19. Only the arrow form may omit "%", because a bare
# "TICKER <number>" would otherwise match quoted price levels (BIL/XLP/XLE/TLT
# all trade under $100, so a size cap alone cannot separate them).
# "コア **18%** (SPY 12 / QQQ 0 / DIA 6)" → capture the parenthesised breakdown.
_CATEGORY_PAREN_BREAKDOWN = re.compile(
    r"(?:コア|防御|テーマ)[^（(\n]{0,32}?\d+\s*%\*{0,2}\s*[（(]([^）)\n]*)[）)]"
)

# Inside a category parenthesis the percent sign is optional: "SPY 12", "GLD 13%".
_CATEGORY_PAREN_ETF = re.compile(
    r"(" + "|".join(_VALID_ETFS) + r")\s*\*{0,2}\s*(\d+(?:\.\d+)?)\s*%?"
)

_SCENARIO_ETF_INLINE = re.compile(
    r"(" + "|".join(_VALID_ETFS) + r")"
    r"\s+"
    r"(?:"
    r"\d+(?:\.\d+)?\s*%?\s*(?:→|->)\s*\*{0,2}\s*(?P<arrow>\d+(?:\.\d+)?)\s*%?"
    r"|"
    r"\*{0,2}\s*(?P<plain>\d+(?:\.\d+)?)\s*%"
    r")"
)


def _normalize_scenario_name_d(raw: str) -> str:
    """Map Format D parenthetical name to standard name.

    Only "base"/"bull"/"bear"/"tail_risk" are valid downstream
    (``strategy_intent`` rejects anything else), so the Japanese and
    Risk-On/Caution spellings used in the blogs must map onto them rather than
    falling through to a slugified passthrough.
    """
    lowered = raw.lower().strip()
    if lowered == "base":
        return "base"
    if lowered == "bull":
        return "bull"
    # Risk-On / リスクオン are the writer's names for the bull scenario.
    # "Bull / さらに上値追い" (2026-06-22) also belongs here — the substring check
    # runs before the bear/tail checks, which never contain "bull".
    if ("bull" in lowered or "risk-on" in lowered or "risk on" in lowered
            or "リスクオン" in lowered):
        return "bull"
    if "bear" in lowered and "tail" in lowered:
        return "bear"  # combined scenario
    if "bear" in lowered:
        return "bear"
    if "tail" in lowered:
        return "tail_risk"
    # 警戒 / Caution are the writer's names for the bear scenario.
    if "警戒" in raw or "caution" in lowered:
        return "bear"
    return lowered.replace(" ", "_")


def _parse_scenario_cash_pct(text: str) -> Optional[float]:
    """Extract cash percentage from scenario action line.

    Handles:
      - "現金 42%→**47%**" → 47  (take target after arrow)
      - "現金 **42%**"      → 42  (no arrow, take the value)
    """
    # The gap between 現金 and its percentage may contain a label such as
    # "・短期債 (BIL): " but never a digit. Excluding digits keeps the search
    # from skipping over the cash value to an unrelated arrow later in the same
    # line — e.g. "現金 **44%**。…XLEは4%→2%へ削減" must yield 44, not 2.
    gap = r"[^\d\n]{0,24}"
    for line in text.splitlines():
        if "現金" not in line:
            continue
        # Prefer the value after → or -> (the target of the change)
        arrow_m = re.search(
            r"現金" + gap + r"(\d+(?:\.\d+)?)\s*%\s*(?:→|->)\s*\*{0,2}\s*(\d+(?:\.\d+)?)\s*%",
            line,
        )
        if arrow_m:
            return float(arrow_m.group(2))
        # No arrow — take the percentage attached to 現金
        plain_m = re.search(r"現金" + gap + r"(\d+(?:\.\d+)?)\s*%", line)
        if plain_m:
            return float(plain_m.group(1))
    return None


def _action_section(block: str) -> str:
    """Return just the アクション part of a scenario block.

    Stops at the first blank line after the action header, or at a Tail Risk /
    probability / section marker. This prevents percentages and ETF mentions in
    later sections from overwriting the action's own values.
    """
    if "**アクション" not in block:
        return block
    section = block.split("**アクション")[1]
    # "\n**注" stops the scan before the scenario's footnotes. Those notes carry
    # conditional variants ("XLE は 5% 据え置き", "XLV 13% + GLD 14%") that would
    # otherwise overwrite the action's own ETF percentages.
    markers = ("\n\n", "\n**注", "\n*実行タイミング", "\n*Tail Risk",
               "\n*シナリオ確率", "\n---", "\n##")
    # Cut at the EARLIEST marker, not the first one that happens to appear in
    # this tuple. Scanning in tuple order let a blank line further down the block
    # win over a "**注1**" line right after the action, so the footnotes'
    # conditional percentages leaked into the allocation.
    positions = [pos for pos in (section.find(m) for m in markers) if pos != -1]
    return section[:min(positions)] if positions else section


def _parse_category_paren_etfs(action_section: str) -> dict[str, float]:
    """Extract ETF percentages from the one-line category-with-breakdown form.

    The Tail Risk action is written on a single line as::

        コア **18%** (SPY 12 / QQQ 0 / DIA 6) / 防御 **23%** (XLV 13 / XLP 10)

    Inside those parentheses the numbers carry no "%", so the general
    ``_SCENARIO_ETF_INLINE`` pattern (which requires "%" on the bare form to
    avoid swallowing quoted price levels) skips them and the block silently
    falls back to a default category split. Restricting the bare-number match to
    the inside of a category parenthesis makes it unambiguous: no price level
    ever appears there.
    """
    etf_alloc: dict[str, float] = {}
    for cat_m in _CATEGORY_PAREN_BREAKDOWN.finditer(action_section):
        for etf_m in _CATEGORY_PAREN_ETF.finditer(cat_m.group(1)):
            pct = float(etf_m.group(2))
            if pct > 100:
                continue
            etf_alloc[etf_m.group(1)] = pct
    return etf_alloc


def _parse_scenario_etf_detail(block: str) -> dict[str, float]:
    """Extract explicit ETF percentages from scenario action lines."""
    etf_alloc: dict[str, float] = {}
    action_section = _action_section(block)
    etf_alloc.update(_parse_category_paren_etfs(action_section))
    for m in _SCENARIO_ETF_INLINE.finditer(action_section):
        pct = float(m.group("arrow") or m.group("plain"))
        if pct > 100:
            continue  # a price level, not an allocation percentage
        etf_alloc[m.group(1)] = pct
    # Map "現金 X%" to BIL if BIL not already found
    if "BIL" not in etf_alloc:
        cash_pct = _parse_scenario_cash_pct(action_section)
        if cash_pct is not None:
            etf_alloc["BIL"] = cash_pct
    return etf_alloc


def _parse_scenarios(text: str) -> dict[str, ScenarioSpec]:
    """Parse the シナリオ別プラン section.

    Supports four header formats:
      A) ### Base Case: desc (55%)            — 2026-01-12 onwards
      B) ### シナリオA) Base Case: desc (55%)  — 2025-11-24 to 2026-01-05
      C) ### シナリオA）Japanese desc（確率：45%） — 2025-11-03 to 2025-11-17
      D) ### シナリオ1（Base）: desc -- 筆者推定45% — 2026-03-09 onwards
    """
    scenarios: dict[str, ScenarioSpec] = {}

    current = _parse_sector_allocation(text)
    etf_ratios = _build_etf_ratios(current)

    # Try Format D first (latest blogs: シナリオ1（Base）... 筆者推定45%)
    headers_d = list(_SCENARIO_HEADER_D.finditer(text))
    if headers_d:
        for idx, header_match in enumerate(headers_d):
            raw_name = header_match.group(1)
            probability = int(header_match.group(2))
            name = _normalize_scenario_name_d(raw_name)

            start = header_match.end()
            end = headers_d[idx + 1].start() if idx + 1 < len(headers_d) else len(text)
            block = text[start:end]

            triggers = _parse_trigger_list(block)

            # ETF detail extraction takes priority over category distribution
            etf_detail = _parse_scenario_etf_detail(block)
            if sum(etf_detail.values()) >= 90:
                alloc = etf_detail
            else:
                cat_alloc = _parse_category_allocation(block)
                alloc = _distribute_to_etfs(cat_alloc, etf_ratios) if cat_alloc else dict(current)
                # Overlay explicit ETF details
                alloc.update(etf_detail)

            rule, min_legs = _parse_satisfaction_rule(block)
            scenarios[name] = ScenarioSpec(
                name=name, probability=probability,
                triggers=triggers, allocation=alloc,
                satisfaction_rule=rule, min_legs=min_legs,
            )

        # Check for inline Tail Risk note (embedded as *Tail Risk（5%）:...*)
        if "tail_risk" not in scenarios:
            tail_m = _TAIL_RISK_INLINE.search(text)
            if tail_m:
                tail_prob = int(tail_m.group(1))
                tail_line = text[tail_m.start(): text.find("\n", tail_m.start()) + 1]
                cat_m = _TAIL_RISK_CAT_ALLOC.search(tail_line)
                if cat_m:
                    tail_cat = {
                        "core": int(cat_m.group(1)),
                        "defensive": int(cat_m.group(2)),
                        "theme": int(cat_m.group(3)),
                        "cash": int(cat_m.group(4)),
                    }
                    tail_alloc = _distribute_to_etfs(tail_cat, etf_ratios)
                else:
                    tail_alloc = dict(current)
                scenarios["tail_risk"] = ScenarioSpec(
                    name="tail_risk", probability=tail_prob,
                    triggers=[], allocation=tail_alloc,
                )

        return scenarios

    # Try EN headers (Format A and B)
    headers_en = list(_SCENARIO_HEADER_EN.finditer(text))
    if headers_en:
        for idx, header_match in enumerate(headers_en):
            raw_name = header_match.group(1)
            probability = int(header_match.group(2))
            name = _normalize_scenario_name(raw_name)

            start = header_match.end()
            end = headers_en[idx + 1].start() if idx + 1 < len(headers_en) else len(text)
            block = text[start:end]

            triggers = _parse_trigger_list(block)

            # ETF detail extraction takes priority
            etf_detail = _parse_scenario_etf_detail(block)
            if sum(etf_detail.values()) >= 90:
                alloc = etf_detail
            else:
                cat_alloc = _parse_category_allocation(block)
                alloc = _distribute_to_etfs(cat_alloc, etf_ratios) if cat_alloc else dict(current)
                alloc.update(etf_detail)

            rule, min_legs = _parse_satisfaction_rule(block)
            scenarios[name] = ScenarioSpec(
                name=name, probability=probability,
                triggers=triggers, allocation=alloc,
                satisfaction_rule=rule, min_legs=min_legs,
            )
        return scenarios

    # Try JP headers (Format C)
    headers_jp = list(_SCENARIO_HEADER_JP.finditer(text))
    if headers_jp:
        # Collect raw scenario data
        raw_scenarios: list[tuple[str, str, int, list[str], dict[str, float]]] = []
        for idx, header_match in enumerate(headers_jp):
            letter = header_match.group(1)
            desc = header_match.group(2).strip()
            probability = int(header_match.group(3))

            start = header_match.end()
            end = headers_jp[idx + 1].start() if idx + 1 < len(headers_jp) else len(text)
            block = text[start:end]

            triggers = _parse_trigger_list(block)
            cat_alloc = _parse_category_allocation(block)
            alloc = _distribute_to_etfs(cat_alloc, etf_ratios) if cat_alloc else dict(current)

            raw_scenarios.append((letter, desc, probability, triggers, alloc))

        # Map Japanese names to standard scenario names
        name_map = _map_jp_scenarios_to_names(
            [(letter, desc, prob) for letter, desc, prob, _, _ in raw_scenarios]
        )

        for letter, desc, prob, triggers, alloc in raw_scenarios:
            name = name_map.get(letter, letter.lower())
            rule, min_legs = _parse_satisfaction_rule(block)
            scenarios[name] = ScenarioSpec(
                name=name, probability=prob,
                triggers=triggers, allocation=alloc,
                satisfaction_rule=rule, min_legs=min_legs,
            )

    return scenarios


_INDICATOR_KEYWORDS = (
    "VIX", "S&P", "SPX", "原油", "Breadth", "Uptrend", "10Y", "10年債", "10年金利",
    "Nasdaq", "NDX", "Dow", "ゴールド", "Gold", "WTI", "Core PCE", "PCE", "GDP",
)


def _has_indicator_keyword(text: str) -> bool:
    return any(kw in text for kw in _INDICATOR_KEYWORDS)


_TRIGGER_SEPARATOR = re.compile(r"\s+\+\s+|\s+or\s+|、")
_OPEN_PARENS = "(（"
_CLOSE_PARENS = ")）"


def _split_trigger_parts(raw: str) -> list[str]:
    """Split a trigger line on top-level `+` / `or` / `、` separators.

    Parenthesised spans are kept intact so that a qualifier such as
    "VIX 26超 (ザラ場、即時)" is not torn into "VIX 26超 (ザラ場" + "即時)".
    Square brackets are deliberately NOT protected: they group OR legs
    ("[WTI ... or 10年債 ...]") which downstream consumers evaluate separately.
    """
    parts: list[str] = []
    depth = 0
    start = 0
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch in _OPEN_PARENS:
            depth += 1
            i += 1
            continue
        if ch in _CLOSE_PARENS:
            depth = max(0, depth - 1)
            i += 1
            continue
        if depth == 0:
            m = _TRIGGER_SEPARATOR.match(raw, i)
            if m:
                parts.append(raw[start:i])
                i = m.end()
                start = i
                continue
        i += 1
    parts.append(raw[start:])
    return parts


def _parse_trigger_list(block: str) -> list[str]:
    """Extract trigger strings from a scenario block.

    Splits on `+`, `or`, `、` boundaries while requiring whitespace around `+` and
    `or` to avoid splitting words like "Core" or numbers like "+0.3%". For bare
    price/number fragments (e.g. "$105 終値 2 日連続"), inherits the indicator
    name from the previous fragment so downstream consumers can identify the
    underlying asset.
    """
    trigger_match = _SCENARIO_TRIGGER.search(block)
    triggers: list[str] = []
    if not trigger_match:
        return triggers
    raw = trigger_match.group(1).strip()
    parts = _split_trigger_parts(raw)
    prev_indicator: str | None = None
    for part in parts:
        cleaned = re.sub(r"\*\*", "", part).strip()
        # Strip stray group brackets left by splitting an OR group such as
        # "[WTI 100ドル上抜け or 10年債 4.806% 上抜け]".
        cleaned = cleaned.strip("[]［］").strip()
        if not cleaned:
            continue
        if (
            prev_indicator
            and not _has_indicator_keyword(cleaned)
            and re.match(r"^[\$\d]", cleaned)
        ):
            cleaned = f"{prev_indicator} {cleaned}"
        triggers.append(cleaned)
        for kw in _INDICATOR_KEYWORDS:
            if kw in cleaned:
                prev_indicator = kw
                break
    return triggers


def _map_jp_scenarios_to_names(
    scenarios: list[tuple[str, str, int]],
) -> dict[str, str]:
    """Map Japanese scenario descriptions to standard names.

    Args:
        scenarios: [(letter, description, probability), ...]

    Returns:
        {letter: standard_name} e.g. {"A": "base", "B": "bull", "C": "bear"}

    Rules:
        1. Highest probability → "base"
        2. Contains bull keywords → "bull"
        3. Contains bear keywords → "bear"
        4. Remaining → fill unfilled slots in probability order
    """
    if not scenarios:
        return {}

    sorted_by_prob = sorted(scenarios, key=lambda x: x[2], reverse=True)
    result: dict[str, str] = {}
    used_names: set[str] = set()

    # Highest probability → base
    base = sorted_by_prob[0]
    result[base[0]] = "base"
    used_names.add("base")

    # Classify remaining by keywords
    remaining = sorted_by_prob[1:]
    unclassified: list[tuple[str, str, int]] = []

    for letter, desc, prob in remaining:
        if "bull" not in used_names and any(kw in desc for kw in _BULL_KEYWORDS):
            result[letter] = "bull"
            used_names.add("bull")
        elif "bear" not in used_names and any(kw in desc for kw in _BEAR_KEYWORDS):
            result[letter] = "bear"
            used_names.add("bear")
        else:
            unclassified.append((letter, desc, prob))

    # Fill remaining slots
    available = [n for n in ["bull", "bear", "tail_risk"] if n not in used_names]
    for (letter, desc, prob), name in zip(unclassified, available):
        result[letter] = name

    return result


_CATEGORY_NAMES = {
    "コア": "core",
    "防御": "defensive",
    "テーマ": "theme",
    "現金": "cash",
}

# Support range format in "from → to" pattern (e.g. "40-45% → **30-35%**").
# The colon after the category label is optional: blogs write both
# "- コア: 40% → **45%**" and "- コア 28% → **33%**" (2026-07-20 onward).
# The label tail is capped and excludes digits, "(" and "$" so that dollar
# example lines ("- コア指数: $40K") and parenthesised ETF detail never supply
# the percentage.
_CAT_LABEL_TAIL = r"(?:\*\*)?[^\d\n$＄(（]{0,12}"
_CAT_ALLOC_VALUE = (
    r"(?:[\d]+(?:\s*-\s*\d+)?\s*%\s*(?:→|->)\s*)?"
    r"(?:\*\*)?\s*(?P<pct>\d+)(?:\s*-\s*(?P<pct_hi>\d+))?\s*%"
)
_CAT_ALLOC_LINE = re.compile(
    r"-\s*(?:\*\*)?(?P<cat>コア|防御|テーマ|現金)" + _CAT_LABEL_TAIL + _CAT_ALLOC_VALUE
)

# Tail Risk actions are written as one inline run rather than a bullet list:
# "コア **15%** (SPY 9/QQQ 2/DIA 4) / 防御 **25%** (...) / テーマ **16%** / 現金 **44%**"
_CAT_ALLOC_INLINE = re.compile(
    r"(?:^|[/／、,—–―(（]|\s)\s*(?:\*\*)?(?P<cat>コア|防御|テーマ|現金)"
    + _CAT_LABEL_TAIL
    + _CAT_ALLOC_VALUE
)


def _parse_category_allocation(block: str) -> Optional[dict[str, int]]:
    """Parse category-level allocation from a scenario action block.

    Returns {"core": 34, "defensive": 24, "theme": 14, "cash": 28} or None.

    Tries the bullet-list form first. If that does not yield a full set, falls
    back to the inline "コア 15% / 防御 25% / ..." form used by Tail Risk, which
    is matched only inside the action section so that percentages quoted in the
    根拠 / トリガー prose cannot be mistaken for an allocation.
    """
    def _collect(pattern: re.Pattern[str], source: str) -> dict[str, int]:
        found: dict[str, int] = {}
        for m in pattern.finditer(source):
            cat_en = _CATEGORY_NAMES.get(m.group("cat"))
            if not cat_en:
                continue
            lo = int(m.group("pct"))
            hi_str = m.group("pct_hi")
            found[cat_en] = round((lo + int(hi_str)) / 2) if hi_str else lo
        return found

    result = _collect(_CAT_ALLOC_LINE, block)
    if len(result) < 3:
        # The inline form always spells out all four categories, so require the
        # full set. A partial match means the text is prose, not an allocation,
        # and a partial set would silently drop a category from the total.
        inline = _collect(_CAT_ALLOC_INLINE, _action_section(block))
        if len(inline) == 4:
            result = inline

    return result if len(result) >= 3 else None


def _build_etf_ratios(current: dict[str, float]) -> dict[str, dict[str, float]]:
    """Build a map of category -> {ETF: ratio_within_category}.

    Given current = {"SPY": 22, "QQQ": 4, "DIA": 8, "XLV": 12, ...},
    returns e.g. {"core": {"SPY": 0.647, "QQQ": 0.118, "DIA": 0.235}, ...}
    """
    categories: dict[str, list[str]] = {
        "core": ["SPY", "QQQ", "DIA", "IWM"],
        "defensive": ["XLV", "XLP"],
        "theme": ["GLD", "XLE", "URA", "TLT", "COPX"],
        "cash": ["BIL"],
    }

    ratios: dict[str, dict[str, float]] = {}
    for cat, symbols in categories.items():
        total = sum(current.get(s, 0.0) for s in symbols)
        if total > 0:
            ratios[cat] = {s: current.get(s, 0.0) / total for s in symbols if current.get(s, 0.0) > 0}
        else:
            # Fallback: equal distribution
            present = [s for s in symbols if s in current]
            if present:
                ratios[cat] = {s: 1.0 / len(present) for s in present}
            else:
                ratios[cat] = {symbols[0]: 1.0}

    return ratios


def _distribute_to_etfs(
    cat_alloc: dict[str, int],
    etf_ratios: dict[str, dict[str, float]],
) -> dict[str, float]:
    """Distribute category percentages to individual ETFs using ratios."""
    result: dict[str, float] = {}
    for cat, pct in cat_alloc.items():
        if cat in etf_ratios:
            for symbol, ratio in etf_ratios[cat].items():
                result[symbol] = round(pct * ratio, 1)

    return result


def _normalize_scenario_name(raw: str) -> str:
    mapping = {
        "base case": "base",
        "bull case": "bull",
        "bear case": "bear",
        "tail risk": "tail_risk",
    }
    return mapping.get(raw.lower(), raw.lower().replace(" ", "_"))


# --- Trading levels -------------------------------------------------------

_INDEX_NAME_MAP = {
    "s&p 500": "sp500",
    "s&p500": "sp500",
    "nasdaq 100": "nasdaq",
    "nasdaq100": "nasdaq",
    "ダウ": "dow",
    "gold": "gold",
    "oil (wti)": "oil",
    "oil(wti)": "oil",
}

_MARKDOWN_TABLE_LINE = re.compile(r"^\|.*\|$")
_TABLE_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
_NUMBER_TOKEN = re.compile(r"\$?\d[\d,]*(?:\.\d+)?")


def _split_markdown_row(line: str) -> list[str]:
    """Split a markdown table row into cells."""
    row = line.strip()
    if not _MARKDOWN_TABLE_LINE.match(row):
        return []
    return [cell.strip() for cell in row.strip("|").split("|")]


def _is_table_separator(cells: list[str]) -> bool:
    """Return True if a row is a markdown separator like |---|:---:|."""
    if not cells:
        return False
    return all(_TABLE_SEPARATOR_CELL.match(c.replace(" ", "")) for c in cells)


def _normalize_trading_level_name(raw: str) -> Optional[str]:
    """Normalize a trading-level row label to StrategySpec index keys."""
    cleaned = re.sub(r"\*+", "", raw).strip()
    lowered = cleaned.lower()

    if "s&p" in lowered:
        return "sp500"
    if "nasdaq" in lowered:
        return "nasdaq"
    if "ダウ" in cleaned or "dow" in lowered:
        return "dow"
    if "gold" in lowered or "金" in cleaned:
        return "gold"
    if "oil" in lowered or "wti" in lowered or "原油" in cleaned:
        return "oil"
    return _INDEX_NAME_MAP.get(lowered)


def _parse_first_number_token(s: str) -> Optional[float]:
    """Parse the first numeric token from a table cell."""
    m = _NUMBER_TOKEN.search(s)
    if not m:
        return None
    return _parse_number(m.group(0))


def _parse_trading_levels(text: str) -> dict[str, TradingLevel]:
    """Parse the 今週の売買レベル table."""
    # Limit parsing to the trading levels section to avoid matching
    # the マーケット状況 table which has a different column layout.
    section = _extract_section(text, _TRADING_LEVELS_SECTION_KEYWORD)
    if not section:
        section = text

    levels: dict[str, TradingLevel] = {}
    for line in section.splitlines():
        cells = _split_markdown_row(line)
        if len(cells) < 4:
            continue
        if _is_table_separator(cells):
            continue

        key = _normalize_trading_level_name(cells[0])
        if not key:
            continue

        level = TradingLevel(
            buy_level=_parse_first_number_token(cells[1]),
            sell_level=_parse_first_number_token(cells[2]),
            stop_loss=_parse_first_number_token(cells[3]),
        )

        # Require at least one parsed number to avoid accidental empty rows.
        if level.buy_level is None and level.sell_level is None and level.stop_loss is None:
            continue
        levels[key] = level
    return levels


# --- Stop losses ----------------------------------------------------------

_STOP_LOSS_PATTERN = re.compile(
    r"\*?\*?"
    r"(?P<name>S&P\s*500|Nasdaq|ダウ|VIX|10Y利回り)"
    r"\*?\*?:\s*"
    r"(?P<value>[0-9,.$]+(?:\.\d+)?(?:%)?)\s*(?:割れ|超[持続]*)"
)


def _parse_stop_losses(text: str) -> dict[str, float]:
    """Parse the ストップロス section."""
    stop_section = _extract_section(text, "ストップロス")
    if not stop_section:
        return {}

    losses: dict[str, float] = {}
    for m in _STOP_LOSS_PATTERN.finditer(stop_section):
        raw_name = m.group("name").strip().lower()
        key = _INDEX_NAME_MAP.get(raw_name, raw_name)
        if key == "vix":
            continue  # VIX is a trigger, not a price stop-loss
        if "10y" in key or "利回り" in key:
            continue  # Yield trigger, not price stop-loss
        val = _parse_number(m.group("value"))
        if val is not None:
            losses[key] = val

    return losses


# --- VIX triggers ---------------------------------------------------------

_VIX_THRESHOLDS = re.compile(
    r"\*?\*?VIX\*?\*?\s*\|[^|]*\|\s*"
    r"\*?\*?(\d+(?:\.\d+)?)\*?\*?\s*\(Risk-On\)\s*/\s*"
    r"\*?\*?(\d+(?:\.\d+)?)\*?\*?\s*\(Caution\)\s*/\s*"
    r"\*?\*?(\d+(?:\.\d+)?)\*?\*?\s*\(Stress\)"
)

# Fallback: slash-separated values without labels, optional bold/decorator text
# Format: | **VIX** | current | 17 / 20 / 23 / 26 | note
# Or: 17 / **20突破** / **23** / 26 (bold + suffix text allowed)
# The threshold cell is captured whole (not four fixed groups) because blogs may
# add chart annotations such as `**14.00 (手描き下限)** / **17** / 20 / 23 / 26`.
# Reading such a cell positionally shifts every level down one rung.
_VIX_THRESHOLD_CELL = re.compile(r"\*?\*?VIX\*?\*?\s*\|[^|\n]*\|([^|\n]*)")

_VIX_LEVEL_IN_SEGMENT = re.compile(r"\d+(?:\.\d+)?")

# Standard Monty ladder (CLAUDE.md "Monty Style" rule 2). Values outside it are
# chart annotations, not regime boundaries.
_VIX_LADDER: tuple[tuple[str, float], ...] = (
    ("risk_on", 17.0),
    ("caution", 20.0),
    ("stress", 23.0),
    ("panic", 26.0),
)

_VIX_POSITIONAL_KEYS = ("risk_on", "caution", "stress", "panic")


def _parse_vix_threshold_levels(text: str) -> list[float]:
    """Return every numeric level listed in the VIX threshold cell, in order."""
    m = _VIX_THRESHOLD_CELL.search(text)
    if not m:
        return []

    levels: list[float] = []
    for segment in m.group(1).split("/"):
        num = _VIX_LEVEL_IN_SEGMENT.search(segment)
        if num:
            levels.append(float(num.group()))
    return levels


def _parse_vix_triggers(text: str) -> dict[str, float]:
    """Parse VIX trigger levels from the マーケット状況 table."""
    m = _VIX_THRESHOLDS.search(text)
    if m:
        return {
            "risk_on": float(m.group(1)),
            "caution": float(m.group(2)),
            "stress": float(m.group(3)),
        }

    levels = _parse_vix_threshold_levels(text)
    if len(levels) < 3:
        return {}

    # Anchor on the standard ladder by value whenever the cell carries most of it,
    # so extra annotation levels cannot shift the mapping.
    by_value = {key: level for key, level in _VIX_LADDER if level in levels}
    if len(by_value) >= 3:
        return by_value

    return dict(zip(_VIX_POSITIONAL_KEYS, levels[:4]))


# --- Yield triggers -------------------------------------------------------

_YIELD_THRESHOLDS = re.compile(
    r"\*?\*?10Y(?:\s*/\s*30Y)?\s*利回り\*?\*?\s*\|[^|]*\|\s*"
    r"(\d+\.\d+)%?\s*\(下限\)\s*/\s*"
    r"(\d+\.\d+)%?\s*\(警戒\)\s*/\s*"
    r"(\d+\.\d+)%?\s*\(赤\)"
)

# Fallback: slash-separated values without labels, with optional space in "10Y 利回り"
# Format: | **10Y 利回り** | current | 4.11% / 4.36% / 4.50% / 4.60% | note
# Bold/decorator text between values is tolerated, e.g. "4.11% / **4.36%突破** / **4.50%** / 4.60%"
# Combined row headers like "10Y / 30Y 利回り" are tolerated; thresholds are read
# from the 3rd cell so the combined current-value cell (4.750% / 5.270%) is skipped.
_YIELD_THRESHOLDS_SLASH = re.compile(
    r"\*?\*?10Y(?:\s*/\s*30Y)?\s*利回り\*?\*?\s*\|[^|]*\|\s*"
    r"\*?\*?(\d+\.\d+)%?[^/|]*?/\s*"
    r"\*?\*?(\d+\.\d+)%?[^/|]*?/\s*"
    r"\*?\*?(\d+\.\d+)%?[^/|]*?/\s*"
    r"\*?\*?(\d+\.\d+)%?"
)


def _parse_yield_triggers(text: str) -> dict[str, float]:
    """Parse yield trigger levels from the マーケット状況 table."""
    m = _YIELD_THRESHOLDS.search(text)
    if m:
        return {
            "lower": float(m.group(1)),
            "warning": float(m.group(2)),
            "red_line": float(m.group(3)),
        }
    m2 = _YIELD_THRESHOLDS_SLASH.search(text)
    if m2:
        return {
            "lower": float(m2.group(1)),
            "warning": float(m2.group(2)),
            "red_line": float(m2.group(3)),
            "extreme": float(m2.group(4)),
        }
    return {}


# --- Breadth / Uptrend ----------------------------------------------------

_BREADTH_200MA = re.compile(
    r"Breadth\s*\(?200\s*MA\)?\s*\*?\*?\s*\|\s*\*?\*?\s*(\d+(?:\.\d+)?)\s*%"
)

_UPTREND_RATIO = re.compile(
    r"Uptrend\s*Ratio\s*\*?\*?\s*\|\s*\*?\*?\s*~?\s*(\d+(?:\.\d+)?)"
)


def _parse_breadth_200ma(text: str) -> Optional[float]:
    m = _BREADTH_200MA.search(text)
    return float(m.group(1)) if m else None


def _parse_uptrend_ratio(text: str) -> Optional[float]:
    m = _UPTREND_RATIO.search(text)
    return float(m.group(1)) if m else None


# --- Bubble score ---------------------------------------------------------

_BUBBLE_SCORE = re.compile(
    r"バブルスコア\s*(\d+)\s*/\s*(\d+)\s*点"
)


def _parse_bubble_score(text: str) -> Optional[int]:
    m = _BUBBLE_SCORE.search(text)
    return int(m.group(1)) if m else None


# --- Pre-event dates ------------------------------------------------------

_EVENT_DATE = re.compile(
    r"\|\s*\*?\*?(\d+/\d+)\s*\([月火水木金土日]\)\*?\*?\s*\|"
)


def _parse_pre_event_dates(text: str, blog_date: str = "") -> list[str]:
    """Extract event dates from the 重要イベント table.

    Converts M/DD format to YYYY-MM-DD using the blog year.
    This ensures dates match the ISO format used by OrderValidator.
    """
    event_section = _extract_section(text, "重要イベント")
    if not event_section:
        return []

    # Infer year from blog_date (YYYY-MM-DD)
    if len(blog_date) >= 7:
        year = int(blog_date[:4])
        blog_month = int(blog_date[5:7])
    else:
        from datetime import date as _date
        year = _date.today().year
        blog_month = _date.today().month

    dates: list[str] = []
    for m in _EVENT_DATE.finditer(event_section):
        raw = m.group(1)  # e.g. "2/18"
        parts = raw.split("/")
        month = int(parts[0])
        day = int(parts[1])
        # Handle year rollover (blog in Nov/Dec, event in Jan/Feb)
        event_year = year + 1 if (blog_month >= 11 and month <= 2) else year
        iso = f"{event_year}-{month:02d}-{day:02d}"
        if iso not in dates:
            dates.append(iso)

    return dates


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

_PHASE_PATTERN = re.compile(
    r"現在フェーズ\*?\*?\s*[:：]\s*\*?\*?\s*(.+?)(?:\s*--|[\*\n])"
)


def _parse_phase(text: str) -> Optional[str]:
    """Parse market phase from '現在フェーズ: **Stress（危機）継続**' etc."""
    m = _PHASE_PATTERN.search(text)
    if not m:
        return None
    raw = re.sub(r"\*+", "", m.group(1)).strip()
    word_m = re.match(r"(\w+)", raw)
    return word_m.group(1) if word_m else raw


def _parse_number(s: str) -> Optional[float]:
    """Parse a number string like '6,771', '$5,046.3', '4.050%' into a float."""
    if not s:
        return None
    cleaned = s.replace(",", "").replace("$", "").replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_section(text: str, heading_keyword: str) -> Optional[str]:
    """Extract text from a section containing heading_keyword until the next section."""
    pattern = re.compile(
        r"^(#{1,4})\s+.*" + re.escape(heading_keyword) + r".*$",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        return None

    level = len(m.group(1))
    start = m.end()

    # Find next heading of same or higher level
    next_heading = re.compile(r"^#{1," + str(level) + r"}\s+", re.MULTILINE)
    end_match = next_heading.search(text, start)
    end = end_match.start() if end_match else len(text)

    return text[start:end]
