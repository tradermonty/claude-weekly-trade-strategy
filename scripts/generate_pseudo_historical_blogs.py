#!/usr/bin/env python3
"""Generate pseudo weekly strategy blogs from historical market states.

Design references in this repository:
- .claude/agents/weekly-trade-blog-writer.md
- .claude/agents/strategy-reviewer.md
- .claude/skills/us-market-bubble-detector/SKILL.md

The generator uses only data available up to each strategy date (no look-ahead),
then writes parser-compatible markdown files:
    YYYY-MM-DD-weekly-strategy.md
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from statistics import stdev
from copy import deepcopy

from trading.backtest.data_provider import DataProvider
from trading.config import AlpacaConfig, FMPConfig


ETF_SYMBOLS = ["SPY", "QQQ", "DIA", "XLV", "XLP", "GLD", "XLE", "BIL", "TLT"]
BREADTH_SYMBOLS = ["SPY", "QQQ", "DIA", "XLV", "XLP", "XLE", "GLD", "TLT"]

BASE_ALLOCATIONS: dict[str, dict[str, float]] = {
    "bull": {"SPY": 30, "QQQ": 20, "DIA": 7, "XLV": 9, "XLP": 5, "GLD": 8, "XLE": 11, "BIL": 10},
    "base": {"SPY": 28, "QQQ": 14, "DIA": 8, "XLV": 11, "XLP": 9, "GLD": 10, "XLE": 8, "BIL": 12},
    "bear": {"SPY": 21, "QQQ": 8, "DIA": 9, "XLV": 14, "XLP": 13, "GLD": 12, "XLE": 7, "BIL": 16},
    "tail_risk": {"SPY": 14, "QQQ": 4, "DIA": 8, "XLV": 16, "XLP": 16, "GLD": 14, "XLE": 6, "BIL": 22},
}

SCENARIO_PROBS: dict[str, dict[str, int]] = {
    "bull": {"base": 40, "bull": 35, "bear": 20, "tail_risk": 5},
    "base": {"base": 55, "bull": 20, "bear": 20, "tail_risk": 5},
    "bear": {"base": 35, "bull": 15, "bear": 35, "tail_risk": 15},
    "tail_risk": {"base": 20, "bull": 10, "bear": 30, "tail_risk": 40},
}

REGIME_LABEL = {
    "bull": "Risk-On",
    "base": "Base",
    "bear": "Caution",
    "tail_risk": "Stress",
}

JP_WEEKDAY = "月火水木金土日"


@dataclass
class WeekState:
    blog_date: date
    obs_date: date
    regime: str
    risk_score: int
    vix: float
    sp500: float
    nasdaq: float
    dow: float
    spy_r5: float
    spy_r20: float
    spy_r60: float
    qqq_r20: float
    xle_r20: float
    gld_r20: float
    vol20: float
    drawdown63: float
    breadth_200ma: float
    uptrend_ratio: float
    bubble_score: int
    allocation: dict[str, float]


@dataclass
class GenerationParams:
    """Parameter set for pseudo blog generation logic."""

    name: str = "default"
    regime_allocations: dict[str, dict[str, float]] = field(
        default_factory=lambda: deepcopy(BASE_ALLOCATIONS)
    )
    score_cut_bull: int = -2
    score_cut_bear: int = 4
    score_cut_tail: int = 7
    tech_rel_threshold: float = 0.03
    tech_tilt: float = 2.0
    energy_rel_threshold: float = 0.02
    energy_tilt: float = 2.0
    gold_strength_threshold: float = 0.04
    gold_tilt: float = 2.0
    bear_cash_boost: float = 2.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate pseudo historical weekly strategy blogs")
    p.add_argument("--start", type=date.fromisoformat, required=True, help="Start date (YYYY-MM-DD)")
    p.add_argument("--end", type=date.fromisoformat, required=True, help="End date (YYYY-MM-DD)")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/pseudo_blogs_generated"),
        help="Directory to write generated markdown blogs",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in output directory",
    )
    p.add_argument(
        "--warmup-days",
        type=int,
        default=120,
        help="Warm-up trading days needed before first generated blog (default: 120)",
    )
    return p.parse_args()


def first_monday_on_or_after(d: date) -> date:
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


def fmt_idx(x: float) -> str:
    return f"{int(round(x)):,}"


def fmt_pct(x: float) -> str:
    return f"{x:.1f}%"


def norm_alloc(alloc: dict[str, float]) -> dict[str, float]:
    clamped = {k: max(v, 0.0) for k, v in alloc.items()}
    total = sum(clamped.values())
    if total <= 0:
        clamped = dict(BASE_ALLOCATIONS["base"])
        total = sum(clamped.values())
    scaled = {k: round(v * 100.0 / total, 1) for k, v in clamped.items()}
    diff = round(100.0 - sum(scaled.values()), 1)
    scaled["BIL"] = round(scaled.get("BIL", 0.0) + diff, 1)
    if scaled["BIL"] < 0:
        deficit = abs(scaled["BIL"])
        scaled["BIL"] = 0.0
        for sym in ("SPY", "QQQ", "DIA", "XLV", "XLP", "GLD", "XLE", "TLT"):
            if deficit <= 0:
                break
            take = min(deficit, scaled.get(sym, 0.0))
            scaled[sym] = round(scaled.get(sym, 0.0) - take, 1)
            deficit = round(deficit - take, 1)
    return scaled


def category_alloc(alloc: dict[str, float]) -> dict[str, int]:
    vals = {
        "core": alloc.get("SPY", 0) + alloc.get("QQQ", 0) + alloc.get("DIA", 0),
        "defensive": alloc.get("XLV", 0) + alloc.get("XLP", 0),
        "theme": alloc.get("GLD", 0) + alloc.get("XLE", 0),
        "cash": alloc.get("BIL", 0),
    }
    rounded = {k: int(round(v)) for k, v in vals.items()}
    rounded["cash"] += 100 - sum(rounded.values())
    if rounded["cash"] < 0:
        need = -rounded["cash"]
        rounded["cash"] = 0
        for key in ("core", "defensive", "theme"):
            if need <= 0:
                break
            take = min(need, rounded[key])
            rounded[key] -= take
            need -= take
    return rounded


def shift_categories(base: dict[str, int], d_core: int, d_def: int, d_theme: int, d_cash: int) -> dict[str, int]:
    raw = {
        "core": base["core"] + d_core,
        "defensive": base["defensive"] + d_def,
        "theme": base["theme"] + d_theme,
        "cash": base["cash"] + d_cash,
    }
    raw = {k: max(v, 0) for k, v in raw.items()}
    total = sum(raw.values())
    if total == 0:
        return dict(base)
    # Normalize to 100, preserving cash adjustment for parser-friendly integers.
    normalized = {k: int(round(v * 100 / total)) for k, v in raw.items()}
    normalized["cash"] += 100 - sum(normalized.values())
    if normalized["cash"] < 0:
        need = -normalized["cash"]
        normalized["cash"] = 0
        for key in ("core", "defensive", "theme"):
            if need <= 0:
                break
            take = min(need, normalized[key])
            normalized[key] -= take
            need -= take
    return normalized


def last_trading_day_on_or_before(d: date, trading_days: list[date]) -> date | None:
    for day in reversed(trading_days):
        if day <= d:
            return day
    return None


def price_return(series: list[float], idx: int, lookback: int) -> float:
    if idx <= 0:
        return 0.0
    start_idx = max(0, idx - lookback)
    p0 = series[start_idx]
    p1 = series[idx]
    if p0 <= 0:
        return 0.0
    return (p1 / p0) - 1.0


def rolling_vol(series: list[float], idx: int, lookback: int = 20) -> float:
    start = max(1, idx - lookback + 1)
    rets: list[float] = []
    for i in range(start, idx + 1):
        if series[i - 1] <= 0:
            continue
        rets.append((series[i] / series[i - 1]) - 1.0)
    if len(rets) < 2:
        return 0.20
    return stdev(rets) * math.sqrt(252.0)


def sma(series: list[float], idx: int, window: int) -> float:
    start = max(0, idx - window + 1)
    vals = series[start: idx + 1]
    if not vals:
        return series[idx]
    return sum(vals) / len(vals)


def classify_regime(
    vix: float,
    r20: float,
    r60: float,
    drawdown63: float,
    vol20: float,
    params: GenerationParams,
) -> tuple[str, int]:
    score = 0
    if vix >= 30:
        score += 3
    elif vix >= 24:
        score += 2
    elif vix >= 19:
        score += 1
    elif vix <= 14:
        score -= 1

    if r20 <= -0.06:
        score += 3
    elif r20 <= -0.02:
        score += 2
    elif r20 < 0:
        score += 1
    elif r20 >= 0.05:
        score -= 1

    if r60 <= -0.08:
        score += 2
    elif r60 <= 0:
        score += 1
    elif r60 >= 0.12:
        score -= 1

    if drawdown63 <= -0.12:
        score += 2
    elif drawdown63 <= -0.06:
        score += 1

    if vol20 >= 0.30:
        score += 1
    elif vol20 <= 0.12:
        score -= 1

    if score >= params.score_cut_tail:
        return "tail_risk", score
    if score >= params.score_cut_bear:
        return "bear", score
    if score <= params.score_cut_bull:
        return "bull", score
    return "base", score


def build_allocation(
    regime: str,
    spy_r20: float,
    qqq_r20: float,
    xle_r20: float,
    gld_r20: float,
    vix: float,
    params: GenerationParams,
) -> dict[str, float]:
    alloc = dict(params.regime_allocations[regime])

    # Relative momentum tilts.
    tech_rel = qqq_r20 - spy_r20
    if tech_rel > params.tech_rel_threshold:
        alloc["QQQ"] += params.tech_tilt
        alloc["SPY"] -= params.tech_tilt * 0.5
        alloc["DIA"] -= params.tech_tilt * 0.5
    elif tech_rel < -params.tech_rel_threshold:
        alloc["QQQ"] -= params.tech_tilt
        alloc["SPY"] += params.tech_tilt * 0.5
        alloc["DIA"] += params.tech_tilt * 0.5

    if xle_r20 > spy_r20 + params.energy_rel_threshold:
        alloc["XLE"] += params.energy_tilt
        alloc["SPY"] -= params.energy_tilt

    if gld_r20 > params.gold_strength_threshold and vix > 20:
        alloc["GLD"] += params.gold_tilt
        alloc["SPY"] -= params.gold_tilt * 0.5
        alloc["QQQ"] -= params.gold_tilt * 0.5

    if regime in {"bear", "tail_risk"}:
        alloc["BIL"] += params.bear_cash_boost
        alloc["SPY"] -= params.bear_cash_boost * 0.5
        alloc["QQQ"] -= params.bear_cash_boost * 0.5

    return norm_alloc(alloc)


def bubble_score(r60: float, vix: float, breadth: float) -> int:
    raw = 6.0 + (max(r60, -0.20) * 30.0) - (max(vix - 18.0, 0.0) * 0.30) + (max(breadth - 55.0, 0.0) * 0.10)
    return max(0, min(15, int(round(raw))))


def ja_date_with_weekday(d: date) -> str:
    return f"{d.month}/{d.day}({JP_WEEKDAY[d.weekday()]})"


def infer_cache_start(cache_dir: Path) -> date | None:
    candidates = [cache_dir / "etf_SPY.json", cache_dir / "fmp_vix.json"]
    starts: list[date] = []
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict) or not payload:
            continue
        try:
            first = min(date.fromisoformat(k) for k in payload.keys())
        except Exception:
            continue
        starts.append(first)
    if not starts:
        return None
    # Use the latest among required series so all required inputs exist.
    return max(starts)


def render_blog(state: WeekState) -> str:
    alloc = state.allocation
    core = alloc["SPY"] + alloc["QQQ"] + alloc["DIA"]
    defensive = alloc["XLV"] + alloc["XLP"]
    theme = alloc["GLD"] + alloc["XLE"]
    cash = alloc["BIL"]
    probs = SCENARIO_PROBS[state.regime]
    cat_base = category_alloc(alloc)
    cat_bull = shift_categories(cat_base, d_core=4, d_def=-2, d_theme=1, d_cash=-3)
    cat_bear = shift_categories(cat_base, d_core=-6, d_def=2, d_theme=-1, d_cash=5)
    cat_tail = shift_categories(cat_base, d_core=-11, d_def=4, d_theme=-2, d_cash=9)

    sp_buy = state.sp500 * 0.99
    sp_sell = state.sp500 * 1.03
    sp_stop = state.sp500 * 0.96
    nq_buy = state.nasdaq * 0.99
    nq_sell = state.nasdaq * 1.03
    nq_stop = state.nasdaq * 0.96
    dj_buy = state.dow * 0.99
    dj_sell = state.dow * 1.03
    dj_stop = state.dow * 0.96
    gold_proxy = 1800 + (state.allocation["GLD"] * 5)
    oil_proxy = 60 + (state.allocation["XLE"] - 8) * 2

    vix_floor = max(12, int(math.floor(state.vix - 2)))
    vix_cap = int(math.ceil(state.vix + 2))

    e1 = state.blog_date
    e2 = state.blog_date + timedelta(days=2)
    e3 = state.blog_date + timedelta(days=4)

    return f"""# 【米国株】{state.blog_date.year}年{state.blog_date.month}月{state.blog_date.day}日週 擬似トレード戦略

