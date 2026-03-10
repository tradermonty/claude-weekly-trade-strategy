# Daily Action Plan Template

## Pre-Market Version

```markdown
# {date} Pre-Market Action Plan

**タイミング**: 寄り付き前
**フェーズ**: {phase}
**データ注記**: 延長取引/気配値ベース（前営業日終値は比較用、本日終値は未確定）

---

## 市場サマリー（延長取引/気配値）

| 指標 | 現在値 | 前日比 | 評価 |
|------|--------|--------|------|
| VIX | {vix} | {vix_change} | {vix_eval} |
| S&P 500 | {sp500} | {sp500_change_pct} | |
| Nasdaq 100 | {nasdaq} | {nasdaq_change_pct} | |
| 10Y利回り | {us10y}% | | {yield_eval} |
| Gold(GC) | ${gold} | {gold_change_pct} | |
| WTI Oil | ${oil} | {oil_change_pct} | |

## Breadth（CSV最新）

| 指標 | 値 | 評価 |
|------|-----|------|
| 200-day MA | {breadth_200ma}% | {breadth_200ma_class} |
| 8-day MA | {breadth_8ma}% | {breadth_8ma_class} |
| Uptrend Ratio | {uptrend_ratio}% {uptrend_color} | {uptrend_class} |

## トリガー評価（暫定）

| トリガー | 基準 | 現在値 | 距離 | 進捗 |
|---------|------|--------|------|------|
{trigger_evaluation_rows}

*注: 進捗は気配値/延長取引ベースの暫定判定。終値確定後に変わる可能性あり。*

## 本日のイベント

{todays_events}

## 推奨アクション

{recommended_actions}

## 朝チェックリスト

{morning_checklist}

---
*Source: FMP API + TraderMonty CSV | Blog: {blog_date}*
```

## Post-Market Version

```markdown
# {date} Post-Market Action Plan

**タイミング**: 引け後
**フェーズ**: {phase}

---

## 本日の市場結果

| 指標 | 終値 | 前日比 | 変化率 | 評価 |
|------|------|--------|--------|------|
| VIX | {vix} | {vix_change} | {vix_change_pct} | {vix_eval} |
| S&P 500 | {sp500} | {sp500_change} | {sp500_change_pct} | |
| Nasdaq 100 | {nasdaq} | {nasdaq_change} | {nasdaq_change_pct} | |
| 10Y利回り | {us10y}% | | | {yield_eval} |
| Gold(GC) | ${gold} | {gold_change} | {gold_change_pct} | |
| WTI Oil | ${oil} | {oil_change} | {oil_change_pct} | |

## Breadth（CSV最新）

| 指標 | 値 | 評価 |
|------|-----|------|
| 200-day MA | {breadth_200ma}% | {breadth_200ma_class} |
| 8-day MA | {breadth_8ma}% | {breadth_8ma_class} |
| Uptrend Ratio | {uptrend_ratio}% {uptrend_color} | {uptrend_class} |

## トリガー評価

| トリガー | 基準 | 現在値 | 距離 | 進捗 |
|---------|------|--------|------|------|
{trigger_evaluation_rows}

## シナリオ判定

{scenario_judgment}

## 明日に向けて

{tomorrow_actions}

## 夜チェックリスト

{evening_checklist}

---
*Source: FMP API + TraderMonty CSV | Blog: {blog_date}*
```
