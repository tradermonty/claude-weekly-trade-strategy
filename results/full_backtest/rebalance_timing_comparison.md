# Rebalance Timing Comparison Report

**Date**: 2026-02-14 (Sat)
**Backtest Period**: 2025-11-03 ~ 2026-02-13 (71 trading days)
**Initial Capital**: $100,000
**Blogs Used**: 16 (0 skipped)
**Slippage**: 0 bps

---

## Overview

Weekly trade strategy blog の allocation をどのタイミングでリバランスするかを比較する。
4パターンの組み合わせで検証:

| Variant | Phase | Rebalance Timing | Description |
|---------|-------|-----------------|-------------|
| A-transition | A (weekly rebalance) | Blog publish day's first trading day | 現行デフォルト |
| A-friday | A (weekly rebalance) | Every Friday (last trading day of week) | 毎週金曜にリバランス |
| B-transition | B (rule engine) | Blog publish day + trigger-based | 現行デフォルト |
| B-friday | B (rule engine) | Every Friday + trigger-based | 金曜定期 + トリガー臨時 |

---

## Summary Table

| Metric | A-transition | A-friday | B-transition | B-friday |
|--------|:-----------:|:--------:|:-----------:|:--------:|
| **Total Return** | +4.65% | +4.62% | **+5.19%** | +5.17% |
| **Max Drawdown** | -2.89% | -2.89% | -2.72% | -2.73% |
| **Sharpe Ratio** | 2.14 | 2.13 | **2.38** | 2.35 |
| **Total Trades** | **122** | 246 | 228 | 305 |
| **Final Value** | $104,653 | $104,623 | **$105,185** | $105,168 |

---

## Weekly Performance Comparison

### Phase A: transition vs friday

| Blog Week | A-transition | A-friday | Diff |
|-----------|:-----------:|:--------:|:----:|
| 2025-11-03 | -0.93% | -0.93% | 0.00pp |
| 2025-11-10 | -0.56% | -0.56% | 0.00pp |
| 2025-11-17 | -0.22% | -0.22% | 0.00pp |
| 2025-11-24 | +1.52% | +1.52% | 0.00pp |
| 2025-12-01 | +0.10% | +0.10% | 0.00pp |
| 2025-12-08 | +0.43% | +0.43% | 0.00pp |
| 2025-12-15 | -0.25% | -0.25% | 0.00pp |
| 2025-12-22 | +0.64% | +0.64% | 0.00pp |
| 2025-12-29 | -0.27% | -0.27% | 0.00pp |
| 2026-01-05 | +0.90% | +0.90% | 0.00pp |
| 2026-01-12 | -0.06% | -0.06% | 0.00pp |
| 2026-01-20 | +1.52% | +1.52% | 0.00pp |
| 2026-01-26 | -0.51% | -0.51% | 0.00pp |
| 2026-02-02 | +1.00% | +1.00% | 0.00pp |
| 2026-02-09 | -0.26% | -0.26% | 0.00pp |

### Phase B: transition vs friday

| Blog Week | B-transition | B-friday | Diff |
|-----------|:-----------:|:--------:|:----:|
| 2025-11-03 | -0.93% | -0.93% | 0.00pp |
| 2025-11-10 | -0.55% | -0.56% | -0.01pp |
| 2025-11-17 | +0.02% | +0.02% | 0.00pp |
| 2025-11-24 | +1.52% | +1.52% | 0.00pp |
| 2025-12-01 | +0.30% | +0.30% | 0.00pp |
| 2025-12-08 | +0.43% | +0.43% | 0.00pp |
| 2025-12-15 | -0.24% | -0.27% | -0.03pp |
| 2025-12-22 | +0.64% | +0.64% | 0.00pp |
| 2025-12-29 | -0.27% | -0.27% | 0.00pp |
| 2026-01-05 | +0.90% | +0.90% | 0.00pp |
| 2026-01-12 | -0.06% | -0.06% | 0.00pp |
| 2026-01-20 | +1.56% | +1.56% | 0.00pp |
| 2026-01-26 | -0.51% | -0.51% | 0.00pp |
| 2026-02-02 | +1.09% | +1.09% | 0.00pp |
| 2026-02-09 | -0.26% | -0.26% | 0.00pp |

