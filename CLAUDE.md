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

### Issue #2: NFP/ISM PMI Date Error (2025-12-27)

**Incident Summary**:
- `market-news-analyzer` wrote "1/2 NFP" and "1/2 ISM PMI" (wrong)
- `strategy-reviewer` did not catch the error
- Actual: NFP is **1/9**, ISM PMI is **1/5** (holiday-adjusted schedules)

**Root Causes**:
1. **API limitation**: FMP API does not accurately reflect BLS/ISM release schedules around holidays
2. **Assumption error**: Assumed "first Friday" (NFP) and "first business day" (ISM) without checking holiday adjustments
3. **No official source verification**: Did not verify with BLS (bls.gov) or ISM (ismworld.org) official calendars
4. **Reviewer checklist gap**: Section 4.4 only covered FOMC/CPI/PCE, not NFP/ISM PMI

**Countermeasures Implemented**:
1. **market-news-analyzer.md**: Added "Official Source Verification Table" with mandatory URLs for NFP, ISM PMI, FOMC, CPI, PCE
2. **strategy-reviewer.md**: Expanded Section 4.4 to include NFP and ISM PMI verification
3. **economic-calendar-fetcher SKILL.md**: Added "API Limitation Warning" about FMP inaccuracies
4. **Report format requirement**: All major economic events must include official source URL

**Prevention Rule**:
```
FOR major economic events (NFP, ISM PMI, FOMC, CPI, PCE):
  1. WebSearch/WebFetch official source (BLS, ISM, Fed, BEA)
  2. Include official source URL in report
  3. Reviewer must verify URL matches stated date
  4. Do NOT assume "first Friday" or "first business day" during holidays
```

**Official Sources**:
| Event | Official Source |
|-------|-----------------|
| NFP | https://www.bls.gov/schedule/news_release/empsit.htm |
| ISM PMI | https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/ |
| FOMC | https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm |
| CPI | https://www.bls.gov/schedule/news_release/cpi.htm |
| PCE | https://www.bea.gov/news/schedule |

---

### Issue #3: Geopolitical Event Detection Gap (2026-01-03)

**Incident Summary**:
- US military intervention in Venezuela (1/3/2026) NOT detected by market-news-analyzer
- Blog published without geopolitical risk section for this major event
- strategy-reviewer validated as "PASS WITH NOTES" despite missing critical information

**Root Causes**:
1. **Generic WebSearch queries**: "Middle East conflict" doesn't cover Latin America
2. **No country-specific searches**: Venezuela, Iran, Libya not explicitly searched
3. **No breaking news check**: Only analyzed "past 10 days" summary, not recent 48-hour events
4. **Reviewer lacked geopolitical verification**: Only checked economic event dates, not geopolitical events

