# Weekly Trade Strategy Blog - プロジェクトガイド

このプロジェクトは、米国株の週間トレード戦略ブログを自動生成するためのシステムです。

---

## プロジェクト構造

```
weekly-trade-strategy/
├── charts/              # チャート画像格納フォルダ
│   └── YYYY-MM-DD/     # 日付ごとのフォルダ
│       ├── chart1.jpeg
│       └── chart2.jpeg
│
├── reports/            # 分析レポート格納フォルダ
│   └── YYYY-MM-DD/    # 日付ごとのフォルダ
│       ├── technical-market-analysis.md
│       ├── us-market-analysis.md
│       └── market-news-analysis.md
│
├── blogs/              # 最終ブログ記事格納フォルダ
│   └── YYYY-MM-DD-weekly-strategy.md
│
└── .claude/
    ├── agents/         # エージェント定義
    └── skills/         # スキル定義
```

## 週間ブログ作成の標準手順

### ステップ0: 準備

1. **チャート画像の配置**
   ```bash
   # 今週の日付でフォルダ作成
   mkdir -p charts/2025-11-03

   # チャート画像を配置（16枚推奨、breadth 2枚は別途分析）
   #
   # Technical Market Analysis対象（14枚）:
   # - VIX (週足)
   # - 米10年債利回り (週足)
   # - Nasdaq 100 (週足)
   # - S&P 500 (週足)
   # - Russell 2000 (週足)
   # - Dow Jones (週足)
   # - 金先物 (週足)
   # - 銅先物 (週足)
   # - 原油 (週足)
   # - 天然ガス (週足)
   # - ウランETF (URA, 週足)
   # - セクターパフォーマンス (1週間)
   # - セクターパフォーマンス (1ヶ月)
   # - 主要銘柄ヒートマップ
   #
   # Market Breadth Analysis対象（2枚、別途分析）:
   # - S&P 500 Breadth Index (200日MA + 8日MA) ← technical-market-analystはスキップ
   # - Uptrend Stock Ratio (全市場) ← technical-market-analystはスキップ
   ```

2. **レポート出力フォルダ作成**
   ```bash
   mkdir -p reports/2025-11-03
   ```

### ステップ1: Technical Market Analysis

**目的**: チャート画像を分析し、テクニカル指標から市場環境を評価

**エージェント**: `technical-market-analyst`

**⚠️ 重要な注記**: Market Breadth分析（S&P 500 Breadth Index, Uptrend Ratio）は**別途実施**されます。technical-market-analystエージェントはこれらのチャートを**スキップ**します。

**入力**:
- `charts/YYYY-MM-DD/*.jpeg` (全チャート画像)

**出力**:
- `reports/YYYY-MM-DD/technical-market-analysis.md`

**実行コマンド例**:
```
今週（2025-11-03）のチャート分析をtechnical-market-analystエージェントで実行してください。
charts/2025-11-03/にあるチャートを分析してください。
ただし、以下のbreadthチャートは**スキップ**してください（別途分析されます）：
- S&P 500 Breadth Index (200日MA + 8日MA)
- Uptrend Stock Ratio (全市場)

レポートをreports/2025-11-03/technical-market-analysis.mdに保存してください。
```

**分析内容**:
- VIX、10年債利回りの現在値と評価
- 主要指数（Nasdaq, S&P500, Russell2000, Dow）のテクニカル分析
- コモディティ（金、銅、原油、ウラン）のトレンド分析
- セクターローテーション分析
- シナリオ別の確率評価

**分析対象外**:
- ❌ S&P 500 Breadth Index - 別途breadth-chart-analystスキルで分析
- ❌ Uptrend Stock Ratio - 別途breadth-chart-analystスキルで分析

---

### ステップ2: US Market Analysis

**目的**: 市場環境の総合評価とバブルリスク検出、**Breadthチャートの詳細分析**

**エージェント**: `us-market-analyst`