**発行日**: {state.blog_date.isoformat()}
**生成方式**: historical-reverse (no look-ahead)
**観測終点**: {state.obs_date.isoformat()} の終値データまで
**準拠テンプレート**: weekly-trade-blog-writer / strategy-reviewer

---

## 3行まとめ

1. **市場環境**: {REGIME_LABEL[state.regime]}。VIX **{state.vix:.2f}**、S&P500 1カ月騰落 **{state.spy_r20 * 100:+.1f}%**。
2. **今週の焦点**: 直近レジームに合わせて、株式と現金のバランスを機械的に調整。
3. **推奨戦略**: リスク資産 **{core + defensive + theme:.1f}%**、現金・短期債 **{cash:.1f}%**。

---

## 今週のアクション

### ロット管理

**現在フェーズ**: **{REGIME_LABEL[state.regime]}**
**推奨リスク配分**: 株式・コモディティ合計 **{core + defensive + theme:.1f}%**、現金・短期債 **{cash:.1f}%**

### 今週の売買レベル

| 指数 | 買いレベル | 売りレベル | ストップロス |
|------|-----------|-----------|-------------|
| **S&P 500** | {fmt_idx(sp_buy)} | {fmt_idx(sp_sell)} | {fmt_idx(sp_stop)} |
| **Nasdaq 100** | {fmt_idx(nq_buy)} | {fmt_idx(nq_sell)} | {fmt_idx(nq_stop)} |
| **ダウ** | {fmt_idx(dj_buy)} | {fmt_idx(dj_sell)} | {fmt_idx(dj_stop)} |
| **Gold** | ${int(round(gold_proxy * 0.98)):,} | ${int(round(gold_proxy * 1.03)):,} | ${int(round(gold_proxy * 0.94)):,} |
| **Oil (WTI)** | ${oil_proxy * 0.95:.1f} | ${oil_proxy * 1.05:.1f} | ${oil_proxy * 0.88:.1f} |

