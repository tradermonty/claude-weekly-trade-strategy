# Weekly Trade Strategy Blog - Project Guide

This project is a system for automatically generating weekly trade strategy blog posts for US stock markets.

---

## Project Structure

```
weekly-trade-strategy/
├── charts/              # Chart image storage
│   └── YYYY-MM-DD/     # Folders by date
│       ├── chart1.jpeg
│       └── chart2.jpeg
│
├── reports/            # Analysis report storage
│   └── YYYY-MM-DD/    # Folders by date
│       ├── technical-market-analysis.md
│       ├── us-market-analysis.md
│       └── market-news-analysis.md
│
├── blogs/              # Final blog post storage
│   └── YYYY-MM-DD-weekly-strategy.md
│
└── .claude/
    ├── agents/         # Agent definitions
    └── skills/         # Skill definitions
```

## Standard Workflow for Weekly Blog Creation

### Step 0: Preparation

1. **Place Chart Images**
   ```bash
   # Create folder for this week's date
   mkdir -p charts/2025-11-03

   # Place chart images (16 recommended, breadth 2 analyzed separately)
   #
   # Technical Market Analysis targets (14 charts):
   # - VIX (weekly)
   # - US 10Y Treasury Yield (weekly)
   # - Nasdaq 100 (weekly)
   # - S&P 500 (weekly)
   # - Russell 2000 (weekly)
   # - Dow Jones (weekly)
   # - Gold Futures (weekly)
   # - Copper Futures (weekly)
   # - Crude Oil (weekly)
   # - Natural Gas (weekly)
   # - Uranium ETF (URA, weekly)
   # - Sector Performance (1 week)
   # - Sector Performance (1 month)
   # - Major Stock Heatmap
   #
   # Market Breadth Analysis targets (2 charts, analyzed separately):
   # - S&P 500 Breadth Index (200-day MA + 8-day MA) <- technical-market-analyst skips
   # - Uptrend Stock Ratio (all markets) <- technical-market-analyst skips
   ```

2. **Create Report Output Folder**
   ```bash
   mkdir -p reports/2025-11-03
   ```

### Step 1: Technical Market Analysis

**Purpose**: Analyze chart images and evaluate market environment from technical indicators

**Agent**: `technical-market-analyst`

**Important Note**: Market Breadth analysis (S&P 500 Breadth Index, Uptrend Ratio) is performed **separately**. The technical-market-analyst agent **skips** these charts.

**Input**:
- `charts/YYYY-MM-DD/*.jpeg` (all chart images)

**Output**:
- `reports/YYYY-MM-DD/technical-market-analysis.md`

**Example Command**:
```
Please run chart analysis for this week (2025-11-03) using the technical-market-analyst agent.
Analyze the charts in charts/2025-11-03/.
However, **skip** the following breadth charts (analyzed separately):
- S&P 500 Breadth Index (200-day MA + 8-day MA)
- Uptrend Stock Ratio (all markets)

Save the report to reports/2025-11-03/technical-market-analysis.md.
```

**Analysis Content**:
- VIX, 10Y yield current values and evaluation
- Technical analysis of major indices (Nasdaq, S&P500, Russell2000, Dow)
- Trend analysis of commodities (gold, copper, oil, uranium)
- Sector rotation analysis
- Probability evaluation by scenario

**Not Analyzed**:
- S&P 500 Breadth Index - analyzed separately by breadth-chart-analyst skill
- Uptrend Stock Ratio - analyzed separately by breadth-chart-analyst skill

---

### Step 2: US Market Analysis

**Purpose**: Comprehensive market environment evaluation and bubble risk detection, **detailed Breadth chart analysis**

**Agent**: `us-market-analyst`

**Input**:
- `reports/YYYY-MM-DD/technical-market-analysis.md` (Step 1 result)
- **CSV data via `fetch_breadth_csv.py`** (PRIMARY source for Breadth/Uptrend Ratio)
- Breadth chart images in `charts/YYYY-MM-DD/` (supplementary visual confirmation)
- Market data (VIX, Breadth, interest rates, etc.)

**Output**:
- `reports/YYYY-MM-DD/us-market-analysis.md`

**Example Command**:
```
Please run comprehensive US market analysis using the us-market-analyst agent.
Reference reports/2025-11-03/technical-market-analysis.md,
fetch CSV data first via fetch_breadth_csv.py for accurate Breadth/Uptrend Ratio values,
then confirm with chart images in charts/2025-11-03/.
Save to reports/2025-11-03/us-market-analysis.md.
```

