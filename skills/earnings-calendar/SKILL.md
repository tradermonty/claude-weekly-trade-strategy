# Earnings Calendar Skill

This skill retrieves upcoming earnings announcements using Finviz's relative period selection ("This Week" or "Next Week"), which **avoids date specification errors**.

## Why Finviz over FMP API?

**Problem with date-based APIs (like FMP)**:
- Requires specifying exact dates (e.g., "2025-12-08" to "2025-12-14")
- If the current date is misunderstood, wrong week's data is returned
- Example error: Returning CRWD/MRVL/SNOW (last week) instead of Oracle/Adobe/Broadcom (this week)

**Solution with Finviz**:
- Uses relative periods: "This Week" or "Next Week"
- No date specification required
- Always returns correct relative week's data

## Usage

### Command Line

```bash
# Get next week's earnings (default)
python scripts/fetch_earnings_finviz.py

# Get this week's earnings
python scripts/fetch_earnings_finviz.py --period "This Week"

# Custom market cap filter
python scripts/fetch_earnings_finviz.py --min-cap 5e9

# Output to file
python scripts/fetch_earnings_finviz.py --output earnings.md

# CSV format
python scripts/fetch_earnings_finviz.py --format csv
```

### In Agent Context

When invoked via `Skill(earnings-calendar)`:

1. **Run the Finviz script**:
   ```bash
   python skills/earnings-calendar/scripts/fetch_earnings_finviz.py --period "Next Week"
   ```

2. **Verify against chart image** (if available):
   - Check `charts/YYYY-MM-DD/` for Earnings Whispers screenshot
   - If image exists, cross-reference with Finviz data
   - Image takes precedence if discrepancies exist

## Output Format

The script outputs a Markdown report with:

1. **Earnings by Date** - Grouped by day
2. **Summary Table** - Top 20 by market cap

Example:
```markdown
## Summary (Top 20 by Market Cap)

| Rank | Ticker | Market Cap | Earnings Date | Timing |
|------|--------|------------|---------------|--------|
| 1 | **AVGO** | $1.8T | Dec 11 | AMC |
| 2 | **ORCL** | $620.3B | Dec 10 | AMC |
| 3 | **COST** | $396.5B | Dec 11 | AMC |
| 4 | **ADBE** | $144.9B | Dec 10 | AMC |
```

## Key Companies to Watch

Focus on companies with:
- Market Cap > $50B (mega-cap)
- High sector influence (AVGO for semis, ORCL/ADBE for software)
- Consumer spending indicators (COST, LULU)

## Timing Reference

- **AMC** = After Market Close (report after 4:00 PM ET)
- **BMO** = Before Market Open (report before 9:30 AM ET)

## Dependencies

```bash
pip install finvizfinance pandas
```

## Error Handling

If Finviz data is unavailable:
1. Fall back to Earnings Whispers chart image (if in charts/ folder)
2. Note "data source: image" in report
3. Never guess or use cached data from previous weeks