---

### セクター配分（4本柱）

| カテゴリ | 配分 | 具体的ETF/銘柄 |
|---------|------|---------------|
| **コア指数** | {fmt_pct(core)} | SPY {fmt_pct(alloc["SPY"])}、QQQ {fmt_pct(alloc["QQQ"])}、DIA {fmt_pct(alloc["DIA"])} |
| **防御セクター** | {fmt_pct(defensive)} | XLV {fmt_pct(alloc["XLV"])}、XLP {fmt_pct(alloc["XLP"])} |
| **テーマ/ヘッジ** | {fmt_pct(theme)} | GLD {fmt_pct(alloc["GLD"])}、XLE {fmt_pct(alloc["XLE"])} |
| **現金・短期債** | {fmt_pct(cash)} | BIL {fmt_pct(alloc["BIL"])} |

**合計: {sum(alloc.values()):.1f}%**

---

### 重要イベント

| 日付 | イベント | Impact | 監視ポイント |
|------|----------|--------|-------------|
| **{ja_date_with_weekday(e1)}** | 週初ポジション確認 | Medium | 前週の終値ベースでレジーム再判定 |
| **{ja_date_with_weekday(e2)}** | 中間チェック | Medium | VIXの変化と主要指数のレンジ維持 |
| **{ja_date_with_weekday(e3)}** | 週末リバランス判定 | High | 翌週への持ち越し配分を固定 |

