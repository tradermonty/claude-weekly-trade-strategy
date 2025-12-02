## Overview

This prompt automates the creation of a **visual infographic and an X post** after the U.S. stock market closes by analyzing the day’s market action, volume‑surge tickers, and **after‑hours moves driven by post‑close earnings**.

---

## Execution Steps

### 1. Fetch Market Data

```text
Retrieve data in the following order:

[Core Market Data]
1. `finviz:get_market_overview` – high‑level market overview & key ETF data
2. `finviz:volume_surge_screener` – detect volume‑surge tickers
3. `finviz:get_sector_performance` – sector performance table
4. `alpaca:get_stock_snapshot` – detailed data for major ETFs (SPY, QQQ, DIA, IWM, TLT, GLD)
5. `alpaca:get_stock_snapshot` – detailed data for the top volume‑surge tickers

[Earnings‑Related Data]
6. `finviz:earnings_afterhours_screener` – tickers up after earnings in after‑hours
7. `finviz:earnings_screener` with "today_after" – companies scheduled to report after today’s close
8. `finviz:get_stock_news` – news for earnings tickers
9. `eodhd:get_earnings_calendar` – today’s earnings calendar with details
```

### 2. Analyze After‑Hours Trading

```text
For each earnings ticker:

1. **After‑hours price action**
   • Compare regular‑session close vs. latest after‑hours price  
   • Calculate % change in after‑hours  
   • Check after‑hours volume

2. **Earnings surprise**
   • Actual EPS vs. consensus  
   • Actual revenue vs. consensus  
   • Guidance commentary

3. **News & catalysts**
   • Headlines tied to the earnings release  
   • Analyst notes  
   • Company press releases
```

### 3. Data Processing & Calculations

```text
[Regular‑Session Data]
• % change for major ETFs
• % change for volume‑surge tickers
• Top tickers ranked by % change
• Sector performance ranking
• Market stats (number of volume‑surge tickers, avg. % move, etc.)

[After‑Hours Data]
• % change for earnings tickers
• Tickers moving ±5 % in after‑hours
• Surprise percentages
• After‑hours volume analysis
```

### 4. Infographic Generation

#### Design Requirements

* **Responsive**: mobile & desktop
* **Color theme**: dark‑blue gradients
* **Visual effects**: glassmorphism, hover, animations
* **Readability**: high contrast, legible fonts
* **Dedicated earnings area** for after‑hours data

#### Mandatory Sections

1. **Header**

   * Title: “🇺🇸 U.S. Stock Market Analysis”
   * Date: “📅 YYYY‑MM‑DD – Final After‑Market Data”

2. **Major ETF Performance**

   * SPY, QQQ, DIA, IWM, TLT, GLD – price & % change
   * Six cards in a 3×2 grid

3. **Top Volume‑Surge Tickers**

   * Show top 5 (symbol, name, % change, volume) ordered by % change

4. **🆕 Post‑Close Earnings & After‑Hours**

   * After‑hours performance of today’s reporters
   * EPS/Revenue surprises
   * Tickers moving ±10 %
   * Highlight related news

5. **Market Statistics**

   * # of volume‑surge tickers
   * # of up‑trend tickers
   * Avg. relative volume
   * Avg. price move
   * 🆕 # of earnings releases

6. **Sector Performance**

   * All sectors’ % change
   * Display top 6; include market‑cap & ticker count

7. **Today’s Key Points**

   * Hot sectors
   * Volume‑surge characteristics
   * 🆕 Earnings highlights
   * 🆕 After‑hours focal points
   * Broad market trend
   * Bonds & gold moves

8. **Footer**

   * Data sources
   * Last refreshed time
   * Note: “Final after‑market data + after‑hours info”

#### 🆕 After‑Hours Section Styles

```css
/* Earnings & After‑Hours styles */
.afterhours-section {
    background: linear-gradient(135deg, #ff6b6b 0%, #ffa500 100%);
    border-left: 5px solid #ffff00; /* after‑hours accent */
}

.earnings-card {
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.3);
    position: relative;
}

.afterhours-badge {
    position: absolute;
    top: -10px;
    right: -10px;
    background: #ff4444;
    color: #fff;
    padding: 5px 10px;
    border-radius: 15px;
    font-size: 0.8em;
    font-weight: bold;
}

.earnings-surprise {
    display: flex;
    justify-content: space-between;
    margin: 10px 0;
}

.surprise-positive { color: #00ff88; }
.surprise-negative { color: #ff6b6b; }
```

