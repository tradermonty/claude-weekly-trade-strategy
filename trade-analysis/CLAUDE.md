# Claude Code Configuration

## Pre-approved Tools and Actions

### Market Analysis & Reporting
- `mcp__finviz__*` - All Finviz market screening and analysis tools
- `mcp__alpaca__*` - All Alpaca trading data and market information tools  
- `mcp__fmp-server__*` - All Financial Modeling Prep API tools
- `WebFetch` for market data sources (finance.yahoo.com, earningswhispers.com, etc.)
- `WebSearch` for market research and analysis

### Report Generation
- `Task` tool with `after-market-reporter` agent for daily market reports
- `Task` tool with `earnings-trade-analyst` agent for earnings analysis
- `Task` tool with `market-environment-strategist` agent for comprehensive market environment analysis
- `Task` tool with `fmp-stock-analyzer` agent for detailed stock fundamental and technical analysis
- `Task` tool with `earnings-analysis-reporter` agent for comprehensive earnings analysis
- `Task` tool with `report-video-generator` agent for creating social media videos from reports
- HTML report generation in `/reports/` directory
- Social media post generation for market updates
- CSV/Excel export for trading data analysis

### File Operations for Reports
- `Write` operations in `/reports/` directory for market analysis outputs
- `Read` operations for analyzing existing market data files
- `Edit` operations for updating report templates and configurations

## Commands
- Market analysis commands can be run without explicit permission
- Report generation workflows are pre-approved for automation
- レポートを作成する前に最初に本日の日付をコマンドラインで確認するようにして date　コマンドで