---

## シナリオ別プラン

### Base Case: レンジ継続 ({probs["base"]}%)

**トリガー**: VIX {vix_floor}-{vix_cap}、主要指数が売買レベル内で推移

**アクション（合計100%）**:
- コア: {cat_base["core"]}%
- 防御: {cat_base["defensive"]}%
- テーマ: {cat_base["theme"]}%
- 現金: {cat_base["cash"]}%

---

### Bull Case: リスク選好回復 ({probs["bull"]}%)

**トリガー**: VIX 17以下 + 1カ月モメンタム改善

**アクション（合計100%）**:
- コア: {cat_base["core"]}% → **{cat_bull["core"]}%**
- 防御: {cat_base["defensive"]}% → **{cat_bull["defensive"]}%**
- テーマ: {cat_base["theme"]}% → **{cat_bull["theme"]}%**
- 現金: {cat_base["cash"]}% → **{cat_bull["cash"]}%**

---

### Bear Case: ボラ上昇と調整 ({probs["bear"]}%)

**トリガー**: VIX 23超 or S&P 500 {fmt_idx(sp_buy)}割れ

**アクション（合計100%）**:
- コア: {cat_base["core"]}% → **{cat_bear["core"]}%**
- 防御: {cat_base["defensive"]}% → **{cat_bear["defensive"]}%**
- テーマ: {cat_base["theme"]}% → **{cat_bear["theme"]}%**
- 現金: {cat_base["cash"]}% → **{cat_bear["cash"]}%**