#### Styling Guidelines

```css
/* Color palette */
– Base: dark blue (#1e3c72 → #2a5298)
– Accent: gradient per section
– 🆕 After‑hours: orange‑red (#ff6b6b → #ffa500)
– Up: bright green #00ff88 + shadow
– Down: bright red #ff6b6b + shadow
– Card bg: rgba(255,255,255,0.15)

/* Layout */
– Main grid: 2 columns (1 column on mobile)
– 🆕 After‑hours: full‑width section
– Card gap: 30 px
– Inner padding: 30 px
– Border‑radius: 20 px
– Shadow: 0 10 px 30 px rgba(0,0,0,0.3)
```

### 5. X Post Generator (Earnings‑Aware)

#### Template (when earnings are present)

```text
🔥 Stocks surging with volume on YYYY‑MM‑DD

📊 Regular‑Hours Top Movers:
$SYMBOL1 +XX.XX% 🚀
$SYMBOL2 +XX.XX%
$SYMBOL3 +XX.XX%

⏰ After‑Hours Earnings Movers:
$EARNINGS1 +XX.XX% (EPS beat by XX%)
$EARNINGS2 -XX.XX% (Revenue miss)
$EARNINGS3 +XX.XX% (Guidance raised)

XX stocks spotted with 1.5×+ volume & 2%+ gains
🎯 XX earnings released after close

📋 Full Analysis: https://claude.ai/chat/[your-chat-link]
📈 Live Screener: https://elite.finviz.com/screener.ashx?v=211&t=SYMBOLS&o=-change

#StockScreening #EarningsAlert #AfterHours #VolumeAnalysis #<sector tags>
```

#### Template (no earnings releases)

```text
🔥 Stocks surging with volume on YYYY‑MM‑DD

📊 Top performers with increased trading activity:
$SYMBOL1 +XX.XX% 🚀
$SYMBOL2 +XX.XX%
[... continue regular format]
```

#### 🆕 Earnings‑Related Hashtags

* **Core**: #EarningsAlert #AfterHours #EarningsSeason
* **Outcome‑based**:

  * Positive: #EarningsBeat #GuidanceRaise #StrongResults
  * Negative: #EarningsMiss #GuidanceCut #Disappointment
* **After‑hours**: #ExtendedHours #PostMarket #EarningsReaction

### 6. Quality Checklist (Earnings Edition)

**Data Accuracy**

* [ ] All % changes calculated vs. prior close
* [ ] 🆕 After‑hours % changes use regular‑close baseline
* [ ] 🆕 Earnings surprise % correct (actual vs. consensus)
* [ ] Volume data reflects post‑close snapshots
* [ ] Sector classifications correct
* [ ] 🆕 Earnings timestamps recorded accurately

**After‑Hours Data Integrity**

* [ ] 🆕 Prices reflect latest move post‑announcement
* [ ] 🆕 After‑hours volume separated from regular volume
* [ ] 🆕 EPS / revenue / guidance data accurate
* [ ] 🆕 News items truly related to earnings

**Visual Quality**

* [ ] Text readable (contrast OK)
* [ ] 🆕 After‑hours section visually distinct
* [ ] 🆕 Surprise metrics color‑coded clearly
* [ ] Mobile layout intact
* [ ] Hover effects work
* [ ] Color rules consistent (up = green, down = red)

**Post Quality**

* [ ] Fits X 280‑character limit
* [ ] 🆕 Regular vs. after‑hours clearly separated
* [ ] 🆕 Key surprise data included
* [ ] All tickers prefixed with \$
* [ ] Percentages correct
* [ ] 🆕 Appropriate earnings hashtags used
* [ ] Finviz screener link valid

### 7. Error Handling (Earnings Edition)