**Analysis Content**:
- Current market phase (Risk-On / Base / Caution / Stress)
- Bubble detection score (0-16 scale)
- **Breadth Index (200-day MA) current value and trend** (from CSV)
- **Uptrend Stock Ratio current value, color (green/red), bottom reversal signal** (from CSV)
- Sector rotation pattern
- Volatility regime

**Important**: Uptrend Stock Ratio is a **leading indicator**. Bottom reversals (red to green transition, rebound from 20% range) often show improvement 1-2 weeks before Breadth 200MA. **CSV data is the primary source; chart images are supplementary**.

---

### Step 3: Market News Analysis

**Purpose**: News impact analysis for past 10 days and event forecast for next 7 days

**Agent**: `market-news-analyzer`

**Input**:
- `reports/YYYY-MM-DD/technical-market-analysis.md` (Step 1 result)
- `reports/YYYY-MM-DD/us-market-analysis.md` (Step 2 result)
- Economic calendar, earnings calendar

**Output**:
- `reports/YYYY-MM-DD/market-news-analysis.md`

**Example Command**:
```
Please run news and event analysis using the market-news-analyzer agent.
Analyze news impact for the past 10 days and important events for the next 7 days,
and save to reports/2025-11-03/market-news-analysis.md.
```

**Analysis Content**:
- Major news and market impact for past 10 days
- Economic indicator schedule for next 7 days
- Major earnings releases (market cap $2B+)
- Scenario analysis by event (with probabilities)
- Risk event prioritization

---

### Step 4: Weekly Blog Generation

**Purpose**: Integrate three reports and generate weekly strategy blog for part-time traders

**Agent**: `weekly-trade-blog-writer`

