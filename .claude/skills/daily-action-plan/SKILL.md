# Daily Action Plan

Generate a daily pre-market or post-market action plan by comparing the latest weekly blog strategy with real-time market data.

## Triggers

- User says "daily action plan", "DAP", "daily plan", "デイリーアクション", "寄り付きプラン", "引け後プラン"
- User says "run daily-action-plan"
- `claude -p "Run daily-action-plan --timing {pre-market|post-market}"`

## Arguments

- `--timing {pre-market|post-market}` (default: auto-detect based on current time)
  - pre-market: Before 9:30 AM ET (23:30 JST winter / 22:30 JST summer)
  - post-market: After 4:00 PM ET (6:00 JST winter / 5:00 JST summer)

## Workflow

### Step 1: Holiday Check

```bash
python3 .claude/skills/daily-action-plan/scripts/build_plan_state.py --check-only
```

- `CLOSED` → Output a brief "Markets Closed" message with next trading day and stop.
- `EARLY_CLOSE` → Continue with early close note.
- `OPEN` → Continue normally.

### Step 2: Data Fetching (only if market is open)

Fetch market data and breadth data in parallel:

```bash
python3 scripts/fetch_market_close.py --json > /tmp/dap_market.json
python3 .claude/skills/breadth-chart-analyst/scripts/fetch_breadth_csv.py --json > /tmp/dap_breadth.json
```

**CRITICAL**: These scripts must complete successfully. If either fails, report the error and stop.

### Step 3: Build plan_state.json

```bash
python3 .claude/skills/daily-action-plan/scripts/build_plan_state.py \
    --timing {pre-market|post-market} \
    --market-json /tmp/dap_market.json \
    --breadth-json /tmp/dap_breadth.json \
    --output /tmp/plan_state.json
```

### Step 4: Verify plan_state.json

```bash
python3 .claude/skills/daily-action-plan/scripts/verify_plan.py \
    --plan-state /tmp/plan_state.json \
    --market-json /tmp/dap_market.json \
    --breadth-json /tmp/dap_breadth.json
```

- `PASS` → Continue to Step 5.
- `FAIL` → Display errors. Investigate and fix if possible, otherwise stop.

### Step 5: Generate Action Plan

Read `plan_state.json` and generate the action plan document in Japanese.

**Reference files to read before writing**:
- `.claude/skills/daily-action-plan/references/monty_thresholds.md` — threshold values
- `.claude/skills/daily-action-plan/references/tone_guidelines.md` — tone rules
- `.claude/skills/daily-action-plan/assets/action_plan_template.md` — output template

**Writing rules**:
1. Use ONLY values from `plan_state.json` — never invent or round numbers
2. VIX evaluation uses Monty thresholds: 17(Risk-On)/20(Caution)/23(Stress)/26(Panic)
3. Include trigger distances for each scenario
4. List today's events from `plan_state.json > events > todays_events`
5. Include the relevant checklist (morning for pre-market, evening for post-market)
6. Follow tone_guidelines.md strictly — no "confirmed" language, no rounding
7. Phase status from blog must be prominently displayed
8. Trigger status must use `progress` field from plan_state.json — never manually
   classify as "達成中" for weekly conditions or omit day-count for consecutive conditions

**Pre-market specifics**:
- Data is extended-hours/pre-market quote; previous close is used for comparison only
- Trigger progress is provisional (based on current quote, not confirmed close)
- Focus on: morning checklist, today's events, key levels to watch
- Include recommended actions based on blog scenarios

**Post-market specifics**:
- Use official closing data
- Evaluate trigger conditions against actual closes
- Determine which scenario is currently closest
- Include evening checklist, tomorrow's focus

**Reading triggers from `plan_state.json` (MANDATORY)**:

**Whether a scenario has fired is a stored verdict. Never infer it from legs.**