**入力**:
- `reports/YYYY-MM-DD/technical-market-analysis.md` (ステップ1の結果)
- `charts/YYYY-MM-DD/` 内のBreadthチャート画像（**必ず実際に読み取ること**）
- 市場データ（VIX, Breadth, 金利等）

**出力**:
- `reports/YYYY-MM-DD/us-market-analysis.md`

**実行コマンド例**:
```
us-market-analystエージェントで米国市場の総合分析を実行してください。
reports/2025-11-03/technical-market-analysis.mdを参照し、
charts/2025-11-03/内のBreadthチャート（S&P 500 Breadth Index, Uptrend Stock Ratio）を
必ず実際に読み取って分析してください。
市場環境とバブルリスクを評価してreports/2025-11-03/us-market-analysis.mdに保存してください。
```

**分析内容**:
- 現在の市場フェーズ（Risk-On / Base / Caution / Stress）
- バブル検出スコア（0-16スケール）
- **Breadth Index（200日MA）の現在値とトレンド**
- **Uptrend Stock Ratioの現在値、色（緑/赤）、底打ち反転シグナル**
- セクターローテーションパターン
- ボラティリティレジーム

**⚠️ 重要**: Uptrend Stock Ratioは**先行指標**。底打ち反転（赤→緑転換、20%台からの反発）は
Breadth 200MAより1-2週間早く改善を示すことが多い。**推測や過去データではなく、実際のチャート画像を読み取ること**。

---

### ステップ3: Market News Analysis

**目的**: 過去10日間のニュース影響分析と今後7日間のイベント予測

**エージェント**: `market-news-analyzer`

**入力**:
- `reports/YYYY-MM-DD/technical-market-analysis.md` (ステップ1の結果)
- `reports/YYYY-MM-DD/us-market-analysis.md` (ステップ2の結果)
- 経済カレンダー、決算カレンダー

**出力**:
- `reports/YYYY-MM-DD/market-news-analysis.md`

**実行コマンド例**:
```
market-news-analyzerエージェントでニュースとイベント分析を実行してください。
過去10日間のニュース影響と今後7日間の重要イベントを分析し、
reports/2025-11-03/market-news-analysis.mdに保存してください。
```

**分析内容**:
- 過去10日間の主要ニュースと市場への影響
- 今後7日間の経済指標スケジュール
- 主要決算発表（時価総額$2B以上）
- イベント別のシナリオ分析（確率付き）
- リスクイベントの優先順位付け

---

### ステップ4: Weekly Blog Generation

**目的**: 3つのレポートを統合し、兼業トレーダー向けの週間戦略ブログを生成

**エージェント**: `weekly-trade-blog-writer`

**入力**:
- `reports/YYYY-MM-DD/technical-market-analysis.md`
- `reports/YYYY-MM-DD/us-market-analysis.md`
- `reports/YYYY-MM-DD/market-news-analysis.md`
- `blogs/` (前週のブログ記事、連続性チェック用)

**出力**:
- `blogs/YYYY-MM-DD-weekly-strategy.md`

**実行コマンド例**:
```
weekly-trade-blog-writerエージェントで2025年11月3日週のブログ記事を作成してください。
reports/2025-11-03/配下の3つのレポートを統合し、
前週のセクター配分との連続性を保ちながら、
blogs/2025-11-03-weekly-strategy.mdに保存してください。
```

**記事構成** (200-300行):
1. **3行まとめ** - 市場環境・焦点・戦略
2. **今週のアクション** - ロット管理、売買レベル、セクター配分、重要イベント
3. **シナリオ別プラン** - Base/Risk-On/Cautionの3シナリオ
4. **マーケット状況** - 統一トリガー（10Y/VIX/Breadth）
5. **コモディティ・セクター戦術** - 金/銅/ウラン/原油
6. **兼業運用ガイド** - 朝/夜チェックリスト
7. **リスク管理** - 今週特有のリスク
8. **まとめ** - 3-5文