**Input**:
- `reports/YYYY-MM-DD/technical-market-analysis.md`
- `reports/YYYY-MM-DD/us-market-analysis.md`
- `reports/YYYY-MM-DD/market-news-analysis.md`
- `blogs/` (previous week's blog post, for continuity check)

**Output**:
- `blogs/YYYY-MM-DD-weekly-strategy.md`

**Example Command**:
```
Please create the blog post for the week of November 3, 2025 using the weekly-trade-blog-writer agent.
Integrate the three reports under reports/2025-11-03/,
maintain continuity with previous week's sector allocation,
and save to blogs/2025-11-03-weekly-strategy.md.
```

**Article Structure** (200-300 lines):
1. **3-Line Summary** - Market environment, focus, strategy
2. **This Week's Action** - Position sizing, buy/sell levels, sector allocation, key events
3. **Scenario Plans** - Base/Risk-On/Caution 3 scenarios
4. **Market Conditions** - Unified triggers (10Y/VIX/Breadth)
5. **Commodity/Sector Tactics** - Gold/Copper/Uranium/Oil
6. **Part-Time Trading Guide** - Morning/Evening checklists
7. **Risk Management** - This week's specific risks
8. **Summary** - 3-5 sentences

**Important Constraints**:
- Sector allocation changes from previous week must be **within ±10-15%** (gradual adjustment)
- During ATH + Base triggers, avoid sudden position reduction
- Cash allocation increases gradually (e.g., 10% -> 20-25% -> 30-35%)

**"Monty Style" Guide (Mandatory)**:

Follow these rules to maintain the established "Monty Style" in blog posts:

1. **Triggers are Price Reaction Based**
   - Bad: "NVIDIA revenue $55B+, Q4 guidance $58B+"
   - Good: "**Post-NVIDIA earnings +8% gap up & new high**" "**-8% gap down or 50-day MA break**"
   - Reason: Part-time traders don't have time to read earnings reports. Use price and technical levels for immediate decisions.

2. **Indicator Levels are Standardized**
   - **VIX**: **17**(Risk-On) / **20**(Caution) / **23**(Stress) / **26**(Panic)
   - **US 10Y Yield**: **4.11%**(lower) / **4.36%**(warning) / **4.50%**(red line) / **4.60%**(extreme)
   - **Breadth (above 200-day MA)**: **60%+**(healthy) / **50%**(border) / **40% or less**(fragile)
   - Reason: Maintain consistency with past articles, avoid reader confusion.

3. **Sector Allocation is 4-Pillar Structure**
   - **Core Index** (SPY/QQQ/DIA): 40-50%
   - **Defensive Sector** (Healthcare + Consumer Staples): 15-25%
   - **Theme/Hedge** (Energy + Gold + Commodities): 15-25%
   - **Cash/Short-term Bonds** (BIL): 15-30%
   - **Important**: Energy is classified as "**Inflation Hedge + Opportunistic**" in category 3, not "Defensive Sector"
   - Reason: Total 100% allocation is clear at a glance. Practical for readers.

4. **Always Include Allocation Examples**
   ```
   - For $100K portfolio:
     - Core Index: $45-50K
     - Defensive (Healthcare $12-15K + Staples $5-8K): $17-23K
     - Theme (Energy $10-12K + Gold $10-12K): $20-24K
     - Cash: $20-25K
   ```
   - Reason: Help understanding with concrete dollar examples, not just abstract percentages.

5. **Breadth Interpretation is Objective**
   - Bad: "Breadth 53% is historically worst"
   - Good: "Breadth 53% indicates a **narrow rally**. Well below 60%+ healthy level, but hasn't reached 40% fragile line"
   - Reason: 53% is an intermediate level. Avoid extreme expressions, align with past standards (0.6+: strong, 0.5: border, 0.4-: warning).

6. **ETF-Based Hedges are Main, Options are Supplementary**
   - **Main Strategy**: Gold (GLD), Long-term Bonds (TLT), Inverse Index (SH/SDS), Short-term Bonds (BIL)
   - **Advanced Supplement**: VIX calls, QQQ puts, SPY puts
   - Example:
     ```markdown
     ### Advanced Options Strategy (Supplement)

     **Note**: The following is for experienced options traders. Part-time traders should use ETF hedges above.

     - VIX call: Buy 25 strike before 11/20 earnings (cost 1-2%)
     - QQQ put: $490 strike (NVIDIA downside hedge, current ~$510, 12/20 expiry)
     ```
   - Reason: Most part-time traders are inexperienced with options. Main strategy should be complete with ETFs.

7. **Part-Time Trading Guide is Price Trigger Based**
   - Bad: "Check earnings content, if EPS/revenue beats expectations, add to position"
   - Good:
     ```markdown
     1. **NVIDIA Earnings Deep Dive (Wed 11/20)**:
        - Check gap size (**+8% or -8%**)
        - Position relative to 20-week MA ($24,558) and 50-day MA (~$24,000)
        - Confirm if closing at new high or engulfing bearish candle
     ```
   - Reason: Format that allows decisions just by looking at charts before work in morning or after work at night.

8. **Minimize Operations in Scenario Plans**
   - Bad: "Core 40-45%->30-35%, Defensive 27-35%->35-40%, Theme 15-20%->10-15%, Cash 20-25%->30-35%" (4 simultaneous changes)
   - Good: "Change only **3 pillars**: Core, Defensive, Cash"
   - Reason: Part-time traders have limited time. Minimize operational complexity.

9. **Allocation Percentages Stay Within 100%**
   - Bad: "Equity 45-50% + Defensive 18-23% + Theme 15-20% = 78-93% invested, Cash 20-25%" (simple sum appears 98-118%)
   - Good:
     ```
     Recommended Risk Allocation: Equity & Commodities total 75-80%, Cash & Short-term Bonds 20-25%
     - Core Index: 45-50%
     - Defensive Sector: 18-23%
     - Theme/Hedge: 15-20%
     - Cash/Short-term Bonds: 20-25%

     *Note: Categories 1-3 include some overlap in equity/commodity portion.
     Overall portfolio assumes risk asset exposure cap of 75-80%,
     with remaining 20-25% in cash/short-term bonds.
     ```
   - Reason: Prevent reader confusion from "78-93% + 20-25% = 98-118%?". 4 pillars include overlap, actual total is ~75-80%.

10. **Unified Earnings Timing Notation**
    - Bad: Event table says "AMC (After Market Close)" but morning check says "pre-market release"
    - Good: "**Released after market close (AMC)**. Check **±8-10% gap before next morning's open** for scenario decision"
    - Reason: AMC earnings are released after close, so decision is made before next morning's open. Unify timing notation to prevent confusion.

11. **Consolidate ATR References in One Place**
    - Bad: Multiple places in text mention "ATR 1.6x" "NVDA week 1.2x"
    - Good:
      - First half: "Individual stocks: **ATR-based** (see Risk Management section for details)"
      - Risk Management section: "**ATR 1.6x** (-6-8%) immediate stop loss. **NVIDIA earnings week reduced to 1.2x** (-5-6%)"
    - Reason: Lighter reading, details can be confirmed in Risk Management section.

12. **Asset Name and Price Scale Consistency**
    - When using futures prices → use futures notation (GC, NQ, CL)
    - When using ETF names → use ETF-scale prices
    - Combined notation: "Gold Futures(GC)/ETF: GLD | GC $5,080"
    - Bad: "Gold(GLD) $5,080" → GLD≈$508, $5,080 is GC scale
    - Good: "Gold Futures(GC) $5,080 (ETF: GLD≈$508)"
    - Reason: Mixing ETF names with futures prices causes reader confusion and incorrect trade sizing.

13. **Options Strike Price Scale Verification**
    | Instrument | ETF Scale | Index/Futures Scale |
    |------------|-----------|---------------------|
    | QQQ / NDX | $XXX range | XXXXX range |
    | GLD / GC | $XXX range | $X,XXX range |
    | SPY / SPX | $XXX range | X,XXX range |
    - Default warning: Strike >±20% from underlying current price → requires confirmation
    - Exception allowed: If hedge purpose, expiry, and IV are explicitly stated, >±20% OTM is acceptable
      Example: "QQQ put $450 (current $510, -12% OTM, insurance purpose, 3/20 expiry, IV 25%)" → OK
    - Bad: "QQQ put 24,000" → QQQ≈$510, 24,000 is NDX (fundamentally different scale → REVISION REQUIRED)
    - Good: "QQQ put $490 (current ~$510, -4%)"
    - Reason: Wrong-scale strikes lead to impossible trades and destroy reader trust.

14. **Intra-Article Consistency Check (Base Policy vs Scenario Actions)**
    - **Base Policy Consistency** (must be unified across these sections):
      - 3-line summary, This Week's Action table, Sector Allocation table, Commodity/Sector Tactics table
      - Same ETF having contradictory policies (increase/maintain/decrease) across these → REVISION REQUIRED
        Bad: This Week's Action "XLE maintain" → Commodity Tactics "XLE increase 5%→6%"
    - **Scenario Conditional Actions** (changes per scenario are normal):
      - Within Scenario Plans (Bull/Bear/Tail Risk), increases/decreases based on conditions are OK
      - However, **logical consistency between premise and recommended action** is mandatory:
        Bad: Bull Case "crude oil pullback" premise → XLE addition (contradicts premise)
        Good: Bull Case "crude oil pullback" premise → XLE reduction → shift to copper
    - **Scenario Allocation Detail**:
      - Show not just category totals but ETF-level numerical breakdown
        Bad: "Theme 16%→18% (+2%)" (breakdown unknown)
        Good: "Theme 16%→18% (GLD 10% maintain, XLE 4% reduce, COPX 4% new)"
    - Reason: Part-time traders execute from a single article; contradictions cause wrong trades.

15. **Trigger Time Criteria, Probability Basis, Source Attribution**
    - **Trigger Time Criteria**:
      - All triggers must specify "closing/intraday" × "immediate/2-day consecutive/weekly close"
        - Panic-level (VIX 26+): "Intraday, immediate action"
        - Stress-level (VIX 23+): "Closing basis, 2-day consecutive"
        - Normal: "Closing basis confirmation"
      - Bad: "VIX 23超定着"
      - Good: "VIX 23超を終値ベースで2日連続"
    - **Probability Basis**:
      - Bare "probability 40%" is prohibited
      - Format: "Author estimate X% (basis: news frequency/market consensus/historical)"
    - **Source Attribution**:
      - All external references must include URLs (media name alone is insufficient)
      - Internal report references → replace with actual data source URLs (TraderMonty CSV, TradingView, etc.)
    - Reason: Vague triggers cause hesitation; unsourced claims undermine credibility.

16. **配分変更に実行タイミングを明記**
    - ロット管理テーブルの各行に「いつ実行するか」を記載
    - Bad: 根拠のみ記載、タイミングは読者の判断任せ
    - Good:
      | カテゴリ | 前週 | 今週 | 変化 | 実行タイミング | 根拠 |
      |---------|------|------|------|-------------|------|
      | コア指数 | 34% | 38% | +4% | 月曜寄り | VIX改善でSPY追加 |
      | テーマ | 14% | 16% | +2% | 月曜寄り | 米イラン緊張でGLD増 |
    - タイミング種別: 「月曜寄り」「〇曜イベント後」「トリガー時」「段階的」
    - Reason: 兼業トレーダーは「何を」だけでなく「いつ」が分からないと実行できない

---

### Step 5 (Required): Iterative Quality Assurance — 3-Round Review

**Purpose**: Ensure quality through up to 3 review→auto-fix cycles before human review

**Agent**: `strategy-reviewer` (review) + orchestrator (fix)

**Process**:

```
Round 1: strategy-reviewer → findings list
  ├── PASS → Done (Step 5 complete)
  └── findings exist → auto-fix → Round 2

Round 2: strategy-reviewer (verify previous findings + full invariant check + regression detection)
  ├── PASS → Done
  └── findings exist → auto-fix → Round 3

Round 3: strategy-reviewer (final full check)
  ├── PASS → Done
  ├── PASS WITH NOTES → OK to publish (with notes)
  └── REVISION REQUIRED → Human review required (High severity remaining)
```

**Review Scope by Round**:

| Round | Review Scope | Fix Agent |
|-------|-------------|-----------|
| Round 1 | Full checklist (complete review) | Auto-fix |
| Round 2 | Previous findings verification + **full invariant check** + regression detection | Auto-fix |
| Round 3 | Remaining findings + **full checklist (complete review)** | — |

**Invariant Checks (mandatory full check every round)**:
- 4-pillar allocation total = 100% (all scenarios)
- Scenario probability total = 100%
- $100K portfolio example = matches allocation %
- VIX/10Y/Breadth trigger levels match standard values
- Asset notation scale consistency across all instances

**Final Verdict Criteria**:
- **PASS**: All findings resolved
- **PASS WITH NOTES**: No High severity, only Medium/Low remaining
- **REVISION REQUIRED**: High severity remaining (human review required)

**Example Command (3-round batch)**:
```
Please run iterative QA (up to 3 rounds) for the blog of 2026-02-23.

Round 1: Full review of blogs/2026-02-23-weekly-strategy.md with strategy-reviewer.
If findings exist, fix them and run Round 2 (verify fixes + invariants + regressions).
If Round 2 has findings, fix and run Round 3 (final full review).
Save final review to reports/2026-02-23/strategy-review.md with round count.
```

**Input**:
- All chart images in `charts/YYYY-MM-DD/` (**re-reading required**)
- `reports/YYYY-MM-DD/technical-market-analysis.md`
- `reports/YYYY-MM-DD/us-market-analysis.md`
- `reports/YYYY-MM-DD/market-news-analysis.md`
- `blogs/YYYY-MM-DD-weekly-strategy.md` (review target)
- Previous week's blog post (for continuity check)

**Output**:
- `reports/YYYY-MM-DD/strategy-review.md`

**Review Content**:
- **Data Verification**: Re-read chart images, compare with blog values
- **Uptrend Ratio Confirmation**: Check for missed bottom reversal signals (most important)
- **Allocation Calculation Check**: Verify 4 pillars total 100%
- **Scenario Consistency**: Check probabilities and stance match between reports
- **Continuity Check**: Verify ±10-15% gradual adjustment from previous week
- **Instrument Notation**: ETF/futures scale consistency (Issue #8)
- **Trigger Precision**: Time criteria, probability basis, source URLs (Issue #8)
- **Intra-Article Consistency**: Base policy vs scenario actions (Issue #8)

**Important**: This step is **required**. Always run before publishing blog post.
The Uptrend Ratio oversight issue can be detected by this review.

---

### Step 6 (Optional): Druckenmiller Strategy Planning

**Purpose**: Integrate three analysis reports and formulate 18-month medium-long term investment strategy

**Agent**: `druckenmiller-strategy-planner`

**Input**:
- `reports/YYYY-MM-DD/technical-market-analysis.md` (Step 1 result)
- `reports/YYYY-MM-DD/us-market-analysis.md` (Step 2 result)
- `reports/YYYY-MM-DD/market-news-analysis.md` (Step 3 result)
- Previous Druckenmiller strategy report (if exists)

**Output**:
- `reports/YYYY-MM-DD/druckenmiller-strategy.md`

**Example Command**:
```
Please formulate the 18-month strategy as of November 3, 2025 using the druckenmiller-strategy-planner agent.
Comprehensively analyze the three reports under reports/2025-11-03/,
apply Druckenmiller's strategy framework,
and save to reports/2025-11-03/druckenmiller-strategy.md.
```

**Analysis Framework**:

1. **Druckenmiller's Investment Philosophy**
   - Macro-focused 18-month forward analysis
   - Position sizing based on conviction
   - Concentrated investment when multiple factors align
   - Quick stop-losses and flexibility

2. **4 Scenario Analysis** (with probabilities)
   - **Base Case** (highest probability scenario)
   - **Bull Case** (optimistic scenario)
   - **Bear Case** (risk scenario)
   - **Tail Risk** (low probability extreme scenario)

3. **Components of Each Scenario**
   - Key catalysts (policy, economy, geopolitics)
   - Timeline (Q1-Q2, Q3-Q4 developments)
   - Impact by asset class
   - Optimal positioning strategy
   - Invalidation signals (strategy change triggers)

**Report Template**: See `.claude/agents/druckenmiller-strategy-planner.md` for full template (~60 lines).

**Key Features**:
- Unlike weekly blog (short-term tactics), this is **18-month medium-long term strategy**
- Focus on macro-economic structural changes and policy turning points
- Position sizing by conviction level (High/Medium/Low)
- Clear invalidation conditions for each scenario
- Uses stanley-druckenmiller-investment skill

**Execution Timing**:
- Simultaneously with weekly blog (quarterly recommended)
- After major events like FOMC
- At major market structure turning points

**Auto-Generation of Missing Reports**:
If upstream reports (Steps 1-3) don't exist, druckenmiller-strategy-planner automatically calls the missing agents.

---

## Batch Execution Script (Recommended)

```bash
# Set date
DATE="2025-11-03"

# Step 0: Prepare folders
mkdir -p charts/$DATE reports/$DATE

# Example prompt for batch execution of Steps 1-5:
"Please create the trade strategy blog for the week of $DATE.

1. Analyze all charts in charts/$DATE/ with technical-market-analyst
   -> reports/$DATE/technical-market-analysis.md

2. Comprehensive market environment evaluation with us-market-analyst (including Breadth chart re-reading)
   -> reports/$DATE/us-market-analysis.md

3. News/event analysis with market-news-analyzer
   -> reports/$DATE/market-news-analysis.md

4. Generate final blog post with weekly-trade-blog-writer
   -> blogs/$DATE-weekly-strategy.md

5. Quality review with strategy-reviewer (required)
   -> reports/$DATE/strategy-review.md
   -> Determine PASS/PASS WITH NOTES/REVISION REQUIRED

Execute each step sequentially and confirm report before proceeding to next.
If Step 5 returns REVISION REQUIRED, correct and re-review."
```

---

## Data Flow Between Agents

### Weekly Blog Generation Flow

```
charts/YYYY-MM-DD/
  ├─> [technical-market-analyst]
  │      └─> reports/YYYY-MM-DD/technical-market-analysis.md
  │            │
  │            ├─> [us-market-analyst] <── also re-reads charts/ (breadth-chart-analyst)
  │            │      └─> reports/YYYY-MM-DD/us-market-analysis.md
  │            │            │
  │            │            ├─> [market-news-analyzer]
  │            │            │      └─> reports/YYYY-MM-DD/market-news-analysis.md
  │            │            │            │
  │            └────────────┴────────────┴─> [weekly-trade-blog-writer]
  │                                                └─> blogs/YYYY-MM-DD-weekly-strategy.md
  │                                                      │
  │                                                      ▼
  ├─────────────────────────────────────────────> [strategy-reviewer] <── Required review
  │                                                      │
  │                                                      └─> reports/YYYY-MM-DD/strategy-review.md
  │                                                           │
  │                                                           ├─ PASS -> OK to publish
  │                                                           ├─ PASS WITH NOTES -> Publish with awareness
  │                                                           └─ REVISION REQUIRED -> Correct and re-review
  │
  └─> (Also references previous week's blog)
       blogs/YYYY-MM-DD-weekly-strategy.md (last week)
```

### Medium-Long Term Strategy Report Generation Flow (Optional)

```
reports/YYYY-MM-DD/
  ├─> technical-market-analysis.md ────┐
  ├─> us-market-analysis.md ───────────┼─> [druckenmiller-strategy-planner]
  └─> market-news-analysis.md ─────────┘      └─> reports/YYYY-MM-DD/druckenmiller-strategy.md
                                                       (18-month investment strategy)
```

---

## Troubleshooting

### Agent Can't Find Charts
- Verify `charts/YYYY-MM-DD/` folder exists
- Verify chart image file format is `.jpeg` or `.png`

### Report Not Generated
- Verify `reports/YYYY-MM-DD/` folder exists
- Verify previous step's report was generated successfully

### Blog Post Sector Allocation Changed Drastically
- Verify previous week's blog post exists in `blogs/`
- Verify weekly-trade-blog-writer agent's continuity check function is enabled

### Blog Post Too Long (300+ lines)
- Check length limit in weekly-trade-blog-writer agent definition
- Check line count after generation: `wc -l blogs/YYYY-MM-DD-weekly-strategy.md`

---

## Recommended Workflow

### Sunday Night (JST) or Friday Night (US Time)
1. Prepare charts on weekend
2. Run technical-market-analyst
3. Confirm results before next step

### Monday Morning
4. Run us-market-analyst, market-news-analyzer
5. Review three reports
6. Generate blog with weekly-trade-blog-writer
7. **Quality review with strategy-reviewer (required)**
8. Correct or publish based on review results

---

## Agent Specifications

### technical-market-analyst
- **Skills**: technical-analyst, breadth-chart-analyst, sector-analyst
- **Analysis Targets**: Weekly charts, Breadth indicators, Sector performance
- **Output Format**: Markdown, scenario probabilities

### us-market-analyst
- **Skills**: market-environment-analysis, us-market-bubble-detector, **breadth-chart-analyst**
- **Analysis Targets**: Market phase, Bubble score, Sentiment, **Breadth/Uptrend Ratio (CSV-first)**
- **Output Format**: Markdown, Risk evaluation
- **Important**: Must run `fetch_breadth_csv.py` first (PRIMARY). Chart images are supplementary confirmation only

### market-news-analyzer
- **Skills**: market-news-analyst, economic-calendar-fetcher, earnings-calendar
- **Analysis Targets**: Past 10 days news, Next 7 days events
- **Output Format**: Markdown, Event scenarios
- **Critical**: FOMC/CPI/PCE dates MUST be WebSearch verified (see Known Issues #1)

### weekly-trade-blog-writer
- **Input**: Above 3 reports + Previous week's blog
- **Constraints**: 200-300 lines, Gradual adjustment (±10-15%)
- **Output Format**: Markdown for part-time traders (5-10 min read)

### strategy-reviewer (Required)
- **Skills**: breadth-chart-analyst
- **Role**: Third-party quality assurance review
- **Input**: All chart images (re-read), All reports, Blog post, Previous week's blog
- **Output Format**: Markdown, PASS/PASS WITH NOTES/REVISION REQUIRED judgment
- **Verification Items**: Data accuracy, Uptrend Ratio confirmation, Allocation calculation, Scenario consistency, Continuity, **Economic event dates (see Known Issues #1)**
- **Important**: **Must run** before publishing blog. Uptrend Ratio oversight can be detected by this review
- **Critical**: MUST cross-check FOMC dates with previous week's blog AND Fed official calendar

### druckenmiller-strategy-planner (Optional)
- **Skills**: stanley-druckenmiller-investment
- **Analysis Targets**: 18-month medium-long term macro strategy, Scenario analysis
- **Input**: Above 3 reports (technical, us-market, market-news)
- **Output Format**: Markdown, 4 scenarios (Base/Bull/Bear/Tail Risk), Probabilities and conviction levels
- **Features**: Druckenmiller-style concentrated investment and quick stop-losses, Macro turning point identification
- **Execution Frequency**: Quarterly, or after major events like FOMC

---

## Breadth Data Source & Thresholds

### CSV Data Fetcher (PRIMARY)

```bash
python3 .claude/skills/breadth-chart-analyst/scripts/fetch_breadth_csv.py
```

**CSV Sources**:
| Data | URL |
|------|-----|
| Market Breadth | `https://tradermonty.github.io/market-breadth-analysis/market_breadth_data.csv` |
| Uptrend Ratio | `https://raw.githubusercontent.com/tradermonty/uptrend-dashboard/main/data/uptrend_ratio_timeseries.csv` |
| Sector Summary | `https://raw.githubusercontent.com/tradermonty/uptrend-dashboard/main/data/sector_summary.csv` |

**Data Source Priority**: CSV (PRIMARY) > Chart Image (SUPPLEMENTARY)
OpenCV scripts (`detect_breadth_values.py`, `detect_uptrend_ratio.py`) are **DEPRECATED** (see Issue #7).

### Thresholds

| Indicator | Threshold | Evaluation |
|-----------|-----------|------------|
| **200-day MA** | >=60% | Healthy |
| **200-day MA** | 50-60% | Narrow Rally/Border |
| **200-day MA** | 40-50% | Caution |
| **200-day MA** | <40% | Fragile |
| **8-day MA** | >=73% | Overbought |
| **8-day MA** | 60-73% | Healthy/Bullish |
| **8-day MA** | 40-60% | Neutral |
| **8-day MA** | 23-40% | Bearish |
| **8-day MA** | <23% | Oversold |

### Checklist

1. Run `fetch_breadth_csv.py` → record 200MA, 8MA, Uptrend Ratio values
2. Compare with thresholds above
3. Verify values are consistent across `us-market-analysis.md`, blog, `strategy-review.md`

---

## Known Issues & Lessons Learned

Countermeasures for Issues #1-#7 are implemented in each agent `.md` file. This section consolidates the Prevention Rules.

### Economic Event Date Verification (Issues #1, #2)

Major economic events (FOMC, NFP, ISM PMI, CPI, PCE) must always be verified against official sources.
FMP API is unreliable around holidays. Assumptions based on rules like "first Friday" are also prohibited.

**Official Sources**:
| Event | Official Source |
|-------|-----------------|
| NFP | https://www.bls.gov/schedule/news_release/empsit.htm |
| ISM PMI | https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/ |
| FOMC | https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm |
| CPI | https://www.bls.gov/schedule/news_release/cpi.htm |
| PCE | https://www.bea.gov/news/schedule |

**Rules**:
- Verify against official sources via WebSearch and include URLs in reports
- Dates contradicting previous week's blog → REVISION REQUIRED
- Reviewer must independently verify dates

### Geopolitical Event Check (Issue #3)

- Run individual searches for Tier 1 oil-producing nations (Venezuela, Iran, Libya, Russia, Saudi Arabia)
- Always run a "military action breaking news" search
- Significant events missing from reports → REVISION REQUIRED

### Breadth Data: CSV-First (Issues #4, #5, #7)

OpenCV scripts (`detect_breadth_values.py`, `detect_uptrend_ratio.py`) are **DEPRECATED**.
Image analysis is fragile against chart format changes and caused critical false detections (dead cross false positive, color inversion).

**Current Rule**: Always run `fetch_breadth_csv.py` first as PRIMARY. CSV values override all image-based detections.
- Reviewer must independently fetch and verify CSV data
- |200MA diff| > 2% or |8MA diff| > 5% → REVISION REQUIRED

### US Holiday & Day-of-Week Verification (Issue #6)

Always verify with `calendar.month()` before writing a day of week alongside a date.

**US Market Holidays**:
| Holiday | Rule |
|---------|------|
| MLK Day | January 3rd Monday |
| Presidents Day | February 3rd Monday |
| Memorial Day | May last Monday |
| Independence Day | July 4th (observed) |
| Labor Day | September 1st Monday |
| Thanksgiving | November 4th Thursday |
| Christmas | December 25 (observed) |
| New Year | January 1 (observed) |

**Rule**: Same date with different days of week within the same document → REVISION REQUIRED

### Instrument Notation & Execution Precision (Issue #8)

2026-02-23: 6件の品質問題を手動レビューで検出（strategy-reviewerが見逃し）。

| # | 問題 | Prevention Rule |
|---|------|----------------|
| 1 | ETF名+先物価格の混在 | Monty Style Rule 12 |
| 2 | オプションストライクの桁不整合 | Rule 13 |
| 3 | 同一記事内でETF方針矛盾 | Rule 14 |
| 4 | トリガー時間定義なし | Rule 15 |
| 5 | 確率根拠なし | Rule 15 |
| 6 | ソースURL不足 | Rule 15 |

**Root Cause**: strategy-reviewerのチェックリストにこれらの観点がなかった。
**Fix**: チェックリスト追加 + 3回イテレーティブレビューで検出率向上。

### VIX Data Source Priority (Issue #9)

2026-02-23~27: VIX closing values were consistently reported 1 day late (e.g., reported 18.63 as 2/27 close, actual was 19.86; 18.63 was the 2/26 close).

**Root Cause**: FRED (VIXCLS) updates with a 1-business-day lag, causing the previous day's value to be picked up as the current day's close. WebSearch results frequently return FRED-sourced data.

**Data Source Priority**:
| Priority | Source | Note |
|----------|--------|------|
| 1 (PRIMARY) | **TradingView** (`CBOE:VIX`) | User-verifiable, real-time |
| 2 | **Cboe official** (`cboe.com/tradable-products/vix/`) | Shows Prev Close + Spot |
| 3 (DEPRECATED) | ~~FRED (VIXCLS)~~ | **Prohibited for same-day data**. 1-day update lag |

**Rules**:
- Always cite data source when reporting VIX values (e.g., "VIX 19.86 (TradingView 2/27 close)")
- When VIX values come from WebSearch, verify source URL; if FRED-sourced, note potential 1-day lag
- User-confirmed TradingView values always take highest priority

---

## Version Control

- **Project Version**: 2.1
- **Last Updated**: 2026-02-21
- **Maintenance**: Update this document regularly

---

## Contact & Feedback

Report improvement suggestions or issues related to this workflow to the project's Issue tracker.