1. **Scenario verdict** — `analysis.trigger_coverage.scenario_rules[<name>]`:
   ```
   { "rule": "all" | "at_least" | "any", "min_legs": N,
     "leg_count": N, "met_leg_count": N, "undecided_leg_count": N,
     "satisfied": true|false }
   ```
   `rule` comes from the blog's own wording — `all` for 「すべて満たす」, `at_least`
   with `min_legs` for 「2つ以上」, `any` for 「いずれか1つ」. **A scenario with
   five legs and `rule: "all"` has NOT fired on one leg.** Report
   `met_leg_count / leg_count` and `satisfied`, in that order.
2. **AND legs within a scenario** (`and_group: "<scenario>#<n>"`) — read
   `analysis.trigger_coverage.and_groups[].satisfied`; each leg also carries
   `and_satisfied`. A group showing `met_count: 1, leg_count: 2,
   satisfied: false` has **not** fired.
3. **Per-leg state** — use `condition_met`, not `met_close`. `met_close` only
   says the level is breached today; `condition_met` folds in the time basis, so
   a 終値2日連続 leg is `false` on day one and `null` when it cannot be decided
   (pre-market, or no previous close on file). `undecided_leg_count > 0` means
   some legs are still unresolved — say so rather than implying a verdict.

**Coverage is fail-closed.** `analysis.trigger_coverage` must satisfy
`evaluated_leg_total + len(manual_only) == source_leg_total`, and the same
identity per scenario. `verify_plan.py` check #18 fails otherwise — meaning a
trigger written in the blog was not evaluated at all. **Do not write the action
plan from a plan_state whose #18, #19 or #20 failed; rebuild it first.** A leg
no branch can evaluate must be declared with `--manual-only-leg "<text>"` so it
is visible, never left to disappear.

### Step 6: Self-Check

Verify the generated plan against `plan_state.json`:
1. Every number in the output must match `plan_state.json` exactly
2. VIX/10Y evaluations must match threshold classifications
3. Scenario probabilities must match blog values
4. Allocation percentages must match blog values

If any mismatch is found, correct and re-verify (max 3 attempts).

### Step 7: Save Output

```bash
mkdir -p reports/YYYY-MM-DD
```

Save to: `reports/YYYY-MM-DD/daily-action-plan-{pre|post}.md`

**IMPORTANT: Do NOT send email or call `send_dap_email.py`.** Email notification is handled by the wrapper script (`run_daily_action_plan.sh`) after this skill completes. Calling it here would cause duplicate emails.

## Output Format

See `assets/action_plan_template.md` for the full template.

Key sections:
1. **Market Summary** — Current prices with evaluations
2. **Breadth Data** — 200MA, 8MA, Uptrend Ratio with classifications
3. **Scenario Distance** — How far current values are from each scenario's triggers
4. **Today's Events** — Events for today (including daily events like geopolitical monitoring)
5. **Recommended Actions** — Based on blog strategy and current data
6. **Checklist** — Morning or evening checklist from blog

## Data Flow

```
scripts/fetch_market_close.py --json → /tmp/dap_market.json
fetch_breadth_csv.py --json         → /tmp/dap_breadth.json
blogs/YYYY-MM-DD-weekly-strategy.md → (parsed by strategy_parser)
                                    ↓
build_plan_state.py → /tmp/plan_state.json
                    ↓
verify_plan.py → PASS/FAIL
                ↓
[Claude generates plan from plan_state.json]
                ↓
reports/YYYY-MM-DD/daily-action-plan-{pre|post}.md
```

## Dependencies

- `scripts/fetch_market_close.py` — FMP API (requires FMP_API_KEY in .env)
- `.claude/skills/breadth-chart-analyst/scripts/fetch_breadth_csv.py` — TraderMonty CSV
- `trading/layer2/tools/strategy_parser.py` — Blog parser
- `trading/core/holidays.py` — US market holiday calendar

## Error Handling

| Error | Action |
|-------|--------|
| FMP API key missing | Print error, stop |
| FMP API timeout | Retry once, then stop |
| Breadth CSV fetch fails | Retry once, then stop |
| No blog found | Print error, stop |
| Blog parse fails | Print error with details, stop |
| verify_plan.py FAIL | Show failed checks, investigate |
| Self-check mismatch | Auto-correct, re-verify (max 3) |