**Market Impact (Potential)**:
- Oil: HIGH (Venezuela = world's largest oil reserves)
- Gold: HIGH (safe-haven demand)
- VIX: MEDIUM-HIGH (geopolitical uncertainty)
- Equities: MEDIUM (risk-off sentiment)

**Countermeasures Implemented**:
1. **market-news-analyst SKILL.md**: Added country-specific searches for Tier 1 oil producers
2. **market-news-analyzer.md**: Added "Breaking Geopolitical News Check" mandatory step
3. **strategy-reviewer.md**: Added "4.5 Geopolitical Event Verification" section
4. **This documentation**: Record for future reference

**Prevention Rule**:
```
FOR weekly analysis:
  1. Run country-specific searches for: Venezuela, Iran, Libya, Russia, Saudi Arabia
  2. Run "military action breaking news" search
  3. Reviewer must independently verify geopolitical events
  4. If major event found but not in reports → REVISION REQUIRED
```

---

### Issue #4: Uptrend Ratio Detection Gap (2026-01-04)

**Incident Summary**:
- Uptrend Ratio reported as "28-32% GREEN, 回復継続中" (wrong)
- Actual value: **~23% RED, declining trend**
- Error propagated to blog without detection by strategy-reviewer

**Root Causes**:
1. **No OpenCV script for Uptrend Ratio**: `detect_breadth_values.py` only handles S&P 500 Breadth Index (200MA/8MA)
2. **LLM visual analysis unreliable**: Used previous week's data instead of reading new chart
3. **No previous week comparison**: 8% drop (31%→23%) not flagged as unusual
4. **Reviewer didn't verify independently**: Trusted report values without running detection script

**Market Impact**:
- Uptrend Ratio is a **LEADING indicator** (precedes Breadth 200MA by 1-2 weeks)
- Misreading caused incorrect "bullish recovery" assessment when market was warning
- Correct reading: 23% RED = approaching 15% crisis line, requires defensive posture

**Countermeasures Implemented**:
1. **detect_uptrend_ratio.py**: New OpenCV script for Uptrend Ratio detection (TDD-developed)
2. **breadth-chart-analyst SKILL.md**: Added "5.0 MANDATORY: Run Uptrend Ratio Detection Script"
3. **strategy-reviewer.md**: Added "4.6 Uptrend Ratio Independent Verification" section
4. **Previous week comparison**: Change detection (>7% triggers manual verification alert)

**Prevention Rule**:
```
FOR Uptrend Ratio analysis:
  1. MUST run detect_uptrend_ratio.py before LLM analysis
  2. Compare script output vs LLM reading (>5% diff = investigate)
  3. Compare vs previous week (>7% change = manual verify)
  4. Reviewer must independently run detection script
  5. If script color differs from report → REVISION REQUIRED
```

**TDD Implementation**:
- 30 test cases implemented and passing
- Tests cover: class structure, HSV color ranges, Y-axis calibration, current value detection, color detection, trend direction, confidence assessment, error handling
- Test file: `.claude/skills/breadth-chart-analyst/tests/test_detect_uptrend_ratio.py`

---

### Issue #5: Uptrend Ratio Early-Break Bug & Threshold Issue (2026-01-11)

**Incident Summary**:
- Uptrend Ratio script reported as "23.0% RED" (wrong)
- Actual value: **~34.1% GREEN** (confirmed by user inspection)
- Error due to algorithmic bug + inappropriate threshold value

**Root Causes**:
1. **Early-break logic bug**: Line 379-383 stopped at FIRST column with >10 pixels, not the TRUE rightmost column
2. **Threshold too high**: 10-pixel threshold excluded thin GREEN line (6 pixels) at true rightmost position
3. **Column selection order**: RED column (29px, col 1306) was selected before GREEN column (6px, col 1314)

**Detailed Failure Mechanism**:
```
Right-to-left scan (column numbers decreasing):
  Column 1314: GREEN 6px (<10px threshold → skipped)
  Column 1313: GREEN 8px (<10px threshold → skipped)
  Column 1312: GREEN 6px (<10px threshold → skipped)
  ↓
  Column 1306: RED 29px (>10px threshold → SELECTED & BREAK)
  → Result: 23% RED detected (WRONG)
  → Missed: 34.1% GREEN at column 1314 (CORRECT)
```

**Impact**:
- 11.1% underestimation of Uptrend Ratio
- Color inversion (RED instead of GREEN)
- Incorrect bottom reversal signal assessment
- Blog propagated wrong market analysis (bearish instead of bullish recovery)

**Countermeasures Implemented**:
1. **Algorithm Fix**: Replaced early-break with full-scan approach
   - Changed from: `if col_pixels > 10: rightmost_col = col; break`
   - Changed to: Collect all qualified columns, then `rightmost_col = max(colored_cols)`

2. **Threshold Adjustment**: Lowered from 10 pixels to 3 pixels
   - Reasoning: Real charts can have thin lines (4-8px) at rightmost edge
   - 3-pixel minimum still filters out noise while detecting thin lines

3. **New Test Cases**: Added `TestMultiColorRightmostDetection` class
   - `test_rightmost_col_is_maximum_not_first`: Verifies true rightmost selection
   - `test_debug_info_contains_colored_cols_metadata`: Validates new debug fields
   - `test_color_at_true_rightmost_prevails`: Ensures color at rightmost column is detected

4. **Debug Info Enhancement**: Added metadata for troubleshooting
   - `colored_cols_found`: Number of columns with ≥3 pixels
   - `colored_cols_range`: (min, max) of colored column indices

**Modified Files**:
- `.claude/skills/breadth-chart-analyst/scripts/detect_uptrend_ratio.py` (Lines 377-396, 649)
- `.claude/skills/breadth-chart-analyst/tests/test_detect_uptrend_ratio.py` (Added Lines 338-431)

**Test Results**:
- All 33 tests passing (30 existing + 3 new)
- 2026-01-12 chart now correctly detects: **34.1% GREEN** (previously 23.0% RED)
- Confidence: MEDIUM (appropriate for 6-pixel thin line)

**Prevention Rule**:
```
FOR rightmost column detection:
  1. Scan ENTIRE search range (no early break)
  2. Collect ALL columns meeting threshold (≥3 pixels)
  3. Select absolute rightmost: max(colored_cols)
  4. Use low threshold (3px) to detect thin lines
  5. Verify detection with debug image (green circle at rightmost position)
```

**Lessons Learned**:
- Early optimization (early break) caused correctness bug
- Pixel count thresholds must accommodate real chart characteristics
- User visual inspection can be more accurate than automated detection
- Debug visualization (marked images) is critical for validation

---

### Issue #6: US Holiday Day-of-Week Error (2026-01-19)

**Incident Summary**:
- Blog wrote "1/20（月）MLK Day" when actual MLK Day is 1/19（月）
- Same date 1/20 listed as both Monday and Tuesday in the event table
- strategy-reviewer did not detect the contradiction

**Root Causes**:
1. **Day-of-week written by inference**: Did not run `calendar.month(YYYY, MM)` before writing
2. **MLK Day rule miscalculated**: MLK Day = "January 3rd Monday" was not properly computed
3. **No holiday verification step**: No agent definition included US holiday verification
4. **Reviewer blind spot**: strategy-reviewer checked economic dates but not holiday dates

**Affected Lines in Blog**:
```
Line 14: "1/20（月）MLK Day休場" → should be "1/19（月）MLK Day休場"
Line 71: "1/20(月) MLK Day" → should be "1/19(月) MLK Day"
Line 72: "1/20(火) Netflix決算後の反応" → should be "1/21(水) Netflix決算反応"
Line 170: "1/20（月）MLK Day休場" → should be "1/19（月）MLK Day休場"
```

**Countermeasures Implemented**:
1. **strategy-reviewer.md**: Added "4.7 US Holiday and Day-of-Week Verification" section
2. **market-news-analyzer.md**: Added "Holiday Verification" mandatory step
3. **weekly-trade-blog-writer.md**: Added "Phase 0: Calendar Verification" preprocessing
4. **CLAUDE.md**: This documentation for future reference

**US Holiday Rules (Federal Holidays Affecting Market)**:
| Holiday | Rule | Example (2026) |
|---------|------|----------------|
| MLK Day | January 3rd Monday | 1/19（月） |
| Presidents Day | February 3rd Monday | 2/16（月） |
| Memorial Day | May last Monday | 5/25（月） |
| Independence Day | July 4th (observed) | 7/3（金）observed |
| Labor Day | September 1st Monday | 9/7（月） |
| Thanksgiving | November 4th Thursday | 11/26（木） |
| Christmas | December 25 (observed) | 12/25（金） |
| New Year | January 1 (observed) | 1/1（木） |

**Prevention Rule**:
```
BEFORE writing ANY date with day-of-week:
  1. Run: python3 -c "import calendar; print(calendar.month(YYYY, MM))"
  2. Verify day-of-week from the output
  3. For US holidays, calculate from rule (3rd Monday, etc.)
  4. strategy-reviewer MUST independently verify holiday dates
  5. If same date has different day-of-week in document → REVISION REQUIRED
```

**Verification Method**:
```bash
# Verify any month's calendar
python3 -c "import calendar; print(calendar.month(2026, 1))"

# Calculate 3rd Monday (MLK Day) - January 2026
# Mo Tu We Th Fr Sa Su
#           1  2  3  4
#  5  6  7  8  9 10 11
# 12 13 14 15 16 17 18
# 19 20 21 22 23 24 25   ← 19 is 3rd Monday
```

**Lessons Learned**:
- LLM date/day-of-week inference is unreliable
- US holiday rules must be explicitly calculated, not assumed
- Same date with different day-of-week is an obvious contradiction that reviewers must catch
- Calendar tool verification should be mandatory, not optional

---

### Issue #7: Breadth 8MA Dead Cross False Detection via OpenCV (2026-02-16)

**Incident Summary**:
- OpenCV detected Breadth 200MA 60.7%, 8MA 60.0% → "dead cross" reported
- CSV data shows actual values: 200MA **62.26%**, 8MA **67.56%** → **NO dead cross** (8MA >> 200MA)
- Error propagated through us-market-analysis, blog, and strategy-review without detection
- strategy-reviewer validated as "PASS WITH NOTES" despite completely wrong Breadth data

**Error Magnitude**:
| Metric | OpenCV (Wrong) | CSV (Correct) | Error |
|--------|---------------|---------------|-------|
| 200MA | 60.7% | **62.26%** | -1.56pt |
| 8MA | 60.0% | **67.56%** | **-7.56pt** |
| Dead Cross | Yes | **No** | **Completely inverted** |
| Uptrend Ratio | ~32-34% | **33.03% GREEN UP** | Approx correct |

**Root Causes**:
1. **Chart format change**: The chart image format changed, causing OpenCV color/line detection to fail catastrophically
2. **No CSV validation**: No independent data source was used to cross-check OpenCV results
3. **Structural vulnerability**: Entire pipeline depended on fragile image analysis
4. **Reviewer trust**: Strategy reviewer accepted "HIGH confidence" OpenCV output without independent verification

**Impact**:
- Blog reported "Breadth 8MA dead cross" as a key Caution signal (false)
- Bear Case probability influenced by non-existent signal
- Readers received incorrect market assessment (Breadth was actually healthy, not deteriorating)

**Countermeasures Implemented**:
1. **fetch_breadth_csv.py**: New CSV data fetcher (stdlib only, no external deps)
   - Location: `.claude/skills/breadth-chart-analyst/scripts/fetch_breadth_csv.py`
   - Tests: `.claude/skills/breadth-chart-analyst/tests/test_fetch_breadth_csv.py` (50 tests)
2. **Data Source Priority**: CSV (PRIMARY) > Image (SUPPLEMENTARY) > ~~OpenCV~~ (DEPRECATED)
3. **breadth-chart-analyst SKILL.md**: Added Step 0 (CSV fetch before any image analysis)
4. **us-market-analyst.md**: Added Step 0 (CSV fetch as first data gathering step)
5. **strategy-reviewer.md**: Added Phase 1.0 (independent CSV verification)
6. **weekly-trade-blog-writer.md**: Added data source hierarchy, no "~" approximations
7. **Reports/Blog corrected**: All 2026-02-16 files updated with CSV values

**CSV Data Sources**:
| Data | URL |
|------|-----|
| Market Breadth | `https://tradermonty.github.io/market-breadth-analysis/market_breadth_data.csv` |
| Uptrend Ratio | `https://raw.githubusercontent.com/tradermonty/uptrend-dashboard/main/data/uptrend_ratio_timeseries.csv` |
| Sector Summary | `https://raw.githubusercontent.com/tradermonty/uptrend-dashboard/main/data/sector_summary.csv` |

**Prevention Rule**:
```
FOR Breadth analysis:
  1. ALWAYS run fetch_breadth_csv.py FIRST (PRIMARY source)
  2. CSV values override ALL image-based detection
  3. If OpenCV and CSV differ: CSV is correct
  4. Reviewer MUST independently fetch CSV data
  5. |200MA diff| > 2% or |8MA diff| > 5% or dead cross mismatch → REVISION REQUIRED
```

**Lessons Learned**:
- Image-based analysis is structurally fragile (chart format changes are undetectable)
- "HIGH confidence" from OpenCV only measures technical quality, not value accuracy
- Independent data source verification is essential at every pipeline stage
- CSV data provides ground truth that image analysis cannot

---

## Version Control

- **Project Version**: 1.9
- **Last Updated**: 2026-02-16
- **Maintenance**: Update this document regularly

---

## Contact & Feedback

Report improvement suggestions or issues related to this workflow to the project's Issue tracker.
