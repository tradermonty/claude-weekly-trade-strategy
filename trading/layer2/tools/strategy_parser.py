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
        pre_event_dates=_parse_pre_event_dates(text),
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

_ETF_SYMBOLS = re.compile(
    r"(SPY|QQQ|DIA|XLV|XLP|GLD|XLE|BIL|TLT|URA|SH|SDS)\s*"
    r"(\d+(?:\.\d+)?)\s*%"
)

_CASH_ROW = re.compile(
    r"\|\s*\*?\*?現金[・&]?短期債\*?\*?\s*\|\s*(\d+)\s*%"
)


def _parse_sector_allocation(text: str) -> dict[str, float]:
    """Parse the セクター配分 table for individual ETF percentages.

    Looks for a table with rows like:
        | コア指数 | 34% | SPY 22%、QQQ 4%、DIA 8% |
    and the cash row:
        | 現金・短期債 | 28% | BIL、MMF |
    """
    alloc: dict[str, float] = {}

    # Find the sector allocation section (セクター配分 or the second table with ETFs)
    # Use the table that contains individual ETF percentages
    for m in _ETF_SYMBOLS.finditer(text):
        symbol = m.group(1)
        pct = float(m.group(2))
        # Keep the last occurrence (the セクター配分 table comes after ロット管理)
        alloc[symbol] = pct

    # Cash row: assign to BIL
    cash_matches = list(_CASH_ROW.finditer(text))
    if cash_matches:
        # Use the last match (from セクター配分 table)
        alloc["BIL"] = float(cash_matches[-1].group(1))

    return alloc


# --- Scenarios ------------------------------------------------------------

_SCENARIO_HEADER = re.compile(
    r"###\s+"
    r"(Base Case|Bull Case|Bear Case|Tail Risk)"
    r"[^(]*\((\d+)%\)",
    re.IGNORECASE,
)

_SCENARIO_TRIGGER = re.compile(r"\*\*トリガー\*\*:\s*(.+?)(?:\n\n|\n###|\n---|\Z)", re.DOTALL)

_SCENARIO_ACTION_LINE = re.compile(
    r"-\s*(?:\*\*)?(?:コア|防御|テーマ|現金)[^:：]*(?:\*\*)?:\s*"
    r"(?:[\d]+%\s*→\s*)?(?:\*\*)?\s*(\d+)\s*%"
)

_CATEGORY_ETF_MAP: dict[str, dict[str, float]] = {}  # built dynamically


def _parse_scenarios(text: str) -> dict[str, ScenarioSpec]:
    """Parse the シナリオ別プラン section."""
    scenarios: dict[str, ScenarioSpec] = {}

    # First, get the current allocation to distribute category %s to ETFs
    current = _parse_sector_allocation(text)

    # Get the base category->ETF ratios from current allocation
    etf_ratios = _build_etf_ratios(current)

    # Split text into scenario blocks
    headers = list(_SCENARIO_HEADER.finditer(text))
    for idx, header_match in enumerate(headers):
        raw_name = header_match.group(1)
        probability = int(header_match.group(2))
        name = _normalize_scenario_name(raw_name)

        # Extract the block of text for this scenario
        start = header_match.end()
        end = headers[idx + 1].start() if idx + 1 < len(headers) else len(text)
        block = text[start:end]

        # Parse triggers
        trigger_match = _SCENARIO_TRIGGER.search(block)
        triggers: list[str] = []
        if trigger_match:
            raw = trigger_match.group(1).strip()
            # Split on common separators
            for part in re.split(r"\s*(?:\+|or|、)\s*", raw):
                cleaned = re.sub(r"\*\*", "", part).strip()
                if cleaned:
                    triggers.append(cleaned)

        # Parse allocation (category level -> distribute to ETFs)
        cat_alloc = _parse_category_allocation(block)
        if cat_alloc:
            alloc = _distribute_to_etfs(cat_alloc, etf_ratios)
        else:
            alloc = dict(current)

        scenarios[name] = ScenarioSpec(
            name=name,
            probability=probability,
            triggers=triggers,
            allocation=alloc,
        )

    return scenarios


_CATEGORY_NAMES = {
    "コア": "core",
    "防御": "defensive",
    "テーマ": "theme",
    "現金": "cash",
}

_CAT_ALLOC_LINE = re.compile(
    r"-\s*(?:\*\*)?(?P<cat>コア|防御|テーマ|現金)[^:：]*(?:\*\*)?:\s*"
    r"(?:[\d]+%\s*→\s*)?(?:\*\*)?\s*(?P<pct>\d+)\s*%"
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
            result[cat_en] = int(m.group("pct"))

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

_TRADING_LEVEL_ROW = re.compile(
    r"\|\s*\*?\*?"
    r"(?P<name>S&P\s*500|Nasdaq\s*100|ダウ|Gold|Oil\s*\(WTI\))"
    r"\*?\*?\s*\|\s*"
    r"(?P<buy>[0-9,.$]+)\s*(?:（[^）]*）)?\s*\|\s*"
    r"(?P<sell>[0-9,.$]+)\s*(?:（[^）]*）)?\s*\|\s*"
    r"(?P<stop>[0-9,.$]+)"
)

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


def _parse_trading_levels(text: str) -> dict[str, TradingLevel]:
    """Parse the 今週の売買レベル table."""
    # Limit search to the trading levels section to avoid matching
    # the マーケット状況 table which has a different column layout.
    section = _extract_section(text, "売買レベル")
    if not section:
        section = text

    levels: dict[str, TradingLevel] = {}
    for m in _TRADING_LEVEL_ROW.finditer(section):
        raw_name = m.group("name").strip().lower()
        key = _INDEX_NAME_MAP.get(raw_name, raw_name)
        levels[key] = TradingLevel(
            buy_level=_parse_number(m.group("buy")),
            sell_level=_parse_number(m.group("sell")),
            stop_loss=_parse_number(m.group("stop")),
        )
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


def _parse_pre_event_dates(text: str) -> list[str]:
    """Extract event dates from the 重要イベント table."""
    event_section = _extract_section(text, "重要イベント")
    if not event_section:
        return []

    dates: list[str] = []
    for m in _EVENT_DATE.finditer(event_section):
        d = m.group(1)
        if d not in dates:
            dates.append(d)

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