---

### Tail Risk: 急変動シナリオ ({probs["tail_risk"]}%)

**トリガー**: VIX 30超 or S&P 500 {fmt_idx(sp_stop)}割れ

**アクション（合計100%）**:
- コア: {cat_base["core"]}% → **{cat_tail["core"]}%**
- 防御: {cat_base["defensive"]}% → **{cat_tail["defensive"]}%**
- テーマ: {cat_base["theme"]}% → **{cat_tail["theme"]}%**
- 現金: {cat_base["cash"]}% → **{cat_tail["cash"]}%**

---

## マーケット状況

| 指標 | 現在値 | トリガー | 評価 |
|------|--------|----------|------|
| **VIX** | **{state.vix:.2f}** | **17**(Risk-On) / **20**(Caution) / **23**(Stress) | **{REGIME_LABEL[state.regime]}** |
| **10Y利回り** | **4.10%** | 4.00%(下限) / 4.35%(警戒) / 4.60%(赤) | 中立 |
| **Breadth(200MA)** | **{state.breadth_200ma:.1f}%** | 60%+(健全) / 50%(境界) / 40%-(脆弱) | 監視 |
| **Uptrend Ratio** | **{state.uptrend_ratio:.1f}** | 40%+(強気) / 25%(中立) / 15%-(危機) | 先行指標 |
| **S&P 500** | {fmt_idx(state.sp500)} | {fmt_idx(sp_sell)} / {fmt_idx(sp_buy)} | レンジ |
| **Nasdaq 100** | {fmt_idx(state.nasdaq)} | {fmt_idx(nq_sell)} / {fmt_idx(nq_buy)} | レンジ |
| **ダウ** | {fmt_idx(state.dow)} | {fmt_idx(dj_sell)} / {fmt_idx(dj_buy)} | レンジ |