**重要な制約**:
- 前週からのセクター配分変更は**±10-15%以内**（段階的調整）
- 史上最高値更新中+Baseトリガーの場合、急激なポジション削減は避ける
- 現金配分は段階的に増加（例: 10% → 20-25% → 30-35%）

**「モンティ節」スタイルガイド（必須遵守）**:

これまでのブログ記事で確立された「モンティ節」スタイルを維持するため、以下の点を厳守してください。

1. **トリガーは価格リアクションベース**
   - ❌ 悪い例: 「NVIDIA売上$55B+、Q4ガイダンス$58B+」
   - ✅ 良い例: 「**NVIDIA決算後+8%以上ギャップアップ & 高値更新**」「**-8%以上ギャップダウン or 50日MA割れ**」
   - 理由: 兼業トレーダーは決算短信を精読する時間がない。価格とテクニカルレベルで即座に判断できる形式にする。

2. **指標水準は標準値に統一**
   - **VIX**: **17**(リスクオン) / **20**(Caution) / **23**(Stress) / **26**(パニック)
   - **米10年債利回り**: **4.11%**(下限) / **4.36%**(警戒) / **4.50%**(レッドライン) / **4.60%**(極端)
   - **Breadth(200日MA上)**: **60%以上**(健全) / **50%**(ボーダー) / **40%以下**(脆弱)
   - 理由: 過去記事との整合性を保ち、読者が混乱しないようにする。

3. **セクター配分は4本柱構造**
   - **① コア指数**(SPY/QQQ/DIA): 40-50%
   - **② 防御セクター**(Healthcare + Consumer Staples): 15-25%
   - **③ テーマ/ヘッジ**(Energy + 金 + コモディティ): 15-25%
   - **④ 現金・短期債**(BIL): 15-30%
   - **重要**: Energyは「防御セクター」ではなく「**インフレヘッジ+オポチュニスティック枠**」として③に分類
   - 理由: 合計100%の配分が一目で理解できる。読者が実務で使いやすい。

4. **配分の読み方(例)を必ず記載**
   ```
   - ポートフォリオ$100Kの場合:
     - コア指数: $45-50K
     - 防御(Healthcare $12-15K + Staples $5-8K): $17-23K
     - テーマ(Energy $10-12K + 金 $10-12K): $20-24K
     - 現金: $20-25K
   ```
   - 理由: 抽象的なパーセントだけでなく、具体的な金額例で理解を助ける。

5. **Breadth解釈は客観的に**
   - ❌ 悪い例: 「Breadth 53%は史上最悪級」
   - ✅ 良い例: 「Breadth 53%は**細いラリー再燃**。60%以上の健全水準は大きく下回るが、40%以下の脆弱ラインには達していない」
   - 理由: 53%は中間的な水準。極端な表現は避け、過去の基準(0.6以上:強い、0.5:ボーダー、0.4未満:警戒)と整合させる。

6. **ヘッジはETFベースがメイン、オプションは補足**
   - **メイン戦略**: 金(GLD)、長期債(TLT)、逆指数(SH/SDS)、短期債(BIL)
   - **上級者向け補足**: VIXコール、QQQプット、SPYプット
   - 記載例:
     ```markdown
     ### 上級者向けオプション戦略(補足)

     **注意**: 以下はオプション取引経験者向け。兼業トレーダーは上記ETFヘッジで十分。

     - VIXコール: 11/20決算前に25ストライク購入(コスト1-2%)
     - QQQプット: 24,000ストライク(NVIDIA下落ヘッジ、12/20満期)
     ```
   - 理由: 兼業トレーダーの多くはオプション取引未経験。メインはETFで完結させる。

7. **兼業運用ガイドは価格トリガーベース**
   - ❌ 悪い例: 「決算内容を確認して、EPS/売上が予想を上回ったら買い増し」
   - ✅ 良い例:
     ```markdown
     1. **NVIDIA決算詳細精査(11/20水)**:
        - ギャップの大きさ(**+8%超 or -8%超**)確認
        - 20週MA($24,558)・50日MA($24,000近辺)との位置関係
        - 引けで高値更新 or 陰線包み込みかの確認
     ```
   - 理由: 朝の出勤前・夜の帰宅後にチャートを見るだけで判断できる形式。

