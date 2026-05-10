#!/usr/bin/env python3
"""Postflight blog draft validator.

Validates a weekly strategy blog draft against `facts_snapshot.json`
and `ir_events.yaml`, applying mechanical checks to prevent regression
of the Round 2-4 review findings.

Usage:
    python3 scripts/postflight_blog_check.py blogs/2026-05-11-weekly-strategy.md
    python3 scripts/postflight_blog_check.py blogs/2026-05-11-weekly-strategy.md --strict

Exit codes:
    0 = PASS (all checks)
    1 = FAIL (at least one violation)
    2 = ERROR (prerequisite missing — facts_snapshot.json or ir_events.yaml)

Reference: CLAUDE.md Issues #18 (ETF spot), #19 (option expiry), #20 (IR times), #21 (terminology).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Issue #21: Forbidden terminology (regex patterns)
FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    (r"Fed\s*静寂週", "Issue #12: Fed events must be enumerated, '静寂週' wording is unsafe"),
    (r"Powell\s*退任", "Issue #21: Use 'Powell 議長任期終了' instead (Powell remains as governor)"),
    (r"(?<!Tail Risk )Panic\s*Mode", "Issue #21: Use 'Tail Risk Defensive Mode' instead"),
    (r"(?i)wikipedia", "Issue #21: Wikipedia is not a primary source (use AP/Reuters/WSJ/Bloomberg/FT)"),
    (r"5/8\s*最終更新", "Issue #21: Use '執筆時点で確認' instead of dating Fed page Last Update"),
    (r"6/19\s*満期", "Issue #19: Juneteenth shifts equity/ETF June expiry to 6/18"),
    (r"5/21\s*満期", "Issue #19: VIX May 2026 standard expiry is 5/19 (Juneteenth shift)"),
    (r"GLD\s*≈\s*GC\s*/\s*10", "Issue #18: Use ETF spot price, not GC/10 conversion"),
    (r"推定\s*\d+\s*:\s*\d+\s*ET", "Issue #20: Earnings times must not be estimated"),
    (r"approx\.\s*\d+\s*:\s*\d+\s*ET", "Issue #20: Earnings times must not be 'approx'"),
]

# Issue #18: ETF spot prices that must appear if mentioned
REQUIRED_ETF_SPOT_KEYS = ["SPY", "QQQ", "GLD"]


@dataclass
class Finding:
    severity: str  # high / medium / low
    category: str
    message: str
    line: int | None = None

    def render(self) -> str:
        loc = f":line {self.line}" if self.line is not None else ""
        return f"  [{self.severity.upper()}] [{self.category}]{loc} {self.message}"


def load_snapshot(target_date: str) -> dict:
    path = PROJECT_ROOT / "reports" / target_date / "facts_snapshot.json"
    if not path.exists():
        print(f"ERROR: facts_snapshot.json not found at {path.relative_to(PROJECT_ROOT)}", file=sys.stderr)
        print("  Run: python3 scripts/preflight_blog_facts.py --date " + target_date, file=sys.stderr)
        sys.exit(2)
    return json.loads(path.read_text())


def load_ir_yaml_text(target_date: str) -> str | None:
    path = PROJECT_ROOT / "reports" / target_date / "ir_events.yaml"
    if not path.exists():
        return None
    return path.read_text()


def line_of(text: str, idx: int) -> int:
    return text[:idx].count("\n") + 1


def check_forbidden_terms(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for pat, reason in FORBIDDEN_PATTERNS:
        for m in re.finditer(pat, text):
            findings.append(Finding(
                severity="high" if "Issue #19" in reason or "Issue #18" in reason else "medium",
                category="Forbidden Term",
                message=f"Match '{m.group()}' — {reason}",
                line=line_of(text, m.start()),
            ))
    return findings


def check_etf_spot_prices(text: str, snapshot: dict) -> list[Finding]:
    """Positive check: each REQUIRED ETF symbol that is mentioned in the body
    must have its current spot price (from facts_snapshot.json) appearing
    verbatim at least once. This avoids false positives from allocation
    amounts (`SPY $15K`) or derived support levels (`GLD $405`).
    """
    findings: list[Finding] = []
    prices = snapshot.get("market_prices", {})
    for sym in REQUIRED_ETF_SPOT_KEYS:
        row = prices.get(sym)
        if not row or row.get("price") is None:
            continue
        spot = row["price"]
        # Only require the spot to appear if the symbol is mentioned at all
        if not re.search(rf"\b{sym}\b", text):
            continue
        # Allow ±0.01 rounding by matching the integer part + first decimal
        spot_str_2dec = f"{spot:.2f}"
        spot_str_1dec = f"{spot:.1f}"
        spot_str_int = f"{int(round(spot))}"
        if spot_str_2dec in text or spot_str_1dec in text or f"${spot_str_int}." in text:
            continue
        findings.append(Finding(
            severity="high",
            category="ETF Spot Missing (Issue #18)",
            message=f"{sym} mentioned but its current spot ${spot:.2f} (from facts_snapshot.json) does not appear verbatim in body",
        ))
    return findings


def extract_otm_claims(text: str) -> list[tuple[str, str, float, float, int]]:
    """Find option strike + OTM% claims in the body.

    Returns list of (symbol, type, strike, claimed_otm_pct, line).
    Pattern: '**TICKER プット|コール**: **$NNN** ... 現値 $XXX[.XX] ... [+-]NN.N% OTM'
    """
    out: list[tuple[str, str, float, float, int]] = []
    # Permissive regex: capture TICKER, type (プット|コール), strike, spot, otm
    pattern = re.compile(
        r"\b(SPY|QQQ|GLD|SLV|TLT|XLE|VIX)\b\s*(プット|コール|put|call)\s*[*:]*\s*\$?\s*([0-9]+(?:\.[0-9]+)?)\s*"
        r"ストライク[\s\S]{0,80}?現値\s*\$?\s*([0-9]+(?:\.[0-9]+)?)[\s\S]{0,80}?([+-]?[0-9]+(?:\.[0-9]+)?)%\s*OTM",
        re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        sym = m.group(1).upper()
        opt_type_raw = m.group(2)
        opt_type = "put" if opt_type_raw in ("プット", "put") else "call"
        strike = float(m.group(3))
        spot = float(m.group(4))
        otm_pct = float(m.group(5))
        out.append((sym, opt_type, strike, spot, otm_pct, line_of(text, m.start())))  # type: ignore[arg-type]
    return out


def check_option_otm(text: str, snapshot: dict | None = None) -> list[Finding]:
    """Recompute OTM% from spot/strike and flag mismatches.

    Two layers of validation:
    1. **Internal consistency**: claimed OTM% must match (strike/spot - 1) * 100
       using the spot quoted in the same option block (±0.3%).
    2. **Spot facts cross-check**: the spot quoted in the option block must
       also match facts_snapshot.market_prices[ticker] (±0.3%). This catches
       the case where the body has a stale spot (e.g., QQQ 現値 $687) inside
       the options block while having the correct spot elsewhere.
    """
    findings: list[Finding] = []
    facts_prices = (snapshot or {}).get("market_prices", {})
    pattern = re.compile(
        r"\b(SPY|QQQ|GLD|SLV|TLT|XLE)\b\s*(プット|コール|put|call)\s*[*:]*\s*\$?\s*([0-9]+(?:\.[0-9]+)?)\s*"
        r"ストライク[\s\S]{0,80}?現値\s*\$?\s*([0-9]+(?:\.[0-9]+)?)[\s\S]{0,200}?([+-]?[0-9]+(?:\.[0-9]+)?)%\s*OTM",
        re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        sym = m.group(1).upper()
        opt_type_raw = m.group(2)
        opt_type = "put" if opt_type_raw in ("プット", "put") else "call"
        strike = float(m.group(3))
        spot = float(m.group(4))
        claimed_otm = float(m.group(5))
        actual_otm = (strike / spot - 1) * 100
        line_no = line_of(text, m.start())
        err = abs(claimed_otm - actual_otm)
        if err > 0.3:
            findings.append(Finding(
                severity="high",
                category="OTM% Recalc (Issue #18)",
                message=f"{sym} {opt_type} ${strike:.0f} @ spot ${spot:.2f}: claimed {claimed_otm:+.1f}%, recalc {actual_otm:+.1f}% (err {err:.2f}%)",
                line=line_no,
            ))

        # Cross-check spot in option block against facts_snapshot
        facts_row = facts_prices.get(sym)
        if facts_row and facts_row.get("price") is not None:
            facts_spot = float(facts_row["price"])
            spot_err_pct = abs(spot - facts_spot) / facts_spot * 100
            if spot_err_pct > 0.3:
                findings.append(Finding(
                    severity="high",
                    category="Option Block Spot Mismatch (Issue #18)",
                    message=f"{sym} option block 現値 ${spot:.2f} but facts_snapshot says ${facts_spot:.2f} (err {spot_err_pct:.2f}%) — stale spot inside options block",
                    line=line_no,
                ))
    return findings


EQUITY_ETF_TICKERS = {"SPY", "QQQ", "DIA", "IWM", "GLD", "SLV", "TLT", "XLE", "XLP", "XLV", "XLF", "XLK", "XLY", "XLI", "XLU", "XLRE", "XLB", "XLC", "URA"}
VIX_TICKERS = {"VIX"}


def _md_set_from_iso(values: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for v in values:
        if not v or len(v) < 10:
            continue
        m, d = v[5:7], v[8:10]
        out.add(f"{int(m)}/{int(d)}")
    return out


def check_option_expiries(text: str, snapshot: dict) -> list[Finding]:
    """Verify option expiries with **instrument-aware** calendar separation.

    Equity/ETF tickers (SPY/QQQ/GLD/etc.) must use ETF monthly calendar.
    VIX must use VIX monthly OR VIX weekly Wednesdays.
    A VIX weekly date (e.g., 5/20) on an ETF option line is a violation
    even though it is a valid VIX expiry.

    Round 6 finding 3: VIX weekly Wednesdays *other than* the recommended
    "post-AMAT 5/27 weekly" (one week after the typical AMAT release week)
    are warned at Medium severity, on the principle that default hedges
    should use VIX monthly (5/19, 6/17) or the explicitly-justified
    post-event weekly. The non-recommended weekly windows are typically
    5/20, 6/3, 6/10 (in 2026-05/06).
    """
    findings: list[Finding] = []
    expiries = snapshot.get("option_expiries", {})
    equity_etf_md = _md_set_from_iso(expiries.get("equity_etf_standard", {}).values())
    vix_monthly_md = _md_set_from_iso(expiries.get("vix_standard", {}).values())
    vix_weekly_md = _md_set_from_iso(expiries.get("vix_weekly_wednesdays", []))
    valid_vix_md = vix_monthly_md | vix_weekly_md
    valid_any = equity_etf_md | valid_vix_md

    # Recommended VIX expiries: monthly + the last weekly Wednesday in the
    # target month (post-event weekly hedge). Other weeklies are warned.
    if vix_weekly_md:
        target_month_str = snapshot.get("target_week_start", "")[5:7]
        target_month_int = int(target_month_str) if target_month_str else 0
        target_weeklies = [d for d in vix_weekly_md
                           if d.startswith(f"{target_month_int}/")]

        def _md_to_day(md: str) -> int:
            return int(md.split("/")[1])

        recommended_weekly_md = {max(target_weeklies, key=_md_to_day)} if target_weeklies else set()
    else:
        recommended_weekly_md = set()
    recommended_vix_md = vix_monthly_md | recommended_weekly_md

    # Pattern: capture optional preceding ticker context (within 80 chars before "X/YY 満期")
    pattern = re.compile(r"(\d{1,2})/(\d{1,2})\s*[（(]?(月|火|水|木|金|土|日)?[)）]?\s*満期")
    for m in pattern.finditer(text):
        md = f"{int(m.group(1))}/{int(m.group(2))}"
        # Look backwards 200 chars for an instrument hint; pick the LATEST mention
        context = text[max(0, m.start() - 200):m.start()].upper()
        last_etf_pos = max((context.rfind(t) for t in EQUITY_ETF_TICKERS), default=-1)
        last_vix_pos = context.rfind("VIX")
        is_vix_context = last_vix_pos > last_etf_pos and last_vix_pos != -1
        is_etf_context = last_etf_pos > last_vix_pos and last_etf_pos != -1
        line_no = line_of(text, m.start())

        if md not in valid_any:
            findings.append(Finding(
                severity="high",
                category="Option Expiry (Issue #19)",
                message=f"Found '{m.group()}' but {md} is not in Cboe/VIX calendar valid expiries (ETF: {sorted(equity_etf_md)}, VIX: {sorted(valid_vix_md)})",
                line=line_no,
            ))
            continue
        if is_etf_context and md not in equity_etf_md:
            findings.append(Finding(
                severity="high",
                category="Option Expiry — ETF using VIX date (Issue #19)",
                message=f"ETF option ('{m.group()}') uses {md} which is a VIX expiry, not an ETF expiry. ETF valid: {sorted(equity_etf_md)}",
                line=line_no,
            ))
            continue
        if is_vix_context and md not in valid_vix_md:
            findings.append(Finding(
                severity="high",
                category="Option Expiry — VIX using ETF date (Issue #19)",
                message=f"VIX option ('{m.group()}') uses {md} which is an ETF expiry, not a VIX expiry. VIX valid: {sorted(valid_vix_md)}",
                line=line_no,
            ))
            continue
        # Round 6 finding 3: VIX weekly that is not monthly/recommended → warn
        if is_vix_context and recommended_vix_md and md not in recommended_vix_md:
            findings.append(Finding(
                severity="medium",
                category="Option Expiry — VIX non-recommended weekly (Issue #19)",
                message=f"VIX option uses weekly {md}. Recommended VIX expiries are monthly ({sorted(vix_monthly_md)}) or post-event weekly ({sorted(recommended_weekly_md)}). Other weeklies (e.g., 5/20) should not be the default hedge expiry.",
                line=line_no,
            ))
    return findings


def check_day_of_week(text: str, snapshot: dict) -> list[Finding]:
    findings: list[Finding] = []
    dow = {row["date"]: row["day_jp"] for row in snapshot.get("day_of_week_table", [])}
    target_year = snapshot.get("target_week_start", "")[:4]
    if not target_year:
        return findings

    pattern = re.compile(r"(\d{1,2})/(\d{1,2})\s*[（(](月|火|水|木|金|土|日)[)）]")
    for m in pattern.finditer(text):
        mo, day, dow_jp = int(m.group(1)), int(m.group(2)), m.group(3)
        iso = f"{target_year}-{mo:02d}-{day:02d}"
        actual = dow.get(iso)
        if actual and actual != dow_jp:
            findings.append(Finding(
                severity="medium",
                category="Day-of-Week (Issue #6)",
                message=f"Body says {mo}/{day}({dow_jp}) but {iso} is actually ({actual})",
                line=line_of(text, m.start()),
            ))
    return findings


def _parse_ir_yaml(ir_yaml: str) -> dict[str, list[dict]]:
    """Lightweight regex-based parser: ticker -> [items].

    Each item: {type, date_et, time_et (or None), time_jst (or None), time_note (or None)}.
    Avoids YAML dependency.
    """
    result: dict[str, list[dict]] = {}
    ticker_blocks = re.split(r"^\s*-\s+ticker:\s*", ir_yaml, flags=re.MULTILINE)
    for blk in ticker_blocks[1:]:
        tm = re.match(r"(\w+)", blk)
        if not tm:
            continue
        ticker = tm.group(1).upper()
        # Cut off at next "- ticker:" boundary if any
        items: list[dict] = []
        # Find each "- type: <kind>" block until the next "- type" or end
        item_starts = [m.start() for m in re.finditer(r"^\s+-\s+type:\s*", blk, flags=re.MULTILINE)]
        item_starts.append(len(blk))
        for i in range(len(item_starts) - 1):
            seg = blk[item_starts[i]:item_starts[i + 1]]
            type_m = re.search(r"type:\s*(\S+)", seg)
            if not type_m:
                continue
            type_val = type_m.group(1).strip().strip('"').strip("'")
            if type_val not in {"release", "call", "webcast"}:
                continue
            date_m = re.search(r'date_et:\s*"?(\d{4}-\d{2}-\d{2})"?', seg)
            time_et_m = re.search(r'time_et:\s*"?([0-9]{2}:[0-9]{2})"?', seg)
            time_et_null = re.search(r'time_et:\s*null', seg)
            time_jst_m = re.search(r'time_jst:\s*"?([0-9]{2}:[0-9]{2})"?', seg)
            time_note_m = re.search(r'time_note:\s*"([^"]+)"', seg)

            items.append({
                "type": type_val,
                "date_et": date_m.group(1) if date_m else None,
                "time_et": time_et_m.group(1) if time_et_m else (None if time_et_null else None),
                "time_et_null": bool(time_et_null),
                "time_jst": time_jst_m.group(1) if time_jst_m else None,
                "time_note": time_note_m.group(1) if time_note_m else None,
            })
        if items:
            result[ticker] = items
    return result


def _normalize_hhmm(s: str) -> str:
    h, mi = s.split(":")
    return f"{int(h):02d}:{mi}"


def check_ir_times_against_yaml(text: str, ir_yaml: str | None) -> list[Finding]:
    """For each ticker × item (release/call/webcast) in ir_events.yaml,
    verify body's nearby ET / JST values match expected values.

    Detects:
    - body has explicit ET time when yaml says time_et: null (Issue #20)
    - body's ET time differs from yaml time_et (Issue #20)
    - body's JST time differs from yaml time_jst (Issue #20 + JST validation)
    """
    if ir_yaml is None:
        return [Finding(
            severity="medium",
            category="IR Manifest (Issue #20)",
            message="ir_events.yaml not found — earnings times cannot be cross-checked",
        )]

    findings: list[Finding] = []
    parsed = _parse_ir_yaml(ir_yaml)

    TYPE_LABELS = {
        "release": r"(?:release|決算\s*release|リリース)",
        "call": r"(?:\bcall\b|conference|決算\s*call|カンファレンス)",
        "webcast": r"(?:webcast|ウェブキャスト)",
    }
    type_re = {k: re.compile(v, re.IGNORECASE) for k, v in TYPE_LABELS.items()}

    # Split the document into "cells" by line, then by | and " / " separators.
    # `/` is only a separator when surrounded by spaces (to avoid splitting dates like 5/11).
    # Within each cell, at most one type label is expected; this disambiguates time→label.
    def _enumerate_cells(text: str) -> list[tuple[int, str]]:
        out: list[tuple[int, str]] = []
        for ln_idx, ln in enumerate(text.split("\n")):
            for cell in re.split(r"\||(?:\s+/\s+)", ln):
                if cell is None:
                    continue
                out.append((ln_idx + 1, cell))
        return out

    cells = _enumerate_cells(text)

    for ticker, items in parsed.items():
        ticker_re = re.compile(rf"\b{ticker}\b")
        # Pre-compute per-cell hits: cell_idx -> set of types found in cell, and
        # ticker presence for ticker scoping.
        for item in items:
            type_val = item["type"]
            t_re = type_re[type_val]

            for line_no, cell in cells:
                # Type label must appear in this cell
                if not t_re.search(cell):
                    continue
                # Ticker context: ticker must appear in same cell OR within ±2 cells
                # (event tables put ticker in a separate cell from time).
                ticker_idx_range = []  # gather indices of cells with ticker on same line
                # Simple check: ticker appears in same line
                # Reconstruct line content from cells with same line_no
                line_cells = [c for ln, c in cells if ln == line_no]
                if not any(ticker_re.search(c) for c in line_cells):
                    continue

                # Time tied to the type label inside the same cell (no other
                # type label may appear in this cell — handled by cell isolation).
                body_et_m = re.search(r"(\d{1,2}:\d{2})\s*ET", cell)
                body_jst_m = re.search(r"(\d{1,2}:\d{2})\s*JST", cell)
                # Sanity: verify no OTHER type label is in the same cell
                other_label_present = any(
                    other_t != type_val and type_re[other_t].search(cell)
                    for other_t in TYPE_LABELS
                )
                if other_label_present:
                    continue  # ambiguous cell — skip

                if not body_et_m and not body_jst_m:
                    continue

                # Issue #20: yaml says time_et: null → body must not have a tied ET time
                if item["time_et_null"] and body_et_m:
                    findings.append(Finding(
                        severity="medium",
                        category=f"IR {type_val.title()} time written when official未明示 (Issue #20)",
                        message=f"{ticker} {type_val} body has '{body_et_m.group(1)} ET' but ir_events.yaml time_et is null (official未明示). Use '時刻未明示' instead.",
                        line=line_no,
                    ))

                # ET mismatch
                if item["time_et"] and body_et_m:
                    if _normalize_hhmm(body_et_m.group(1)) != _normalize_hhmm(item["time_et"]):
                        findings.append(Finding(
                            severity="medium",
                            category=f"IR {type_val.title()} ET Mismatch (Issue #20)",
                            message=f"{ticker} {type_val} body says {body_et_m.group(1)} ET but ir_events.yaml says {item['time_et']} ET",
                            line=line_no,
                        ))

                # JST mismatch
                if item["time_jst"] and body_jst_m:
                    if _normalize_hhmm(body_jst_m.group(1)) != _normalize_hhmm(item["time_jst"]):
                        findings.append(Finding(
                            severity="medium",
                            category=f"IR {type_val.title()} JST Mismatch (Issue #20)",
                            message=f"{ticker} {type_val} body says {body_jst_m.group(1)} JST but ir_events.yaml time_jst says {item['time_jst']} JST",
                            line=line_no,
                        ))
    return findings


NON_TICKERS = {
    # Time/date abbreviations
    "ATH", "AMC", "BMO", "ET", "JST", "BRT", "EDT", "EST", "PT", "PST", "PDT", "UTC", "CT", "MT", "GMT", "DST", "AH", "PM", "AM",
    # Macro indicators
    "CPI", "PPI", "PCE", "ISM", "PMI", "GDP", "GDPNow", "NFP", "ADP", "JOLTS",
    # Central banks
    "FED", "FOMC", "BLS", "BEA", "OECD", "ECB", "BOJ", "BOE", "RBA", "RBNZ", "PBOC", "SNB",
    # Tech/file abbreviations
    "API", "CSV", "PDF", "URL", "JSON", "YAML", "HTML", "XML", "HTTP", "HTTPS",
    # Trading/option terms
    "ETF", "OTM", "ITM", "ATM", "MA", "EMA", "SMA", "WMA", "RSI", "MACD", "ATR",
    # Indices
    "VIX", "SPX", "NDX", "DJI", "RUT", "DXY", "EFA", "EEM",
    # Currencies / metals abbr
    "USD", "EUR", "JPY", "GBP", "CHF", "CNY", "AUD", "CAD", "BRL", "INR", "BPS", "BP",
    # Misc text
    "AI", "ML", "QT", "QE", "JR", "SR", "TBA", "TBD", "AMA", "FAQ", "IPO", "DCF", "EPS", "GAAP", "FCF", "EBITDA",
    "OPEC", "OPEX", "CAPEX", "CAGR", "ROI", "ROE", "ROA",
    "WTI", "GC", "CL", "NG", "HG",  # commodity codes
    # Geographic
    "NY", "LA", "SF", "DC", "UK", "EU", "US", "USA", "JP", "CN", "DE", "FR", "JFK", "SFO",
    # IR is investor relations (link text)
    "IR",
    # Common English words that look like tickers
    "CLOSE", "OPEN", "HIGH", "LOW", "SELL", "BUY", "HOLD", "BEAR", "BULL",
    "BASE", "PEAK", "PRE", "POST", "NEW", "OLD", "VS", "ROW", "NEXT", "LAST",
    "CALL", "PUT", "LONG", "SHORT", "NEAR", "FAR", "OUR", "OUT", "OFF", "OFF",
    "TOP", "END", "MID", "ALL", "ANY", "ONE", "TWO", "THE", "AND", "FOR", "BUT",
    "GAP", "GAPS", "BAR", "BARS",
}

# Patterns where a ticker is clearly tied to an earnings event:
# - "TICKER call/release/webcast"
# - "TICKER Q1/Q2/Q3/Q4 (FY26)? (決算)? call/release/webcast"
# - "TICKER 決算"
# - "earnings: TICKER" / "決算: TICKER"
# We require ADJACENCY (≤ 30 chars and no other ticker between) to avoid
# false positives like "TLT or VIX call" / "[IR](url)".
TICKER_EARNINGS_PATTERNS = [
    # Forward: TICKER (...modifiers...) earnings_word
    re.compile(
        r"\b([A-Z]{2,5})\b\s*"
        r"(?:Q[1-4]\s*)?(?:FY\d{2,4}\s*)?(?:決算\s*)?"
        r"(?:call|webcast|release|earnings|conference|カンファレンス|ウェブキャスト|リリース|決算)\b",
        re.IGNORECASE,
    ),
    # Forward Japanese: TICKER 決算
    re.compile(r"\b([A-Z]{2,5})\b\s*決算"),
    # Reverse: earnings_word ... TICKER (e.g., "決算: BABA")
    re.compile(
        r"(?:earnings|決算)\s*[:：]\s*\b([A-Z]{2,5})\b",
        re.IGNORECASE,
    ),
]


def check_ir_manifest_completeness(text: str, ir_yaml: str | None) -> list[Finding]:
    """Round 6 finding 1: if body mentions a ticker with earnings vocabulary
    (call/release/webcast/決算) but the ticker is missing from ir_events.yaml,
    flag as High severity.

    We require adjacency between ticker and earnings vocab to avoid false
    positives from sentences like "TLT or VIX call" (TLT is an ETF, "call"
    refers to option contract not earnings call).
    """
    findings: list[Finding] = []
    parsed = _parse_ir_yaml(ir_yaml) if ir_yaml else {}
    manifest_tickers = set(parsed.keys())
    seen: set[tuple[str, int]] = set()

    for pat in TICKER_EARNINGS_PATTERNS:
        for m in pat.finditer(text):
            ticker = m.group(1)
            if ticker is None:
                continue
            ticker = ticker.upper()
            if ticker in NON_TICKERS:
                continue
            if ticker in manifest_tickers:
                continue
            line_no = line_of(text, m.start())
            key = (ticker, line_no)
            if key in seen:
                continue
            seen.add(key)
            findings.append(Finding(
                severity="high",
                category="IR Manifest Missing Ticker (Issue #20)",
                message=f"Body mentions '{ticker}' adjacent to earnings vocabulary but {ticker} is not in ir_events.yaml manifest. Add to manifest or remove the earnings reference from body.",
                line=line_no,
            ))
    return findings


def collect(text: str, snapshot: dict, ir_yaml: str | None) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_forbidden_terms(text))
    findings.extend(check_etf_spot_prices(text, snapshot))
    findings.extend(check_option_otm(text, snapshot))
    findings.extend(check_option_expiries(text, snapshot))
    findings.extend(check_day_of_week(text, snapshot))
    findings.extend(check_ir_times_against_yaml(text, ir_yaml))
    findings.extend(check_ir_manifest_completeness(text, ir_yaml))
    return findings


def main() -> int:
    p = argparse.ArgumentParser(description="Postflight blog draft validator")
    p.add_argument("blog_path", help="Path to blogs/YYYY-MM-DD-weekly-strategy.md")
    p.add_argument("--strict", action="store_true", help="Fail on medium severity too (default: high only)")
    args = p.parse_args()

    blog = Path(args.blog_path)
    if not blog.exists():
        print(f"ERROR: {blog} not found", file=sys.stderr)
        return 2

    # Extract date from filename: YYYY-MM-DD-weekly-strategy.md
    m = re.match(r"(\d{4}-\d{2}-\d{2})-weekly-strategy\.md", blog.name)
    if not m:
        print(f"ERROR: cannot parse date from filename {blog.name}", file=sys.stderr)
        return 2
    target_date = m.group(1)

    snapshot = load_snapshot(target_date)
    ir_yaml = load_ir_yaml_text(target_date)
    text = blog.read_text()

    findings = collect(text, snapshot, ir_yaml)
    high = [f for f in findings if f.severity == "high"]
    medium = [f for f in findings if f.severity == "medium"]
    low = [f for f in findings if f.severity == "low"]

    print(f"# Postflight Check — {blog.name}")
    print(f"target_date: {target_date}")
    print(f"high: {len(high)}, medium: {len(medium)}, low: {len(low)}")
    print()

    if high:
        print("## HIGH severity (must fix)")
        for f in high:
            print(f.render())
        print()
    if medium:
        print("## MEDIUM severity")
        for f in medium:
            print(f.render())
        print()
    if low:
        print("## LOW severity")
        for f in low:
            print(f.render())
        print()

    fail_threshold_severities = {"high"}
    if args.strict:
        fail_threshold_severities.add("medium")
    failed = any(f.severity in fail_threshold_severities for f in findings)

    if failed:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
