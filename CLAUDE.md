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
- Breadth chart images in `charts/YYYY-MM-DD/` (**must actually read them**)
- Market data (VIX, Breadth, interest rates, etc.)

**Output**:
- `reports/YYYY-MM-DD/us-market-analysis.md`

**Example Command**:
```
Please run comprehensive US market analysis using the us-market-analyst agent.
Reference reports/2025-11-03/technical-market-analysis.md,
and be sure to actually read and analyze the Breadth charts (S&P 500 Breadth Index, Uptrend Stock Ratio)
in charts/2025-11-03/.
Evaluate market environment and bubble risk and save to reports/2025-11-03/us-market-analysis.md.
```

**Analysis Content**:
- Current market phase (Risk-On / Base / Caution / Stress)
- Bubble detection score (0-16 scale)
- **Breadth Index (200-day MA) current value and trend**
- **Uptrend Stock Ratio current value, color (green/red), bottom reversal signal**
- Sector rotation pattern
- Volatility regime

**Important**: Uptrend Stock Ratio is a **leading indicator**. Bottom reversals (red to green transition, rebound from 20% range) often show improvement 1-2 weeks before Breadth 200MA. **Read the actual chart image, not assumptions or past data**.

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
     - QQQ put: 24,000 strike (NVIDIA downside hedge, 12/20 expiry)
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

---

### Step 5 (Required): Strategy Review - Quality Assurance

**Purpose**: Conduct quality assurance review from third-party perspective, detect data misreading, logical contradictions, signal omissions

**Agent**: `strategy-reviewer`

**Input**:
- All chart images in `charts/YYYY-MM-DD/` (**re-reading required**)
- `reports/YYYY-MM-DD/technical-market-analysis.md`
- `reports/YYYY-MM-DD/us-market-analysis.md`
- `reports/YYYY-MM-DD/market-news-analysis.md`
- `blogs/YYYY-MM-DD-weekly-strategy.md` (review target)
- Previous week's blog post (for continuity check)

**Output**:
- `reports/YYYY-MM-DD/strategy-review.md`

**Example Command**:
```
Please review the blog post for the week of 2025-12-01 using the strategy-reviewer agent.
Re-read the charts in charts/2025-12-01/,
verify the quality of blogs/2025-12-01-weekly-strategy.md.
Save review results to reports/2025-12-01/strategy-review.md.
```

**Review Content**:
- **Data Verification**: Re-read chart images, compare with blog values
- **Uptrend Ratio Confirmation**: Check for missed bottom reversal signals (most important)
- **Allocation Calculation Check**: Verify 4 pillars total 100%
- **Scenario Consistency**: Check probabilities and stance match between reports
- **Continuity Check**: Verify ±10-15% gradual adjustment from previous week

**Judgment Results**:
- **PASS**: OK to publish
- **PASS WITH NOTES**: Minor issues, OK to publish with awareness
- **REVISION REQUIRED**: Corrections required, do not publish

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

**Report Structure** (~150-200 lines):
```markdown
# Strategic Investment Outlook - [Date]

## Executive Summary
[2-3 paragraphs: Summary of dominant themes and strategic positioning]

## Market Context & Current Environment
### Macroeconomic Backdrop
[Monetary policy, business cycle, macro indicators current state]

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
- [Q1-Q2 expected development]
- [Q3-Q4 expected development]
**Strategic Positioning:**
- [Asset allocation recommendation]
- [Specific trade ideas with conviction levels]
**Risk Management:**
- [Invalidation signals]
- [Stop-loss/exit criteria]

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
[Indicators to track for scenario validation/invalidation]

## Conclusion & Next Review Date
[Final strategy recommendation and next review timing]
```

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
- **Analysis Targets**: Market phase, Bubble score, Sentiment, **Breadth charts (including Uptrend Ratio)**
- **Output Format**: Markdown, Risk evaluation
- **Important**: Must **actually read** Breadth chart images and identify leading indicators like Uptrend Ratio bottom reversals

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

## Breadth Chart Auto-Detection Tool

### Overview

A Python script that uses OpenCV to automatically detect 200-day MA and 8-day MA values from S&P 500 Breadth Index charts.
Prevents visual reading errors and obtains high-accuracy values.

### Script Location

```
.claude/skills/breadth-chart-analyst/scripts/detect_breadth_values.py
```

### Usage

```bash
# Basic execution (display detection results)
python3 .claude/skills/breadth-chart-analyst/scripts/detect_breadth_values.py charts/YYYY-MM-DD/IMG_XXXX.jpeg

# Debug mode (visually confirm detection results)
python3 .claude/skills/breadth-chart-analyst/scripts/detect_breadth_values.py charts/YYYY-MM-DD/IMG_XXXX.jpeg --debug

# Output in JSON format
python3 .claude/skills/breadth-chart-analyst/scripts/detect_breadth_values.py charts/YYYY-MM-DD/IMG_XXXX.jpeg --json
```