8. **シナリオ別プランの操作量を最小化**
   - ❌ 悪い例: 「コア40-45%→30-35%、防御27-35%→35-40%、テーマ15-20%→10-15%、現金20-25%→30-35%」(4つ同時変更)
   - ✅ 良い例: 「コア・防御・現金の**3本だけ**を変える」
   - 理由: 兼業トレーダーは時間が限られている。実務上の操作量を最小化。

9. **配分パーセンテージは100%以内に収める**
   - ❌ 悪い例: 「株式45-50% + 防御18-23% + テーマ15-20% = 78-93%投資、現金20-25%」(単純合計で98-118%に見える)
   - ✅ 良い例:
     ```
     推奨リスク配分: 株式・コモディティ合計 75-80%、現金・短期債 20-25%
     - ① コア指数: 45-50%
     - ② 防御セクター: 18-23%
     - ③ テーマ/ヘッジ: 15-20%
     - ④ 現金・短期債: 20-25%

     ※注: ①〜③は一部重複を含む株式・コモディティ部分の配分。
     ポートフォリオ全体ではリスク資産エクスポージャー上限を75-80%程度、
     残りを現金・短期債20-25%と想定。
     ```
   - 理由: 「78-93% + 20-25% = 98-118%?」という読者の混乱を防ぐ。4本柱は重複を含むため、実質合計は75-80%程度であることを明示。

10. **決算タイミング表記の統一**
    - ❌ 悪い例: イベント表では「AMC(After Market Close)」なのに、朝チェックでは「寄付き前発表」
    - ✅ 良い例: 「**前日引け後発表(AMC)**。翌朝の**寄付き前に±8-10%ギャップを確認**し、シナリオ判定」
    - 理由: AMC決算は引け後発表なので、判断は翌朝寄付き前。タイミング表記を統一して混乱を防ぐ。

11. **ATR参照は一か所に集約**
    - ❌ 悪い例: 本文の複数箇所に「ATR 1.6倍」「NVDA週は1.2倍」と散在
    - ✅ 良い例:
      - 前半: 「個別銘柄: **ATRベース**(詳細はリスク管理セクション参照)」
      - リスク管理セクション: 「**ATR 1.6倍**(-6-8%)で即座損切り。**NVIDIA決算週は1.2倍**(-5-6%)に縮小」
    - 理由: 読み口が軽くなり、詳細はリスク管理セクションで確認できる構成に。

---

### ステップ5（必須）: Strategy Review - 品質保証レビュー

**目的**: 第三者視点で戦略ブログの品質保証を実施し、データ誤読・論理矛盾・シグナル見落としを検出

**エージェント**: `strategy-reviewer`

**入力**:
- `charts/YYYY-MM-DD/` 内の全チャート画像（**再読み取り必須**）
- `reports/YYYY-MM-DD/technical-market-analysis.md`
- `reports/YYYY-MM-DD/us-market-analysis.md`
- `reports/YYYY-MM-DD/market-news-analysis.md`
- `blogs/YYYY-MM-DD-weekly-strategy.md` (レビュー対象)
- 前週のブログ記事（連続性チェック用）

**出力**:
- `reports/YYYY-MM-DD/strategy-review.md`

**実行コマンド例**:
```
strategy-reviewerエージェントで2025-12-01週のブログ記事をレビューしてください。
charts/2025-12-01/内のチャートを再読み取りし、
blogs/2025-12-01-weekly-strategy.mdの品質を検証してください。
レビュー結果をreports/2025-12-01/strategy-review.mdに保存してください。
```

