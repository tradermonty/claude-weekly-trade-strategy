# Daily Action Plan Tone Guidelines

Based on user feedback (2026-03-09) and MEMORY.md.

## Mandatory Rules

1. **Never declare "panic exit confirmed" or "reversal confirmed" based on closing price alone**
   - Intraday shocks (VIX 35, WTI $119) matter even if close looks calmer

2. **VIX 26 below 2-day consecutive is a custom Monty rule**
   - Always label as "Monty original rule", not a standard market signal

3. **Avoid overly bullish framing of politician statements**
   - Condition must be "official ceasefire/supply normalization signal from counterparty"

4. **Correct tone for stress situations**
   - Good: "Closed with stress-level pullback, but stress regime not yet cleared"
   - Bad: "Panic exit confirmed"

5. **Threshold realism**
   - Don't cite a threshold as imminent trigger when day's range contradicts it

6. **Data-first, opinion-second**
   - Present numbers first, then interpretation
   - Use plan_state.json values, never invent or round

7. **週足条件は金曜確定まで「推移中」と表記**
   - Bad: 月曜に「S&P 20週MA維持 → 達成中」
   - Good: 「推移中（水準上、金曜確定待ち）」
   - 金曜引け後のみ「達成」または「未達（週足確定）」と表記

8. **連続日条件は進捗を「N/M日達成」形式で表示**
   - Bad: 「VIX 26以下 → 距離: -0.5」（距離のみ）
   - Good: 「VIX 26以下 → 1/2日達成（本日条件充足）」
   - plan_state.json の `progress` フィールドをそのまま使用

## Style

- Concise: 5-minute read max
- Actionable: What to do, when, at what price
- Price-trigger based: Not "if EPS beats" but "if +8% gap up"
- Use tables for clarity
- Japanese language, technical terms in English