---

## Analysis

### 1. Transition vs Friday: Negligible Return Difference

- Phase A: +4.65% vs +4.62% (diff **0.03pp**)
- Phase B: +5.19% vs +5.17% (diff **0.02pp**)

週次リターンの差は全週でほぼ 0.00pp。金曜リバランスは transition day とほぼ同じ allocation を適用するため、追加リバランスの効果は微少。この期間の相場は比較的穏やかなトレンド（+4~5%）で、週内ドリフトが小さかったことが主因と考えられる。

### 2. Trade Count: Friday Mode Doubles Trades

| Variant | Trades | vs Transition |
|---------|-------:|:------------:|
| A-transition | 122 | baseline |
| A-friday | 246 | **+102%** |
| B-transition | 228 | baseline |
| B-friday | 305 | **+34%** |

Friday モードでは毎週末にリバランスが発生するため、Phase A で約2倍、Phase B で約1.3倍のトレード数となる。スリッページやコミッションを考慮すると、トレードコスト増加が friday モードの不利要因になる。

### 3. Phase B Outperforms Phase A

| Metric | Phase A (best) | Phase B (best) | Advantage |
|--------|:--------------:|:--------------:|:---------:|
| Return | +4.65% | +5.19% | **+0.54pp** |
| Max DD | -2.89% | -2.72% | **+0.17pp** |
| Sharpe | 2.14 | 2.38 | **+0.24** |

Phase B のトリガーベースリバランス（VIX スパイク検知 → 防御シフト）が、ドローダウン抑制とリターン向上の両面で寄与。特に 2025-11-17 週（A: -0.22%, B: +0.02%）と 2025-12-01 週（A: +0.10%, B: +0.30%）で差が出ている。

### 4. Max Drawdown and Risk-Adjusted Return

全4パターンで Max Drawdown は -2.72% ~ -2.89% と低水準。Sharpe Ratio は全パターンで 2.0 超と良好。Phase B の方がリスク調整後リターンで優位。

---

## Conclusions

1. **Best overall**: **B-transition** (+5.19%, Sharpe 2.38, 228 trades)
2. **Friday rebalancing adds no meaningful alpha** in this period (+0.02~0.03pp)
3. **Friday rebalancing increases trade costs** significantly (x1.3 ~ x2.0)
4. **Trigger-based rebalancing (Phase B)** is more effective than periodic rebalancing alone

### Recommendations

- **Default setting remains `transition`** - 金曜リバランスの優位性は確認されず
- **Phase B を推奨** - トリガーベースの方がリスク管理に優れる
- **追加検証が有効な場面**:
  - スリッページを 5~10 bps で再検証（friday モードの不利が顕在化するか）
  - 急落局面を含むより長い期間での検証（friday モードが早期復帰に寄与するか）
  - 2025年前半（correction 含む期間）でのバックテスト

---

## Reproduction

```bash
# Phase A - transition (default)
uv run python -m trading.backtest --start 2025-11-03 --end 2026-02-14 \
  --phase A --output results/full_backtest/phase_a

# Phase A - friday
uv run python -m trading.backtest --start 2025-11-03 --end 2026-02-14 \
  --phase A --timing week_end --output results/full_backtest/phase_a_friday

# Phase B - transition (default)
uv run python -m trading.backtest --start 2025-11-03 --end 2026-02-14 \
  --phase B --output results/full_backtest/phase_b

# Phase B - friday
uv run python -m trading.backtest --start 2025-11-03 --end 2026-02-14 \
  --phase B --timing week_end --output results/full_backtest/phase_b_friday
```

---

*Generated by backtest engine v1.0 with `--timing` variant support*