**レビュー内容**:
- **データ検証**: チャート画像を再読み取りし、ブログ記載値と照合
- **Uptrend Ratio確認**: 底打ち反転シグナルの見落としがないか（最重要）
- **配分計算チェック**: 4本柱が100%になっているか
- **シナリオ整合性**: レポート間で確率・スタンスが一致しているか
- **連続性チェック**: 前週から±10-15%以内の段階的調整か

**判定結果**:
- **PASS**: 公開OK
- **PASS WITH NOTES**: 軽微な問題あり、認識の上で公開可
- **REVISION REQUIRED**: 修正必須、公開不可

**⚠️ 重要**: このステップは**必須**です。ブログ記事を公開する前に必ず実行してください。
今回のUptrend Ratio見落とし問題もこのレビューで検出できます。

---

### ステップ6（オプション）: Druckenmiller Strategy Planning

**目的**: 3つの分析レポートを統合し、18ヶ月の中長期投資戦略を策定

**エージェント**: `druckenmiller-strategy-planner`

**入力**:
- `reports/YYYY-MM-DD/technical-market-analysis.md` (ステップ1の結果)
- `reports/YYYY-MM-DD/us-market-analysis.md` (ステップ2の結果)
- `reports/YYYY-MM-DD/market-news-analysis.md` (ステップ3の結果)
- 前回のDruckenmiller戦略レポート（存在する場合）

**出力**:
- `reports/YYYY-MM-DD/druckenmiller-strategy.md`

**実行コマンド例**:
```
druckenmiller-strategy-plannerエージェントで2025年11月3日時点の18ヶ月戦略を策定してください。
reports/2025-11-03/配下の3つのレポートを総合的に分析し、
Druckenmiller流の戦略フレームワークを適用して、
reports/2025-11-03/druckenmiller-strategy.mdに保存してください。
```

**分析フレームワーク**:

1. **Druckenmillerの投資哲学**
   - マクロ重視の18ヶ月先行分析
   - 確信度に基づくポジションサイジング
   - 複数要因が揃った時の集中投資
   - 素早い損切りと柔軟性

2. **4つのシナリオ分析**（確率付き）
   - **Base Case** (最高確率シナリオ)
   - **Bull Case** (楽観シナリオ)
   - **Bear Case** (リスクシナリオ)
   - **Tail Risk** (低確率の極端シナリオ)

3. **各シナリオの構成要素**
   - 主要カタリスト（政策、景気、地政学）
   - タイムライン（Q1-Q2、Q3-Q4の展開）
   - 資産クラス別の影響
   - 最適ポジショニング戦略
   - 無効化シグナル（戦略転換のトリガー）

**レポート構成** (約150-200行):
```markdown
# Strategic Investment Outlook - [Date]

## Executive Summary
[2-3段落：支配的テーマと戦略的ポジショニングの要約]

## Market Context & Current Environment
### Macroeconomic Backdrop
[金融政策、景気サイクル、マクロ指標の現状]

### Technical Market Structure
[主要テクニカルレベル、トレンド、パターン]

### Sentiment & Positioning
[市場センチメント、機関投資家ポジション、逆張り機会]

## 18-Month Scenario Analysis

### Base Case Scenario (XX% probability)
**Narrative:** [最も可能性の高い市場の道筋]
**Key Catalysts:**
- [カタリスト1]
- [カタリスト2]
**Timeline Markers:**
- [Q1-Q2の予想展開]
- [Q3-Q4の予想展開]
**Strategic Positioning:**
- [資産配分推奨]
- [具体的なトレードアイデアと確信度]
**Risk Management:**
- [無効化シグナル]
- [ストップロス/撤退基準]

### Bull Case Scenario (XX% probability)
[Base Caseと同様の構成]

### Bear Case Scenario (XX% probability)
[Base Caseと同様の構成]

### Tail Risk Scenario (XX% probability)
[Base Caseと同様の構成]

## Recommended Strategic Actions

### High Conviction Trades
[テクニカル、ファンダメンタル、センチメントが揃ったトレード]

### Medium Conviction Positions
[良好なリスク/リワードだが要因の整合性が低いポジション]

### Hedges & Protective Strategies
[リスク管理ポジションとポートフォリオ保険]

### Watchlist & Contingent Trades
[確認待ちまたは特定トリガー待ちのセットアップ]

## Key Monitoring Indicators
[シナリオ検証/無効化のための追跡指標]

## Conclusion & Next Review Date
[最終的な戦略推奨と次回見直し時期]
```