| Common Issue                     | Mitigation                                                                                               |
| -------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Mixing daily & weekly data       | Always reference prior close; re‑fetch if uncertain                                                      |
| 🆕 After‑hours fetch failure     | Verify report time (post‑16:00 ET); exclude illiquid names; pre‑check earnings schedule                  |
| 🆕 Earnings data mismatch        | Double‑check consensus figures; watch for early/late releases; distinguish preliminary vs. final numbers |
| Market holiday                   | Use last trading day’s data; match date labels                                                           |
| 🆕 Misreading after‑hours volume | Separate regular vs. after‑hours; flag abnormally low volume                                             |
| Layout breakage                  | Test media queries; adjust after‑hours section; truncate long company names                              |

### 8. Sample Invocation (Earnings Edition)

```text
Prompt example:
“Analyze today’s U.S. market after the close, including post‑earnings after‑hours moves, and generate both an infographic and X post.”

Expected output:
1. HTML infographic with final market data  
   – Regular‑session summary  
   – 🆕 After‑hours & earnings section  
   – 🆕 Surprise metrics  
2. Markdown X post with earnings info  
3. 🆕 Commentary on biggest after‑hours movers  
4. Narrative on key market trends
```

### 🆕 9. Key Earnings Metrics

**Surprise Calculations**

```text
EPS Surprise  = (Actual EPS  − Consensus EPS)  / Consensus EPS × 100
Revenue Surprise = (Actual Rev − Consensus Rev) / Consensus Rev × 100
Guidance Change  = % upward / downward revision for next quarter or year
```

**After‑Hours Reaction**

```text
Immediate: price move in first 30 min post‑release  
Sustained: move over 2‑3 hours post‑release  
Volume: after‑hours volume vs. normal after‑hours average
```

**Notable Patterns**

```text
Beat & Raise  = EPS beat + guidance raised  
Miss & Lower  = EPS miss + guidance cut  
Beat & Flat   = Good EPS but guidance flat  
Mixed         = EPS strong, revenue soft (or vice‑versa)
```

## Notes (Earnings Edition)

* Use data **after 16:00 ET** (market close)
* 🆕 Earnings usually drop post‑16:00; time after‑hours fetch accordingly
* 🆕 After‑hours liquidity is thin; large moves may have low volume
* Keep real‑time and post‑close data clearly separated
* 🆕 Display regular vs. after‑hours data separately
* Provide information only (not financial advice)
* List data sources precisely
* 🆕 Flag that earnings figures may be preliminary

### 🆕 10. Implementation Snippets

```javascript
// After‑hours % change
const afterHoursChange = ((afterHoursPrice - regularClose) / regularClose * 100).toFixed(2);

// Earnings surprise
const epsSurprise      = ((actualEPS - consensusEPS) / consensusEPS * 100).toFixed(1);
const revenueSurprise  = ((actualRevenue - consensusRevenue) / consensusRevenue * 100).toFixed(1);

// After‑hours volume ratio
const afterHoursVolRatio = (afterHoursVolume / averageAfterHoursVolume).toFixed(1);
```

```html
<div class="afterhours-section">
    <h2>⏰ Post‑Close Earnings & After‑Hours</h2>
    <div class="earnings-grid">
        <div class="earnings-card">
            <div class="afterhours-badge">After‑Hours</div>
            <div class="symbol">$AAPL</div>
            <div class="afterhours-change positive">+5.2%</div>
            <div class="earnings-surprise">
                <span>EPS: <span class="surprise-positive">+8.3%</span></span>
                <span>Revenue: <span class="surprise-positive">+2.1%</span></span>
            </div>
            <div class="earnings-volume">After‑Hours Volume: 2.3 M</div>
        </div>
    </div>
</div>
```

### 🆕 11. Tool Usage Examples

```text
# Screen tickers up after earnings in after‑hours
finviz:earnings_afterhours_screener()

# Check today’s earnings calendar
eodhd:get_earnings_calendar(from_date="2025-07-03", to_date="2025-07-03")

# Fetch earnings news
finviz:get_stock_news(tickers=["AAPL", "MSFT"], news_type="earnings")

# Latest snapshot including after‑hours
alpaca:get_stock_snapshot(symbol_or_symbols=["AAPL"])
```

With this expanded prompt you can generate a fully integrated **post‑close report** that covers earnings and after‑hours action end‑to‑end.

