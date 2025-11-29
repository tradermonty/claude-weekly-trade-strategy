# Weekly Trade Strategy Blog - Project Guide (English)

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
   # - S&P 500 Breadth Index (200-day MA + 8-day MA) ← technical-market-analyst skips this
   # - Uptrend Stock Ratio (all markets) ← technical-market-analyst skips this
   ```

2. **Create Report Output Folder**
   ```bash
   mkdir -p reports/2025-11-03
   ```

### Step 1: Technical Market Analysis

**Purpose**: Analyze chart images and evaluate market environment from technical indicators

**Agent**: `technical-market-analyst`

**⚠️ Important Note**: Market Breadth analysis (S&P 500 Breadth Index, Uptrend Ratio) is conducted **separately**. The technical-market-analyst agent **skips** these charts.

**Input**:
- `charts/YYYY-MM-DD/*.jpeg` (all chart images)

**Output**:
- `reports/YYYY-MM-DD/technical-market-analysis.md`

**Example Command**:
```
Analyze this week's (2025-11-03) charts using the technical-market-analyst agent.
Analyze the charts in charts/2025-11-03/.
However, **skip** the following breadth charts (they will be analyzed separately):
- S&P 500 Breadth Index (200-day MA + 8-day MA)
- Uptrend Stock Ratio (all markets)

Save the report to reports/2025-11-03/technical-market-analysis.md.
```

**Analysis Content**:
- VIX, 10Y yield current values and assessment
- Technical analysis of major indices (Nasdaq, S&P500, Russell2000, Dow)
- Commodity trend analysis (gold, copper, oil, uranium)
- Sector rotation analysis
- Scenario-based probability assessment

**Not Analyzed**:
- ❌ S&P 500 Breadth Index - analyzed separately with breadth-chart-analyst skill
- ❌ Uptrend Stock Ratio - analyzed separately with breadth-chart-analyst skill

---

### Step 2: US Market Analysis

**Purpose**: Comprehensive market environment assessment, bubble risk detection, **and detailed Breadth chart analysis**

**Agent**: `us-market-analyst`

**Input**:
- `reports/YYYY-MM-DD/technical-market-analysis.md` (Step 1 results)
- `charts/YYYY-MM-DD/` Breadth chart images (**must be actually read**)
- Market data (VIX, Breadth, interest rates, etc.)

**Output**:
- `reports/YYYY-MM-DD/us-market-analysis.md`

**Example Command**:
```
Execute comprehensive US market analysis using the us-market-analyst agent.
Reference reports/2025-11-03/technical-market-analysis.md,
and make sure to actually read and analyze the Breadth charts (S&P 500 Breadth Index, Uptrend Stock Ratio)
in charts/2025-11-03/.
Assess market environment and bubble risk, and save to reports/2025-11-03/us-market-analysis.md.
```

**Analysis Content**:
- Current market phase (Risk-On / Base / Caution / Stress)
- Bubble detection score (0-16 scale)
- **Breadth Index (200-day MA) current value and trend**
- **Uptrend Stock Ratio current value, color (green/red), bottom reversal signals**
- Sector rotation patterns
- Volatility regime

**⚠️ Important**: Uptrend Stock Ratio is a **leading indicator**. Bottom reversals (red→green transition, bounce from 20% range) often indicate improvement 1-2 weeks before Breadth 200MA. **Read actual chart images, do not estimate or guess.**

---

### Step 3: Market News Analysis

**Purpose**: Analyze news impact from past 10 days and predict events for next 7 days

**Agent**: `market-news-analyzer`

**Input**:
- `reports/YYYY-MM-DD/technical-market-analysis.md` (Step 1 results)
- `reports/YYYY-MM-DD/us-market-analysis.md` (Step 2 results)
- Economic calendar, earnings calendar

**Output**:
- `reports/YYYY-MM-DD/market-news-analysis.md`

**Example Command**:
```
Execute news and event analysis using the market-news-analyzer agent.
Analyze news impact from the past 10 days and important events for the next 7 days,
and save to reports/2025-11-03/market-news-analysis.md.
```

**Analysis Content**:
- Major news from past 10 days and market impact
- Economic indicator schedule for next 7 days
- Major earnings releases (market cap > $2B)
- Event-based scenario analysis (with probabilities)
- Risk event prioritization

---

### Step 4: Weekly Blog Generation

**Purpose**: Integrate 3 reports and generate weekly strategy blog for part-time traders

**Agent**: `weekly-trade-blog-writer`

**Input**:
- `reports/YYYY-MM-DD/technical-market-analysis.md`
- `reports/YYYY-MM-DD/us-market-analysis.md`
- `reports/YYYY-MM-DD/market-news-analysis.md`
- `blogs/` (previous week's blog for continuity check)

**Output**:
- `blogs/YYYY-MM-DD-weekly-strategy.md`

**Example Command**:
```
Create a blog post for the week of November 3, 2025 using the weekly-trade-blog-writer agent.
Integrate the 3 reports in reports/2025-11-03/,
maintain continuity with the previous week's sector allocation,
and save to blogs/2025-11-03-weekly-strategy.md.
```

**Article Structure** (200-300 lines):
1. **3-Line Summary** - Market environment, focus, strategy
2. **This Week's Actions** - Lot management, trade levels, sector allocation, key events
3. **Scenario-Based Plans** - Base/Risk-On/Caution 3 scenarios
4. **Market Status** - Unified triggers (10Y/VIX/Breadth)
5. **Commodity & Sector Tactics** - Gold/Copper/Uranium/Oil
6. **Part-Time Trader Guide** - Morning/Evening checklists
7. **Risk Management** - This week's specific risks
8. **Summary** - 3-5 sentences

**Important Constraints**:
- Sector allocation changes from previous week: **within ±10-15%** (gradual adjustment)
- During all-time highs + Base trigger, avoid drastic position reduction
- Gradually increase cash allocation (e.g., 10% → 20-25% → 30-35%)

**"Monty Style" Guidelines (Mandatory Compliance)**:

To maintain the established "Monty Style" in past blog posts, strictly adhere to the following:

1. **Triggers are Price Reaction-Based**
   - ❌ Bad: "NVIDIA revenue $55B+, Q4 guidance $58B+"
   - ✅ Good: "**NVIDIA post-earnings gap-up +8% or more & new highs**", "**Gap-down -8% or more or 50-day MA break**"
   - Reason: Part-time traders don't have time to read earnings reports. Format for instant decision-making using price and technical levels.

2. **Standardize Indicator Levels**
   - **VIX**: **17** (risk-on) / **20** (Caution) / **23** (Stress) / **26** (panic)
   - **US 10Y Yield**: **4.11%** (lower bound) / **4.36%** (warning) / **4.50%** (red line) / **4.60%** (extreme)
   - **Breadth (above 200-day MA)**: **60%+** (healthy) / **50%** (border) / **40% or less** (fragile)
   - Reason: Maintain consistency with past posts to avoid reader confusion.

3. **Sector Allocation: 4-Pillar Structure**
   - **① Core Indices** (SPY/QQQ/DIA): 40-50%
   - **② Defensive Sectors** (Healthcare + Consumer Staples): 15-25%
   - **③ Themes/Hedges** (Energy + Gold + Commodities): 15-25%
   - **④ Cash/Short-term Bonds** (BIL): 15-30%
   - **Important**: Energy is classified in ③ as "**inflation hedge + opportunistic**", not as a defensive sector
   - Reason: Total 100% allocation is clear at a glance. Easy for readers to use in practice.

4. **Always Include Allocation Reading Example**
   ```
   - For a $100K portfolio:
     - Core indices: $45-50K
     - Defensive (Healthcare $12-15K + Staples $5-8K): $17-23K
     - Themes (Energy $10-12K + Gold $10-12K): $20-24K
     - Cash: $20-25K
   ```
   - Reason: Not just abstract percentages, but concrete dollar examples to aid understanding.

5. **Interpret Breadth Objectively**
   - ❌ Bad: "Breadth at 53% is historically worst-ever"
   - ✅ Good: "Breadth at 53% indicates **narrow rally resumption**. Significantly below the healthy 60%+ level, but not reaching the fragile 40% or less line"
   - Reason: 53% is a middle-range level. Avoid extreme expressions, align with past standards (0.6+: strong, 0.5: border, <0.4: warning).

6. **Hedges Mainly ETF-Based, Options as Supplement**
   - **Main Strategy**: Gold (GLD), Long-term Bonds (TLT), Inverse Indices (SH/SDS), Short-term Bonds (BIL)
   - **Advanced Supplement**: VIX calls, QQQ puts, SPY puts
   - Example notation:
     ```markdown
     ### Advanced Options Strategy (Supplement)

     **Note**: For experienced options traders. ETF hedges above are sufficient for part-time traders.

     - VIX calls: Buy 25 strike before 11/20 earnings (cost 1-2%)
     - QQQ puts: 24,000 strike (NVIDIA downside hedge, 12/20 expiry)
     ```
   - Reason: Many part-time traders have no options experience. Main strategy completes with ETFs.

7. **Part-Time Trader Guide: Price Trigger-Based**
   - ❌ Bad: "Review earnings details, buy more if EPS/revenue beats estimates"
   - ✅ Good:
     ```markdown
     1. **NVIDIA Earnings Deep Dive (11/20 Wed)**:
        - Check gap magnitude (**+8% or more vs -8% or more**)
        - Relationship to 20-week MA ($24,558) and 50-day MA (around $24,000)
        - Confirm if closes at new highs or bearish engulfing
     ```
   - Reason: Format allows decision-making just by checking charts before work or after returning home.

8. **Minimize Operations in Scenario-Based Plans**
   - ❌ Bad: "Core 40-45%→30-35%, Defensive 27-35%→35-40%, Themes 15-20%→10-15%, Cash 20-25%→30-35%" (4 simultaneous changes)
   - ✅ Good: "Change **only 3**: Core, Defensive, Cash"
   - Reason: Part-time traders have limited time. Minimize practical operations.

9. **Keep Allocation Percentages Within 100%**
   - ❌ Bad: "Equities 45-50% + Defensive 18-23% + Themes 15-20% = 78-93% invested, Cash 20-25%" (simple sum appears 98-118%)
   - ✅ Good:
     ```
     Recommended risk allocation: Equities/Commodities total 75-80%, Cash/Short-term bonds 20-25%
     - ① Core indices: 45-50%
     - ② Defensive sectors: 18-23%
     - ③ Themes/Hedges: 15-20%
     - ④ Cash/Short-term bonds: 20-25%

     *Note: ①-③ include overlaps in equity/commodity portions.
     Total portfolio assumes risk asset exposure capped around 75-80%,
     with remaining 20-25% in cash/short-term bonds.
     ```
   - Reason: Prevent reader confusion like "78-93% + 20-25% = 98-118%?". Clarify that 4 pillars include overlaps, with actual total around 75-80%.

10. **Standardize Earnings Timing Notation**
    - ❌ Bad: "AMC (After Market Close)" in event table, but "pre-market release" in morning checklist
    - ✅ Good: "**Released after previous day's close (AMC)**. **Check ±8-10% gap before next morning's open** for scenario determination"
    - Reason: AMC earnings are released after close, so judgment happens pre-market next morning. Standardize timing notation to prevent confusion.

11. **Consolidate ATR References in One Section**
    - ❌ Bad: "ATR 1.6x", "NVDA week 1.2x" scattered across multiple sections
    - ✅ Good:
      - Front section: "Individual stocks: **ATR-based** (see Risk Management section for details)"
      - Risk Management section: "**ATR 1.6x** (-6-8%) for immediate stop loss. **NVIDIA earnings week: 1.2x** (-5-6%) tightened"
    - Reason: Lighter reading flow, with details consolidated in Risk Management section for reference.

---

### Step 5: Strategy Review (Quality Assurance)

**Purpose**: Final quality gate before blog publication - verify that all chart readings are accurate and the strategy correctly reflects market conditions

**Agent**: `strategy-reviewer`

**Input**:
- `charts/YYYY-MM-DD/` (Breadth chart images for re-verification)
- `reports/YYYY-MM-DD/us-market-analysis.md` (Step 2 results)
- `blogs/YYYY-MM-DD-weekly-strategy.md` (Step 4 output)

**Output**:
- `reports/YYYY-MM-DD/strategy-review.md`
- Verdict: PASS / PASS WITH NOTES / REVISION REQUIRED

**Example Command**:
```
Review the weekly strategy blog for 2025-11-03 using the strategy-reviewer agent.
Re-verify the Breadth chart readings in charts/2025-11-03/,
compare against reports/2025-11-03/us-market-analysis.md and blogs/2025-11-03-weekly-strategy.md,
and save the review to reports/2025-11-03/strategy-review.md.
```

**Review Focus Areas**:
1. **Breadth Chart Verification**:
   - Re-read actual Breadth chart images using breadth-chart-analyst skill
   - Verify Uptrend Stock Ratio current value and trend direction
   - Check for bottom reversal signals (red→green transition)
   - Compare against values in us-market-analysis.md

2. **Strategy Consistency Check**:
   - Verify blog strategy aligns with actual chart readings
   - Check that phase assessment (Risk-On/Base/Caution/Stress) matches market data
   - Validate sector allocation against market conditions
   - Confirm scenario probabilities are justified by technical evidence

3. **Verdict Determination**:
   - **PASS**: All chart readings accurate, strategy correctly reflects market conditions
   - **PASS WITH NOTES**: Minor inconsistencies, blog acceptable with noted caveats
   - **REVISION REQUIRED**: Significant discrepancies found, blog must be revised before publication

**⚠️ Critical**: If discrepancies are found between chart readings and strategy, this agent will provide specific correction recommendations.

---

### Step 6 (Optional): Druckenmiller Strategy Planning

**Purpose**: Integrate 3 analysis reports and formulate 18-month medium-to-long-term investment strategy

**Agent**: `druckenmiller-strategy-planner`

**Input**:
- `reports/YYYY-MM-DD/technical-market-analysis.md` (Step 1 results)
- `reports/YYYY-MM-DD/us-market-analysis.md` (Step 2 results)
- `reports/YYYY-MM-DD/market-news-analysis.md` (Step 3 results)
- Previous Druckenmiller strategy report (if exists)

**Output**:
- `reports/YYYY-MM-DD/druckenmiller-strategy.md`

**Example Command**:
```
Formulate an 18-month strategy as of November 3, 2025 using the druckenmiller-strategy-planner agent.
Comprehensively analyze the 3 reports in reports/2025-11-03/,
apply Druckenmiller-style strategic framework,
and save to reports/2025-11-03/druckenmiller-strategy.md.
```

**Analysis Framework**:

1. **Druckenmiller's Investment Philosophy**
   - Macro-focused 18-month forward analysis
   - Position sizing based on conviction level
   - Concentrated investment when multiple factors align
   - Quick stop losses and flexibility

2. **4 Scenario Analysis** (with probabilities)
   - **Base Case** (highest probability scenario)
   - **Bull Case** (optimistic scenario)
   - **Bear Case** (risk scenario)
   - **Tail Risk** (low-probability extreme scenario)

3. **Components of Each Scenario**
   - Key catalysts (policy, economy, geopolitics)
   - Timeline (Q1-Q2, Q3-Q4 developments)
   - Impact by asset class
   - Optimal positioning strategy
   - Invalidation signals (strategy pivot triggers)

**Report Structure** (approx. 150-200 lines):
```markdown
# Strategic Investment Outlook - [Date]

## Executive Summary
[2-3 paragraphs: Summary of dominant themes and strategic positioning]

## Market Context & Current Environment
### Macroeconomic Backdrop
[Monetary policy, business cycle, current macro indicators]

### Technical Market Structure
[Key technical levels, trends, patterns]

### Sentiment & Positioning
[Market sentiment, institutional positioning, contrarian opportunities]

## 18-Month Scenario Analysis

### Base Case Scenario (XX% probability)
**Narrative:** [Most likely market path]
**Key Catalysts:**
- [Catalyst 1]
- [Catalyst 2]
**Timeline Markers:**
- [Q1-Q2 expected developments]
- [Q3-Q4 expected developments]
**Strategic Positioning:**
- [Asset allocation recommendations]
- [Specific trade ideas with conviction levels]
**Risk Management:**
- [Invalidation signals]
- [Stop loss/exit criteria]

### Bull Case Scenario (XX% probability)
[Same structure as Base Case]

### Bear Case Scenario (XX% probability)
[Same structure as Base Case]

### Tail Risk Scenario (XX% probability)
[Same structure as Base Case]

## Recommended Strategic Actions

### High Conviction Trades
[Trades where technical, fundamental, and sentiment align]

### Medium Conviction Positions
[Good risk/reward but lower factor alignment]

### Hedges & Protective Strategies
[Risk management positions and portfolio insurance]

### Watchlist & Contingent Trades
[Setups awaiting confirmation or specific triggers]

## Key Monitoring Indicators
[Tracking indicators for scenario validation/invalidation]

## Conclusion & Next Review Date
[Final strategic recommendation and next review timing]
```

**Key Features**:
- Unlike weekly blog (short-term tactics), this is an **18-month medium-to-long-term strategy**
- Emphasizes structural changes in macro economy and policy inflection points
- Position sizing based on conviction level (High/Medium/Low)
- Each scenario has clear invalidation conditions
- Leverages stanley-druckenmiller-investment skill

**Execution Timing**:
- Quarterly (recommended), or simultaneously with weekly blog
- After major events like FOMC
- At major market structure turning points

**Auto-Generation of Missing Reports**:
If upstream reports (Steps 1-3) don't exist, druckenmiller-strategy-planner automatically invokes missing agents.

---

## Batch Execution Script (Recommended)

```bash
# Set date
DATE="2025-11-03"

# Step 0: Prepare folders
mkdir -p charts/$DATE reports/$DATE

# Example prompt for batch execution of Steps 1-5:
"Create a trade strategy blog for the week of $DATE.

1. technical-market-analyst analyzes all charts in charts/$DATE/
   → reports/$DATE/technical-market-analysis.md

2. us-market-analyst provides comprehensive market environment assessment
   (IMPORTANT: Must read actual Breadth chart images using breadth-chart-analyst skill)
   → reports/$DATE/us-market-analysis.md

3. market-news-analyzer analyzes news/events
   → reports/$DATE/market-news-analysis.md

4. weekly-trade-blog-writer generates final blog post
   → blogs/$DATE-weekly-strategy.md

5. strategy-reviewer performs quality assurance review
   (Re-verifies Breadth chart readings and strategy consistency)
   → reports/$DATE/strategy-review.md

Execute each step sequentially, reviewing reports before proceeding to the next.
Do NOT publish the blog until strategy-reviewer returns PASS verdict."
```

---

## Data Flow Between Agents

### Weekly Blog Generation Flow (5-Step Workflow)

```
charts/YYYY-MM-DD/
  ├─> [Step 1: technical-market-analyst]
  │      └─> reports/YYYY-MM-DD/technical-market-analysis.md
  │            │
  │            ├─> [Step 2: us-market-analyst] ← Also reads Breadth charts directly
  │            │      └─> reports/YYYY-MM-DD/us-market-analysis.md
  │            │            │
  │            │            ├─> [Step 3: market-news-analyzer]
  │            │            │      └─> reports/YYYY-MM-DD/market-news-analysis.md
  │            │            │            │
  │            └────────────┴────────────┴─> [Step 4: weekly-trade-blog-writer]
  │                                                │
  │                                                └─> blogs/YYYY-MM-DD-weekly-strategy.md
  │                                                          │
  │                                                          ▼
  ├────────────────────────────────────────> [Step 5: strategy-reviewer]
  │   (Re-reads Breadth charts)                       │
  │                                                   ├─> reports/YYYY-MM-DD/strategy-review.md
  │                                                   │
  │                                                   ▼
  │                                          PASS → ✅ Ready to Publish
  │                                          REVISION REQUIRED → ⚠️ Revise Blog
  │
  └─> (Also references previous week's blog)
       blogs/YYYY-MM-DD-weekly-strategy.md (last week)
```

### Medium-to-Long-Term Strategy Report Generation Flow (Optional)

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

### Reports Not Generated
- Verify `reports/YYYY-MM-DD/` folder exists
- Verify previous step's report was generated successfully

### Blog Post Sector Allocation Changed Drastically
- Verify previous week's blog post exists in `blogs/`
- Verify weekly-trade-blog-writer agent's continuity check feature is enabled

### Blog Post Too Long (Over 300 Lines)
- Check weekly-trade-blog-writer agent definition's length limit
- Check line count after generation: `wc -l blogs/YYYY-MM-DD-weekly-strategy.md`

---

## Recommended Workflow

### Sunday Night (Japan Time) or Friday Night (US Time)
1. Prepare charts over the weekend
2. Run technical-market-analyst
3. Review results before proceeding to next step

### Monday Morning
4. Run us-market-analyst (ensure Breadth charts are read)
5. Run market-news-analyzer
6. Review all 3 reports
7. Generate blog with weekly-trade-blog-writer
8. Run strategy-reviewer for quality assurance
9. If PASS: Final review and publish
   If REVISION REQUIRED: Revise blog and re-run strategy-reviewer

---

## Detailed Specifications of Each Agent

### technical-market-analyst
- **Skills**: technical-analyst, sector-analyst
- **Analysis Targets**: Weekly charts (VIX, yields, indices, commodities), Sector performance
- **Output Format**: Markdown with scenario-based probabilities
- **Note**: Skips Breadth charts (S&P 500 Breadth Index, Uptrend Ratio) - these are analyzed in Step 2

### us-market-analyst
- **Skills**: market-environment-analysis, us-market-bubble-detector, breadth-chart-analyst
- **Analysis Targets**: Market phase, bubble score, sentiment, **Breadth chart images**
- **Output Format**: Markdown with risk assessment
- **⚠️ Critical**: Must read actual Breadth chart images using breadth-chart-analyst skill. Never estimate or guess Uptrend Stock Ratio values.

### market-news-analyzer
- **Skills**: market-news-analyst, economic-calendar-fetcher, earnings-calendar
- **Analysis Targets**: Past 10 days news, next 7 days events
- **Output Format**: Markdown with event-based scenarios

### weekly-trade-blog-writer
- **Input**: Above 3 reports + previous week's blog
- **Constraints**: 200-300 lines, gradual adjustment (±10-15%)
- **Output Format**: Markdown for part-time traders (5-10 min read)

### strategy-reviewer (Quality Assurance - Mandatory)
- **Skills**: breadth-chart-analyst
- **Analysis Targets**: Re-verify Breadth chart readings, strategy consistency
- **Input**: Breadth charts, us-market-analysis.md, weekly blog
- **Output Format**: Markdown review report with PASS/PASS WITH NOTES/REVISION REQUIRED verdict
- **Purpose**: Final quality gate to catch discrepancies between chart readings and strategy before publication

### druckenmiller-strategy-planner (Optional)
- **Skills**: stanley-druckenmiller-investment
- **Analysis Targets**: 18-month medium-to-long-term macro strategy, scenario analysis
- **Input**: Above 3 reports (technical, us-market, market-news)
- **Output Format**: Markdown, 4 scenarios (Base/Bull/Bear/Tail Risk), with probabilities and conviction levels
- **Features**: Druckenmiller-style concentrated investment and quick stop losses, identifying macro turning points
- **Execution Frequency**: Quarterly, or after major events like FOMC

---

## Version Control

- **Project Version**: 1.1
- **Last Updated**: 2025-11-28
- **Changelog**:
  - v1.1: Added strategy-reviewer agent (Step 5) for quality assurance, updated us-market-analyst to require breadth-chart-analyst skill
  - v1.0: Initial release with 4-step workflow
- **Maintenance**: This document should be updated regularly

---

## Contact & Feedback

For improvement suggestions or issue reports regarding this workflow, please report them to the project's Issue tracker.
