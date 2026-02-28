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
_ETF_SYMBOLS = re.compile(
    r"(SPY|QQQ|DIA|XLV|XLP|GLD|XLE|BIL|TLT|URA|SH|SDS)\s*"
    r"(\d+(?:\.\d+)?)"
    r"(?:\s*-\s*(\d+(?:\.\d+)?))?"
    r"\s*%"
)

# Fix 2: Support range format for cash row
_CASH_ROW = re.compile(
    r"\|\s*\*?\*?現金[・&]?短期債\*?\*?\s*\|\s*"
    r"(?:\*?\*?)?\s*(\d+)(?:\s*-\s*(\d+))?\s*%"
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


def _parse_sector_allocation(text: str) -> dict[str, float]:
    """Parse the セクター配分 table for individual ETF percentages.

    Looks for a table with rows like:
        | コア指数 | 34% | SPY 22%、QQQ 4%、DIA 8% |
    and the cash row:
        | 現金・短期債 | 28% | BIL、MMF |

    Falls back to category-level parsing for early blogs that lack
    individual ETF percentages.
    """
    alloc: dict[str, float] = {}

    # Parse from the dedicated allocation section first so scenario blocks
    # (which can contain ETF percentages) do not overwrite current allocation.
    section = _extract_section(text, _SECTOR_ALLOCATION_SECTION_KEYWORD)
    parse_source = section if section else text

    for m in _ETF_SYMBOLS.finditer(parse_source):
        symbol = m.group(1)
        pct = _midpoint(float(m.group(2)), m.group(3))
        # Keep the last occurrence inside the allocation section.
        alloc[symbol] = pct

    # Cash row: assign to BIL
    cash_matches = list(_CASH_ROW.finditer(parse_source))
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

# Support both **トリガー**: and **トリガー条件**: and **条件**:
_SCENARIO_TRIGGER = re.compile(
    r"\*\*(?:トリガー(?:条件)?|条件)\*\*[：:]\s*(.+?)(?:\n\n|\n###|\n---|\Z)",
    re.DOTALL,
)

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


def _parse_scenarios(text: str) -> dict[str, ScenarioSpec]:
    """Parse the シナリオ別プラン section.

    Supports three header formats:
      A) ### Base Case: desc (55%)            — 2026-01-12 onwards
      B) ### シナリオA) Base Case: desc (55%)  — 2025-11-24 to 2026-01-05
      C) ### シナリオA）Japanese desc（確率：45%） — 2025-11-03 to 2025-11-17
    """
    scenarios: dict[str, ScenarioSpec] = {}

    current = _parse_sector_allocation(text)
    etf_ratios = _build_etf_ratios(current)

    # Try EN headers first (Format A and B)
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
            cat_alloc = _parse_category_allocation(block)
            alloc = _distribute_to_etfs(cat_alloc, etf_ratios) if cat_alloc else dict(current)

            scenarios[name] = ScenarioSpec(
                name=name, probability=probability,
                triggers=triggers, allocation=alloc,
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
            scenarios[name] = ScenarioSpec(
                name=name, probability=prob,
                triggers=triggers, allocation=alloc,
            )

    return scenarios


def _parse_trigger_list(block: str) -> list[str]:
    """Extract trigger strings from a scenario block."""
    trigger_match = _SCENARIO_TRIGGER.search(block)
    triggers: list[str] = []
    if trigger_match:
        raw = trigger_match.group(1).strip()
        for part in re.split(r"\s*(?:\+|or|、)\s*", raw):
            cleaned = re.sub(r"\*\*", "", part).strip()
            if cleaned:
                triggers.append(cleaned)
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

# Support range format in "from → to" pattern (e.g. "40-45% → **30-35%**")
_CAT_ALLOC_LINE = re.compile(
    r"-\s*(?:\*\*)?(?P<cat>コア|防御|テーマ|現金)[^:：]*(?:\*\*)?[：:]\s*"
    r"(?:[\d]+(?:\s*-\s*\d+)?%\s*→\s*)?"
    r"(?:\*\*)?\s*(?P<pct>\d+)(?:\s*-\s*(?P<pct_hi>\d+))?\s*%"
)


def _parse_category_allocation(block: str) -> Optional[dict[str, int]]:
    """Parse category-level allocation from a scenario action block.

    Returns {"core": 34, "defensive": 24, "theme": 14, "cash": 28} or None.
    """
    result: dict[str, int] = {}
    for m in _CAT_ALLOC_LINE.finditer(block):
        cat_jp = m.group("cat")
        cat_en = _CATEGORY_NAMES.get(cat_jp)
        if cat_en:
            lo = int(m.group("pct"))
            hi_str = m.group("pct_hi")
            if hi_str:
                result[cat_en] = round((lo + int(hi_str)) / 2)
            else:
                result[cat_en] = lo

    return result if len(result) >= 3 else None


def _build_etf_ratios(current: dict[str, float]) -> dict[str, dict[str, float]]:
    """Build a map of category -> {ETF: ratio_within_category}.

    Given current = {"SPY": 22, "QQQ": 4, "DIA": 8, "XLV": 12, ...},
    returns e.g. {"core": {"SPY": 0.647, "QQQ": 0.118, "DIA": 0.235}, ...}
    """
    categories: dict[str, list[str]] = {
        "core": ["SPY", "QQQ", "DIA"],
        "defensive": ["XLV", "XLP"],
        "theme": ["GLD", "XLE", "URA", "TLT"],
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


def _parse_vix_triggers(text: str) -> dict[str, float]:
    """Parse VIX trigger levels from the マーケット状況 table."""
    m = _VIX_THRESHOLDS.search(text)
    if not m:
        return {}
    return {
        "risk_on": float(m.group(1)),
        "caution": float(m.group(2)),
        "stress": float(m.group(3)),
    }


# --- Yield triggers -------------------------------------------------------

_YIELD_THRESHOLDS = re.compile(
    r"\*?\*?10Y利回り\*?\*?\s*\|[^|]*\|\s*"
    r"(\d+\.\d+)%?\s*\(下限\)\s*/\s*"
    r"(\d+\.\d+)%?\s*\(警戒\)\s*/\s*"
    r"(\d+\.\d+)%?\s*\(赤\)"
)


def _parse_yield_triggers(text: str) -> dict[str, float]:
    """Parse yield trigger levels from the マーケット状況 table."""
    m = _YIELD_THRESHOLDS.search(text)
    if not m:
        return {}
    return {
        "lower": float(m.group(1)),
        "warning": float(m.group(2)),
        "red_line": float(m.group(3)),
    }


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
