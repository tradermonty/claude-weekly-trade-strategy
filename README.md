# Weekly Trade Strategy Blog Generator

米国株の週間トレード戦略ブログを自動生成するAIエージェントシステム

[English](#english) | [日本語](#japanese)

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

- **Claude Code CLI** または **Claude Desktop**
- 以下のClaudeスキルが利用可能であること：
  - `technical-analyst`
  - `breadth-chart-analyst`
  - `sector-analyst`
  - `market-environment-analysis`
  - `us-market-bubble-detector`
  - `market-news-analyst`
  - `economic-calendar-fetcher`
  - `earnings-calendar`
  - `stanley-druckenmiller-investment`（中長期戦略用）

### セットアップ

1. **リポジトリのクローン**

```bash
git clone <repository-url>
cd weekly-trade-strategy
```

2. **環境変数の設定**

`.env`ファイルを作成し、必要なAPI キーを設定：

```bash
# Financial Modeling Prep API (決算・経済カレンダー取得用)
FMP_API_KEY=your_api_key_here
```

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
mkdir -p reports/2025-11-03
```

3. **一括実行プロンプト** (Claude Code/Desktop で実行)

```
2025-11-03週のトレード戦略ブログを作成してください。

1. technical-market-analystでcharts/2025-11-03/の全チャートを分析
   → reports/2025-11-03/technical-market-analysis.md

2. us-market-analystで市場環境を総合評価
   → reports/2025-11-03/us-market-analysis.md

3. market-news-analyzerでニュース/イベント分析
   → reports/2025-11-03/market-news-analysis.md

4. weekly-trade-blog-writerで最終ブログ記事を生成
   → blogs/2025-11-03-weekly-strategy.md

各ステップを順次実行し、レポートを確認してから次に進んでください。
```

4. **オプション: 中長期戦略レポート生成**

週間ブログとは別に、18ヶ月の中長期投資戦略レポートを生成できます（四半期ごと推奨）。

```
druckenmiller-strategy-plannerエージェントで2025年11月3日時点の18ヶ月戦略を策定してください。

reports/2025-11-03/配下の3つのレポートを総合的に分析し、
Druckenmiller流の戦略フレームワークを適用して、
reports/2025-11-03/druckenmiller-strategy.mdに保存してください。
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

```
weekly-trade-strategy/
│
├── charts/                          # チャート画像（ユーザーが配置）
│   └── YYYY-MM-DD/
│       ├── vix.jpeg
│       ├── 10year_yield.jpeg
│       └── ...
│
├── reports/                         # 分析レポート（自動生成）
│   └── YYYY-MM-DD/
│       ├── technical-market-analysis.md
│       ├── us-market-analysis.md
│       ├── market-news-analysis.md
│       └── druckenmiller-strategy.md  # (オプション: 中長期戦略)
│
├── blogs/                           # 最終ブログ記事（自動生成）
│   └── YYYY-MM-DD-weekly-strategy.md
│
├── .claude/
│   ├── agents/                      # Claudeエージェント定義（5エージェント）
│   │   ├── technical-market-analyst.md
│   │   ├── us-market-analyst.md
│   │   ├── market-news-analyzer.md
│   │   ├── weekly-trade-blog-writer.md
│   │   └── druckenmiller-strategy-planner.md
│   │
│   └── skills/                      # Claudeスキル定義（9スキル）
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
├── CLAUDE.md                        # 詳細な実行手順ガイド
├── README.md                        # このファイル
├── .env                             # 環境変数 (要作成)
└── .gitignore
```

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

- **Claude Code CLI** or **Claude Desktop**
- The following Claude skills must be available:
  - `technical-analyst`
  - `breadth-chart-analyst`
  - `sector-analyst`
  - `market-environment-analysis`
  - `us-market-bubble-detector`
  - `market-news-analyst`
  - `economic-calendar-fetcher`
  - `earnings-calendar`
  - `stanley-druckenmiller-investment` (for medium-term strategy)

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/tradermonty/weekly-trade-strategy.git
cd weekly-trade-strategy
```

2. **Create `.env` file with your FMP API key**
```bash
echo "FMP_API_KEY=your_api_key_here" > .env
```

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

4. **Run the complete workflow via Claude Code/Desktop**

See the Japanese section above for detailed execution prompts and workflow.

### Project Structure

See the Japanese section above for detailed structure.

### Agents

- **technical-market-analyst**: Chart-based technical analysis
- **us-market-analyst**: Market environment and bubble risk evaluation
- **market-news-analyzer**: News impact and event forecasting
- **weekly-trade-blog-writer**: Final blog post generation
- **druckenmiller-strategy-planner** (Optional): Medium-term (18-month) strategy planning with 4-scenario analysis

### Documentation

- **Workflow Guide**: See `CLAUDE.md` for detailed step-by-step workflow instructions
- **Code Review**: See `CODE_REVIEW.md` for comprehensive codebase review and best practices

### License

This project is licensed under the MIT License.

### Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## Acknowledgments

This project leverages Claude's advanced AI capabilities for financial market analysis. All trading strategies generated are for educational purposes only and should not be considered as financial advice.

---

**Version**: 1.1
**Last Updated**: 2025-11-17

## Recent Updates (v1.1 - 2025-11-17)

- ✅ Added comprehensive "Monty Style" guide with 11 rules for consistent blog formatting
- ✅ Improved allocation percentage clarity (75-80% risk assets vs 20-25% cash)
- ✅ Standardized indicator levels (VIX: 17/20/23/26, 10Y: 4.11/4.36/4.50/4.60)
- ✅ Price-based triggers for better usability by part-time traders
- ✅ Added Druckenmiller-style 18-month strategy report capability