**重要な特徴**:
- 週間ブログ（短期戦術）とは異なり、**18ヶ月の中長期戦略**
- マクロ経済の構造変化や政策転換点を重視
- 確信度に応じたポジションサイジング（High/Medium/Low）
- 各シナリオに明確な無効化条件を設定
- stanley-druckenmiller-investmentスキルを活用

**実行タイミング**:
- 週間ブログと同時（四半期ごと推奨）
- FOMCなど重大イベント後
- 市場構造の大きな転換点

**不足レポートの自動生成**:
上流レポート（ステップ1-3）が存在しない場合、druckenmiller-strategy-plannerは自動的に不足エージェントを呼び出します。

---

## 一括実行スクリプト（推奨）

```bash
# 日付設定
DATE="2025-11-03"

# ステップ0: フォルダ準備
mkdir -p charts/$DATE reports/$DATE

# ステップ1-5を一括実行するプロンプト例：
「$DATE週のトレード戦略ブログを作成してください。

1. technical-market-analystでcharts/$DATE/の全チャートを分析
   → reports/$DATE/technical-market-analysis.md

2. us-market-analystで市場環境を総合評価（Breadthチャート再読み取り含む）
   → reports/$DATE/us-market-analysis.md

3. market-news-analyzerでニュース/イベント分析
   → reports/$DATE/market-news-analysis.md

4. weekly-trade-blog-writerで最終ブログ記事を生成
   → blogs/$DATE-weekly-strategy.md

5. strategy-reviewerで品質レビュー（必須）
   → reports/$DATE/strategy-review.md
   → PASS/PASS WITH NOTES/REVISION REQUIREDを判定

各ステップを順次実行し、レポートを確認してから次に進んでください。
ステップ5でREVISION REQUIREDの場合は、修正後に再レビューしてください。」
```

---

## エージェント間のデータフロー

### 週間ブログ生成フロー

```
charts/YYYY-MM-DD/
  ├─> [technical-market-analyst]
  │      └─> reports/YYYY-MM-DD/technical-market-analysis.md
  │            │
  │            ├─> [us-market-analyst] ←── charts/も再読み取り（breadth-chart-analyst）
  │            │      └─> reports/YYYY-MM-DD/us-market-analysis.md
  │            │            │
  │            │            ├─> [market-news-analyzer]
  │            │            │      └─> reports/YYYY-MM-DD/market-news-analysis.md
  │            │            │            │
  │            └────────────┴────────────┴─> [weekly-trade-blog-writer]
  │                                                └─> blogs/YYYY-MM-DD-weekly-strategy.md
  │                                                      │
  │                                                      ▼
  ├─────────────────────────────────────────────> [strategy-reviewer] ←── 必須レビュー
  │                                                      │
  │                                                      └─> reports/YYYY-MM-DD/strategy-review.md
  │                                                           │
  │                                                           ├─ PASS → 公開OK
  │                                                           ├─ PASS WITH NOTES → 認識の上で公開
  │                                                           └─ REVISION REQUIRED → 修正後再レビュー
  │
  └─> (前週のブログ記事も参照)
       blogs/YYYY-MM-DD-weekly-strategy.md (先週)
```

### 中長期戦略レポート生成フロー（オプション）

```
reports/YYYY-MM-DD/
  ├─> technical-market-analysis.md ────┐
  ├─> us-market-analysis.md ───────────┼─> [druckenmiller-strategy-planner]
  └─> market-news-analysis.md ─────────┘      └─> reports/YYYY-MM-DD/druckenmiller-strategy.md
                                                       (18ヶ月投資戦略)
```