バブルスコア {state.bubble_score}/15 点

---

## リスク管理

- レジーム判定スコア: **{state.risk_score}**
- 20日実現ボラティリティ: **{state.vol20 * 100:.1f}%**
- 63日高値からの下落率: **{state.drawdown63 * 100:.1f}%**
- ストップロスは指数レベル基準で機械執行

---

> 注: 本記事はバックテスト用に、当時点で観測可能な市場データから擬似生成したものです。
"""


def build_week_state(
    blog_date: date,
    obs_date: date,
    day_index: dict[date, int],
    prices: dict[str, list[float]],
    market: dict[date, tuple[float, float, float, float]],
    params: GenerationParams,
) -> WeekState:
    idx = day_index[obs_date]
    spy = prices["SPY"]
    qqq = prices["QQQ"]
    xle = prices["XLE"]
    gld = prices["GLD"]

    spy_r5 = price_return(spy, idx, 5)
    spy_r20 = price_return(spy, idx, 20)
    spy_r60 = price_return(spy, idx, 60)
    qqq_r20 = price_return(qqq, idx, 20)
    xle_r20 = price_return(xle, idx, 20)
    gld_r20 = price_return(gld, idx, 20)

    vol20 = rolling_vol(spy, idx, 20)
    start_63 = max(0, idx - 63)
    high_63 = max(spy[start_63: idx + 1])
    drawdown63 = (spy[idx] / high_63) - 1.0 if high_63 > 0 else 0.0

    vix, sp500, nasdaq, dow = market[obs_date]
    regime, risk_score = classify_regime(
        vix, spy_r20, spy_r60, drawdown63, vol20, params
    )
    alloc = build_allocation(
        regime, spy_r20, qqq_r20, xle_r20, gld_r20, vix, params
    )

    breadth_count = 0
    uptrend_count = 0
    for sym in BREADTH_SYMBOLS:
        series = prices[sym]
        px = series[idx]
        sma50 = sma(series, idx, 50)
        sma20 = sma(series, idx, 20)
        if px > sma50:
            breadth_count += 1
        if sma20 > sma50:
            uptrend_count += 1

    breadth = (breadth_count / len(BREADTH_SYMBOLS)) * 100.0
    uptrend = (uptrend_count / len(BREADTH_SYMBOLS)) * 100.0
    bubble = bubble_score(spy_r60, vix, breadth)

    return WeekState(
        blog_date=blog_date,
        obs_date=obs_date,
        regime=regime,
        risk_score=risk_score,
        vix=vix,
        sp500=sp500,
        nasdaq=nasdaq,
        dow=dow,
        spy_r5=spy_r5,
        spy_r20=spy_r20,
        spy_r60=spy_r60,
        qqq_r20=qqq_r20,
        xle_r20=xle_r20,
        gld_r20=gld_r20,
        vol20=vol20,
        drawdown63=drawdown63,
        breadth_200ma=breadth,
        uptrend_ratio=uptrend,
        bubble_score=bubble,
        allocation=alloc,
    )


def generate_pseudo_blogs(
    start: date,
    end: date,
    output_dir: Path,
    *,
    overwrite: bool = False,
    warmup_days: int = 120,
    params: GenerationParams | None = None,
) -> tuple[int, int]:
    """Generate parser-compatible pseudo weekly blogs and return (generated, skipped)."""
    if end < start:
        raise ValueError("end must be on or after start")
    if params is None:
        params = GenerationParams()

    # Buffer range for indicator warm-up and lookback.
    buffer_start = start - timedelta(days=420)
    cache_dir = Path(".backtest_cache")
    cache_start = infer_cache_start(cache_dir)
    if cache_start and buffer_start < cache_start:
        buffer_start = cache_start

    alpaca = AlpacaConfig.from_env()
    fmp = FMPConfig.from_env()
    provider = DataProvider(alpaca, fmp, cache_dir)
    provider.load_etf_data(ETF_SYMBOLS, buffer_start, end)
    provider.load_fmp_data(buffer_start, end)

    trading_days = provider.get_trading_days(buffer_start, end)
    if not trading_days:
        raise RuntimeError("No trading days in requested range")

    day_index = {d: i for i, d in enumerate(trading_days)}
    prices: dict[str, list[float]] = {s: [] for s in ETF_SYMBOLS}
    market: dict[date, tuple[float, float, float, float]] = {}

    for d in trading_days:
        etf = provider.get_etf_prices(d)
        for sym in ETF_SYMBOLS:
            px = etf.get(sym)
            if px is None:
                if prices[sym]:
                    px = prices[sym][-1]
                else:
                    px = 0.0
            prices[sym].append(px)

        m = provider.get_market_data(d)
        vix = float(m.vix if m.vix is not None else 20.0)
        spx = float(m.sp500 if m.sp500 is not None else prices["SPY"][-1] * 10)
        ndx = float(m.nasdaq if m.nasdaq is not None else prices["QQQ"][-1] * 45)
        dji = float(m.dow if m.dow is not None else prices["DIA"][-1] * 150)
        market[d] = (vix, spx, ndx, dji)

    first_valid_idx = None
    required_symbols = ("SPY", "QQQ", "DIA", "XLV", "XLP", "GLD", "XLE", "BIL")
    for i, d in enumerate(trading_days):
        if not all(prices[s][i] > 0 for s in required_symbols):
            continue
        vix, spx, ndx, dji = market[d]
        if min(vix, spx, ndx, dji) <= 0:
            continue
        first_valid_idx = i
        break
    if first_valid_idx is None:
        raise RuntimeError("No valid market history found in cache for requested range")

    out_dir = output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    week = first_monday_on_or_after(start)
    generated = 0
    skipped = 0

    while week <= end:
        obs = last_trading_day_on_or_before(week - timedelta(days=1), trading_days)
        if obs is None:
            skipped += 1
            week += timedelta(days=7)
            continue
        if day_index[obs] < first_valid_idx + warmup_days:
            skipped += 1
            week += timedelta(days=7)
            continue

        state = build_week_state(week, obs, day_index, prices, market, params)
        content = render_blog(state)

        out_file = out_dir / f"{week.isoformat()}-weekly-strategy.md"
        if out_file.exists() and not overwrite:
            skipped += 1
        else:
            out_file.write_text(content, encoding="utf-8")
            generated += 1

        week += timedelta(days=7)

    return generated, skipped


def main() -> None:
    args = parse_args()
    if args.end < args.start:
        raise SystemExit("--end must be on or after --start")

    generated, skipped = generate_pseudo_blogs(
        start=args.start,
        end=args.end,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
        warmup_days=args.warmup_days,
        params=GenerationParams(),
    )

    print(f"Output dir: {args.output_dir}")
    print(f"Generated: {generated}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()
