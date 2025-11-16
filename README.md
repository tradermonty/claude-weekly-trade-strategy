# Weekly Trade Strategy Blog Generator

An AI agent system that automatically generates weekly trading strategy blog posts for US stock markets using Claude Agents.

[English](#english) | [日本語](#japanese)

---

## <a name="english"></a>English

### Overview

An AI agent system that automatically generates weekly trading strategy blog posts for US stock markets using Claude Agents. The system performs step-by-step chart analysis, market environment evaluation, and news analysis to produce actionable strategy reports for part-time traders.

### Key Features

- **Technical Analysis**: Weekly chart analysis of VIX, yields, breadth indicators, major indices, and commodities
- **Market Environment Assessment**: Bubble risk detection, sentiment analysis, sector rotation analysis
- **News & Event Analysis**: Past 10 days news impact evaluation, upcoming 7 days economic indicators and earnings forecasts
- **Weekly Strategy Blog Generation**: Integrates three analysis reports into a 200-300 line Markdown format trading strategy
- **Medium-Term Strategy Report** (Optional): 18-month Druckenmiller-style investment strategy with 4 scenarios (Base/Bull/Bear/Tail Risk)

### Prerequisites

- **Claude Code CLI** (Required)
  - This project uses `.claude/agents/` feature, which is exclusive to Claude Code
  - Installation: https://docs.claude.ai/claude-code
- **FMP API** (Optional)
  - For automatic earnings and economic calendar retrieval
  - Free plan: 250 requests/day

**Note**: This project does not work with Claude Desktop as it does not support `.claude/agents/`. Please use Claude Code CLI.

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/tradermonty/weekly-trade-strategy.git
cd weekly-trade-strategy
```

2. **Set up environment variables (Optional)**

**FMP API is not required** but recommended for automatic earnings and economic calendar retrieval.

| Feature | Without FMP API | With FMP API |
|---------|----------------|--------------|
| Chart Analysis | ✅ Fully functional | ✅ Fully functional |
| Market Environment | ✅ Fully functional | ✅ Fully functional |
| News Analysis | ⚠️ Partial | ✅ Full |
| Earnings Calendar | ❌ Manual check needed | ✅ Auto-retrieved |
| Economic Calendar | ❌ Manual check needed | ✅ Auto-retrieved |

**To use FMP API** (recommended):

```bash
echo "FMP_API_KEY=your_api_key_here" > .env
```

- Free plan: 250 requests/day (sufficient for weekly analysis)
- Sign up: https://site.financialmodelingprep.com/
- Setup time: ~5 minutes

**To use without FMP API**:

No `.env` file needed. You'll need to manually check earnings and economic calendars.

3. **Prepare chart images** (Recommended: 16 charts)

Create date folder and place weekly chart images:
```bash
mkdir -p charts/2025-11-17
# Add your chart images (.jpeg or .png) to charts/2025-11-17/
```

**Recommended Charts** (Weekly timeframe):
- **Volatility & Rates** (2): VIX, US 10-Year Treasury Yield
- **Major Indices** (4): Nasdaq 100, S&P 500, Russell 2000, Dow Jones
- **Commodities** (5): Gold, Copper, WTI Crude Oil, Natural Gas, Uranium ETF (URA)
- **Sectors** (3): Sector Performance (1-week, 1-month), Industry Performance
- **Breadth** (2, Optional): S&P 500 Breadth Index, Uptrend Stock Ratio

**Chart Sources**: TradingView, FinViz, StockCharts

4. **Run the complete workflow via Claude Code**

Example prompt for weekly blog generation:
```
Create a weekly trade strategy blog for the week of 2025-11-17.

1. Run technical-market-analyst on all charts in charts/2025-11-17/
   → reports/2025-11-17/technical-market-analysis.md

2. Run us-market-analyst for market environment assessment
   → reports/2025-11-17/us-market-analysis.md

3. Run market-news-analyzer for news/event analysis
   → reports/2025-11-17/market-news-analysis.md

4. Run weekly-trade-blog-writer to generate final blog post
   → blogs/2025-11-17-weekly-strategy.md

Execute each step sequentially and verify reports before proceeding to the next step.
```

**Optional: Medium-Term Strategy Report**

Generate an 18-month Druckenmiller-style investment strategy (recommended quarterly):

```
Use druckenmiller-strategy-planner to create an 18-month strategy as of 2025-11-17.

Analyze the 3 reports under reports/2025-11-17/, apply Druckenmiller's strategic framework,
and save to reports/2025-11-17/druckenmiller-strategy.md.
```

Features:
- 18-month forward-looking macro analysis
- 4 scenarios (Base/Bull/Bear/Tail Risk) with probability estimates
- Conviction-based position sizing recommendations
- Identification of macro turning points (monetary policy, economic cycles)
- Clear invalidation conditions for each scenario

### Project Structure

```
weekly-trade-strategy/
│
├── charts/                          # Chart images (user-provided)
│   └── YYYY-MM-DD/
│       ├── vix.jpeg
│       ├── 10year_yield.jpeg
│       └── ...
│
├── reports/                         # Analysis reports (auto-generated)
│   └── YYYY-MM-DD/
│       ├── technical-market-analysis.md
│       ├── us-market-analysis.md
│       ├── market-news-analysis.md
│       └── druckenmiller-strategy.md  # (Optional: medium-term strategy)
│
├── blogs/                           # Final blog posts (auto-generated)
│   └── YYYY-MM-DD-weekly-strategy.md
│
├── .claude/
│   ├── agents/                      # Claude agent definitions (5 agents)
│   │   ├── technical-market-analyst.md
│   │   ├── us-market-analyst.md
│   │   ├── market-news-analyzer.md
│   │   ├── weekly-trade-blog-writer.md
│   │   └── druckenmiller-strategy-planner.md
│   │
│   └── skills/                      # Claude skill definitions (9 skills)
│       ├── technical-analyst/
│       ├── breadth-chart-analyst/
│       ├── sector-analyst/
│       ├── market-environment-analysis/
│       ├── us-market-bubble-detector/
│       ├── market-news-analyst/
│       ├── economic-calendar-fetcher/
│       ├── earnings-calendar/
│       └── stanley-druckenmiller-investment/
│
├── CLAUDE.md                        # Detailed workflow guide
├── README.md                        # This file
├── .env                             # Environment variables (create this)
└── .gitignore
```

### Agents

| Agent | Role | Output |
|-------|------|--------|
| `technical-market-analyst` | Chart-based technical analysis | `technical-market-analysis.md` |
| `us-market-analyst` | Market environment and bubble risk evaluation | `us-market-analysis.md` |
| `market-news-analyzer` | News impact and event forecasting | `market-news-analysis.md` |
| `weekly-trade-blog-writer` | Final blog post generation | `YYYY-MM-DD-weekly-strategy.md` |
| `druckenmiller-strategy-planner` (Optional) | Medium-term (18-month) strategy planning (4-scenario analysis) | `druckenmiller-strategy.md` |

### Troubleshooting

**Q: Agent can't find charts**
- Verify `charts/YYYY-MM-DD/` folder exists
- Ensure image format is `.jpeg` or `.png`

**Q: Reports not generated**
- Check `reports/YYYY-MM-DD/` folder is created
- Verify previous step's report was generated successfully

**Q: Blog sector allocation changes drastically**
- Check previous week's blog exists in `blogs/` directory
- Agents are designed for gradual adjustments (±10-15%)

**Q: FMP API errors**
- Verify `FMP_API_KEY` is correctly set in `.env` file
- Check API key validity at [Financial Modeling Prep](https://site.financialmodelingprep.com/)

### Documentation

- **Workflow Guide**: See `CLAUDE.md` for detailed step-by-step workflow instructions

### License

This project is licensed under the MIT License.

### Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## <a name="japanese"></a>日本語

### 概要

このプロジェクトは、Claude Agentsを活用して、米国株市場の週間トレード戦略ブログを自動生成するシステムです。チャート分析、市場環境評価、ニュース分析を段階的に実行し、兼業トレーダー向けの実践的な戦略レポートを生成します。

### 主な機能

- **テクニカル分析**: VIX、金利、Breadth指標、主要指数、コモディティの週足チャート分析
- **市場環境評価**: バブルリスク検出、センチメント分析、セクターローテーション分析
- **ニュース・イベント分析**: 過去10日間のニュース影響評価、今後7日間の経済指標・決算予測
- **週間戦略ブログ生成**: 3つの分析レポートを統合し、実践的なトレード戦略を200-300行のMarkdown形式で出力
- **中長期戦略レポート**（オプション）: Druckenmiller流の18ヶ月投資戦略を4シナリオ（Base/Bull/Bear/Tail Risk）で生成

### 前提条件

- **Claude Code CLI** (必須)
  - このプロジェクトは`.claude/agents/`機能を使用するため、Claude Code専用です
  - インストール: https://docs.claude.ai/claude-code
- **FMP API** (オプション)
  - 決算・経済カレンダー自動取得に使用
  - 無料プラン: 250リクエスト/日

**注意**: Claude Desktopでは`.claude/agents/`が利用できないため、このプロジェクトは動作しません。Claude Code CLIをご使用ください。

### セットアップ

1. **リポジトリのクローン**

```bash
git clone https://github.com/tradermonty/weekly-trade-strategy.git
cd weekly-trade-strategy
```

2. **環境変数の設定（オプション）**

**FMP APIは必須ではありません**が、今後7日間の決算・経済カレンダーを自動取得するために推奨されます。

| 機能 | FMP APIなし | FMP APIあり |
|------|------------|------------|
| チャート分析 | ✅ 完全動作 | ✅ 完全動作 |
| 市場環境評価 | ✅ 完全動作 | ✅ 完全動作 |
| ニュース分析 | ⚠️ 部分動作 | ✅ 完全動作 |
| 決算カレンダー | ❌ 手動確認必要 | ✅ 自動取得 |
| 経済カレンダー | ❌ 手動確認必要 | ✅ 自動取得 |

**FMP APIを使用する場合**:

`.env`ファイルを作成し、APIキーを設定：

```bash
# Financial Modeling Prep API (決算・経済カレンダー取得用)
FMP_API_KEY=your_api_key_here
```

- 無料プラン: 250リクエスト/日（週間分析には十分）
- 登録: https://site.financialmodelingprep.com/
- 所要時間: 約5分

**FMP APIなしで使用する場合**:

`.env`ファイルの作成は不要です。決算・経済カレンダーは手動で確認してください。

3. **フォルダ構造の確認**

```
weekly-trade-strategy/
├── charts/              # チャート画像格納フォルダ
├── reports/             # 分析レポート格納フォルダ
├── blogs/               # 最終ブログ記事格納フォルダ
├── .claude/
│   ├── agents/          # Claudeエージェント定義（5エージェント）
│   └── skills/          # Claudeスキル定義（9スキル）
├── CLAUDE.md            # 詳細なワークフローガイド
├── README.md            # このファイル
├── .env                 # 環境変数（要作成）
└── .gitignore
```

### 使い方

#### クイックスタート

1. **チャート画像を準備** (推奨16枚)

```bash
# 日付フォルダを作成
mkdir -p charts/2025-11-17

# チャート画像を配置
# 画像形式: .jpeg または .png
# ファイル名: 任意（説明的な名前を推奨）
```

**推奨チャート一覧** (週足チャートを推奨):

**ボラティリティ・金利** (2枚):
- VIX (CBOE Volatility Index) - 週足
- 米10年債利回り (US 10-Year Treasury Yield) - 週足

**主要株価指数** (4枚):
- Nasdaq 100 (週足)
- S&P 500 (週足)
- Russell 2000 (週足)
- Dow Jones Industrial Average (週足)

**コモディティ** (5枚):
- 金先物 (Gold Futures) - 週足
- 銅先物 (Copper Futures) - 週足
- 原油 (WTI Crude Oil) - 週足
- 天然ガス (Natural Gas) - 週足
- ウランETF (URA) - 週足

**セクター・マーケットブレス** (3枚):
- セクターパフォーマンス (1週間) - FinViz等
- セクターパフォーマンス (1ヶ月) - FinViz等
- インダストリーパフォーマンス (1週間または1ヶ月)

**その他** (2枚、オプション):
- S&P 500 Breadth Index (200日MA + 8日MA) - 別途分析
- Uptrend Stock Ratio (全市場) - 別途分析

**チャート取得先の例**:
- TradingView (https://www.tradingview.com/) - カスタマイズ可能な週足チャート
- FinViz (https://finviz.com/) - セクター・インダストリーパフォーマンス
- StockCharts (https://stockcharts.com/) - Breadth指標チャート

**注意**:
- すべて週足（Weekly）チャートを使用
- 画像サイズ: 推奨 1200x800px 以上（読みやすさのため）
- S&P 500 Breadth IndexとUptrend Ratioは別途breadth分析で使用（technical-market-analystではスキップ）

2. **レポートフォルダを作成**

```bash
mkdir -p reports/2025-11-17
```

3. **一括実行プロンプト** (Claude Codeで実行)

```
2025-11-17週のトレード戦略ブログを作成してください。

1. technical-market-analystでcharts/2025-11-17/の全チャートを分析
   → reports/2025-11-17/technical-market-analysis.md

2. us-market-analystで市場環境を総合評価
   → reports/2025-11-17/us-market-analysis.md

3. market-news-analyzerでニュース/イベント分析
   → reports/2025-11-17/market-news-analysis.md

4. weekly-trade-blog-writerで最終ブログ記事を生成
   → blogs/2025-11-17-weekly-strategy.md

各ステップを順次実行し、レポートを確認してから次に進んでください。
```

4. **オプション: 中長期戦略レポート生成**

週間ブログとは別に、18ヶ月の中長期投資戦略レポートを生成できます（四半期ごと推奨）。

```
druckenmiller-strategy-plannerエージェントで2025年11月17日時点の18ヶ月戦略を策定してください。

reports/2025-11-17/配下の3つのレポートを総合的に分析し、
Druckenmiller流の戦略フレームワークを適用して、
reports/2025-11-17/druckenmiller-strategy.mdに保存してください。
```

**特徴**:
- 18ヶ月先行の中長期マクロ分析
- 4つのシナリオ（Base/Bull/Bear/Tail Risk）と確率評価
- 確信度に基づくポジションサイジング推奨
- マクロ転換点（金融政策、景気サイクル）の識別
- 各シナリオの無効化条件を明示

#### ステップ別実行

より詳細な手順は `CLAUDE.md` を参照してください。

### プロジェクト構造

詳細は英語セクションの「Project Structure」を参照してください。

### エージェント一覧

| エージェント | 役割 | 出力 |
|---------|------|------|
| `technical-market-analyst` | チャート画像からテクニカル分析を実行 | `technical-market-analysis.md` |
| `us-market-analyst` | 市場環境とバブルリスクを評価 | `us-market-analysis.md` |
| `market-news-analyzer` | ニュース影響とイベント予測を分析 | `market-news-analysis.md` |
| `weekly-trade-blog-writer` | 3つのレポートを統合してブログ記事を生成 | `YYYY-MM-DD-weekly-strategy.md` |
| `druckenmiller-strategy-planner`（オプション） | 中長期（18ヶ月）戦略プランニング（4シナリオ分析） | `druckenmiller-strategy.md` |

### トラブルシューティング

**Q: エージェントがチャートを見つけられない**
- `charts/YYYY-MM-DD/` フォルダが存在するか確認
- 画像形式が `.jpeg` または `.png` であることを確認

**Q: レポートが生成されない**
- `reports/YYYY-MM-DD/` フォルダが作成されているか確認
- 前のステップのレポートが正常に生成されているか確認

**Q: ブログ記事のセクター配分が急変している**
- 前週のブログ記事が `blogs/` ディレクトリに存在するか確認
- エージェントは段階的調整（±10-15%）を行うよう設計されています

**Q: FMP APIエラーが発生する**
- `.env` ファイルに `FMP_API_KEY` が正しく設定されているか確認
- APIキーの有効性を確認（[Financial Modeling Prep](https://site.financialmodelingprep.com/)）

### ライセンス

このプロジェクトはMITライセンスの下で公開されています。

### 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。

---

## Acknowledgments

This project leverages Claude's advanced AI capabilities for financial market analysis. All trading strategies generated are for educational purposes only and should not be considered as financial advice.

---

**Version**: 1.2
**Last Updated**: 2025-11-17

## Recent Updates

### v1.2 (2025-11-17)
- ✅ Reorganized README: English first, Japanese second
- ✅ Added `.claude/settings.local.json` to enable auto-approval of project tools
- ✅ Fixed market breadth misinterpretation (50-60% is normal, not "worst ever")
- ✅ Added anti-fear-mongering guidelines to prevent sensationalist language
- ✅ Clarified Claude Code CLI is required (not Claude Desktop)
- ✅ Clarified FMP API is optional (not required)

### v1.1 (2025-11-17)
- ✅ Added comprehensive "Monty Style" guide with 11 rules for consistent blog formatting
- ✅ Improved allocation percentage clarity (75-80% risk assets vs 20-25% cash)
- ✅ Standardized indicator levels (VIX: 17/20/23/26, 10Y: 4.11/4.36/4.50/4.60)
- ✅ Price-based triggers for better usability by part-time traders
- ✅ Added Druckenmiller-style 18-month strategy report capability