### Example Output

```
============================================================
Breadth Chart Detection Results (OpenCV)
============================================================

Image: charts/2025-12-22/IMG_5499.jpeg
Confidence: HIGH

--- Detected Values ---
200-Day MA: 59.8% (narrow_rally (50-60%))
8-Day MA:   61.9% (healthy_bullish (60-73%))

--- Calibration ---
Red line (0.73) Y-pixel: 377
Blue line (0.23) Y-pixel: 916
Y-scale: -0.0009276437847866419
Calibration successful: True
============================================================
```

### How Detection Works

1. **Y-axis Calibration**: Detect red dotted line (0.73) and blue dotted line (0.23), calculate conversion formula between pixel position and percentage
2. **Green Line (200-day MA) Detection**: Extract green pixels in HSV color space, identify position at right edge
3. **Orange Line (8-day MA) Detection**: Extract orange pixels in HSV color space, identify position at right edge
4. **Value Conversion**: Convert detected pixel positions to percentage values

### Confidence Levels

- **HIGH**: Both reference lines (red/blue) detected, both MA values successfully detected
- **MEDIUM**: Some reference lines or MA values could not be detected
- **LOW**: Using estimated values (when reference lines not detected)
- **FAILED**: Detection failed

### Recommended Workflow

1. **Run Before Chart Analysis**: Get accurate values with this script before LLM analyzes charts
2. **Confirm with Debug Image**: Visually verify detection positions are correct using `--debug` generated image
3. **Reflect in Reports**: Incorporate detection results into us-market-analysis.md and blog posts

### Breadth Chart Reading Checklist (Required)

**Important**: LLM chart reading is error-prone, so the following checklist **must** be executed.

#### 1. Run Auto-Detection Script

```bash
python3 .claude/skills/breadth-chart-analyst/scripts/detect_breadth_values.py charts/YYYY-MM-DD/IMG_XXXX.jpeg --debug
```

#### 2. Confirm Detection Results

- [ ] **Confidence**: Verify it's HIGH
- [ ] **200-Day MA**: Record detected value (e.g., 59.8%)
- [ ] **8-Day MA**: Record detected value (e.g., 61.9%)
- [ ] **Debug Image**: Confirm detection positions are correct in `*_debug_detection.jpeg`

#### 3. Compare with Thresholds

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

#### 4. Reflect in Reports

Accurately reflect detected values in the following files:

- [ ] `reports/YYYY-MM-DD/us-market-analysis.md`
- [ ] `blogs/YYYY-MM-DD-weekly-strategy.md`
- [ ] `reports/YYYY-MM-DD/strategy-review.md` (during review)

#### 5. Consistency Check

- [ ] Verify Breadth values match across all 3 files
- [ ] Verify interpretation based on thresholds (Healthy/Border/Fragile etc.) is correct

---

## Known Issues & Lessons Learned

### Issue #1: FOMC Date Error (2025-12-22)

**Incident Summary**:
- `market-news-analyzer` wrote "12月18日FOMC" (wrong)
- `strategy-reviewer` validated it as "OK" (detection failure)
- Actual FOMC was 12/9-10 (correctly stated in previous week's blog as "12/10 FOMC終了")

**Root Causes**:
1. **Date confusion**: Micron earnings (12/18) was confused with FOMC (12/10)
2. **Source mismatch ignored**: CNBC URL contained `/2025/12/10/` but body text said "12/18"
3. **Previous blog not cross-checked**: Previous week clearly stated "12/10 FOMC終了"
4. **Reviewer assumed correctness**: Did not verify against Fed official calendar

**Countermeasures Implemented**:
1. **market-news-analyzer.md**: Added "Critical Date Verification" section with WebSearch requirement
2. **strategy-reviewer.md**: Added "4.4 Economic Event Date Verification" checklist item
3. **Both agents**: Added "Known Error Pattern" documentation to prevent recurrence

**Prevention Rule**:
```
IF previous_blog says "12/10 FOMC終了"
AND current_blog says different FOMC date
THEN → REVISION REQUIRED (automatic)
```

**Verification Method**:
```bash
# Always verify FOMC dates with:
WebSearch("FOMC [month] [year] meeting date result")
# Cross-check with: federalreserve.gov/monetarypolicy/fomccalendars.htm
```

---

## Version Control

- **Project Version**: 1.2
- **Last Updated**: 2025-12-22
- **Maintenance**: Update this document regularly

---

## Contact & Feedback

Report improvement suggestions or issues related to this workflow to the project's Issue tracker.