---

## トラブルシューティング

### エージェントがチャートを見つけられない
- `charts/YYYY-MM-DD/` フォルダが存在するか確認
- チャート画像のファイル形式が`.jpeg`または`.png`か確認

### レポートが生成されない
- `reports/YYYY-MM-DD/` フォルダが存在するか確認
- 前のステップのレポートが正常に生成されているか確認

### ブログ記事のセクター配分が急変している
- 前週のブログ記事が`blogs/`に存在するか確認
- weekly-trade-blog-writerエージェントの連続性チェック機能が有効か確認

### ブログ記事が長すぎる（300行超過）
- weekly-trade-blog-writerエージェント定義の長さ制限を確認
- 記事生成後、行数を確認: `wc -l blogs/YYYY-MM-DD-weekly-strategy.md`

---

## 推奨ワークフロー

### 日曜夜（日本時間）または金曜夜（米国時間）
1. 週末にチャートを準備
2. technical-market-analystを実行
3. 結果を確認してから次のステップへ

### 月曜朝
4. us-market-analyst、market-news-analyzerを実行
5. 3つのレポートをレビュー
6. weekly-trade-blog-writerでブログ生成
7. **strategy-reviewerで品質レビュー（必須）**
8. レビュー結果に応じて修正または公開

---

## 各エージェントの詳細仕様

### technical-market-analyst
- **スキル**: technical-analyst, breadth-chart-analyst, sector-analyst
- **分析対象**: 週足チャート、Breadth指標、セクターパフォーマンス
- **出力形式**: Markdown、シナリオ別確率付き

### us-market-analyst
- **スキル**: market-environment-analysis, us-market-bubble-detector, **breadth-chart-analyst**
- **分析対象**: 市場フェーズ、バブルスコア、センチメント、**Breadthチャート（Uptrend Ratio含む）**
- **出力形式**: Markdown、リスク評価
- **重要**: Breadthチャート画像を**実際に読み取り**、Uptrend Ratioの底打ち反転など先行指標を識別すること

### market-news-analyzer
- **スキル**: market-news-analyst, economic-calendar-fetcher, earnings-calendar
- **分析対象**: 過去10日ニュース、今後7日イベント
- **出力形式**: Markdown、イベント別シナリオ

### weekly-trade-blog-writer
- **入力**: 上記3レポート + 前週ブログ
- **制約**: 200-300行、段階的調整（±10-15%）
- **出力形式**: 兼業トレーダー向けMarkdown（5-10分読了）

### strategy-reviewer（必須）
- **スキル**: breadth-chart-analyst
- **役割**: 第三者視点での品質保証レビュー
- **入力**: 全チャート画像（再読み取り）、全レポート、ブログ記事、前週ブログ
- **出力形式**: Markdown、PASS/PASS WITH NOTES/REVISION REQUIREDの判定
- **検証項目**: データ精度、Uptrend Ratio確認、配分計算、シナリオ整合性、連続性
- **重要**: ブログ公開前に**必ず実行**。今回のUptrend Ratio見落としもこのレビューで検出可能

### druckenmiller-strategy-planner（オプション）
- **スキル**: stanley-druckenmiller-investment
- **分析対象**: 18ヶ月中長期マクロ戦略、シナリオ分析
- **入力**: 上記3レポート（technical, us-market, market-news）
- **出力形式**: Markdown、4シナリオ（Base/Bull/Bear/Tail Risk）、確率・確信度付き
- **特徴**: Druckenmiller流の集中投資と素早い損切り、マクロ転換点の識別
- **実行頻度**: 四半期ごと、またはFOMC等の重大イベント後

---

## バージョン管理

- **プロジェクトバージョン**: 1.0
- **最終更新日**: 2025-11-02
- **メンテナンス**: このドキュメントは定期的に更新してください

---

## 連絡先・フィードバック

このワークフローに関する改善提案や問題報告は、プロジェクトのIssueトラッカーに報告してください。
