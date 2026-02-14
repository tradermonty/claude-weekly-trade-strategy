# 自動トレード実行システム設計書 v2

## Context

週次トレード戦略ブログ（blogs/YYYY-MM-DD-weekly-strategy.md）に基づくトレード実行は現在手動で行っている。兼業トレーダーにとって日中の閾値突破やストップロスへの即時対応が難しい。Claude Agent SDKを活用し、ブログの自然言語戦略を解釈して自動実行するシステムを構築する。

v1レビュー指摘（全10件）を反映: 実行頻度の矛盾、LLMガード不足、市場データ基盤の脆さ、単位正規化、キルスイッチ矛盾、bubble_scorer自動化不可、損失計算定義不足、注文冪等性、スケジューラ耐性、テスト計画の障害系不足。

---

## ユーザー決定事項

| 項目 | 決定 |
|------|------|
| ブローカー | Alpaca（手数料無料、ペーパートレード完備） |
| 自律性 | 完全自動（ペーパートレード検証後） |
| 通知 | メール（Gmail SMTP） |
| 監視頻度 | 15分間隔（市場時間中はルールエンジンで監視、トリガー時のみClaude起動） |
| LLMの役割 | Claude提案→ルールエンジン検証→決定論的注文生成 |
| Breadthデータ | 週次チャート画像OCR継続（日中はブログ記載値を参照） |
| 市場データ | FMP API（VIX/Treasury/指数/コモディティ）+ Alpaca（ETFリアルタイム） |

---

## 1. システムアーキテクチャ

### 1.1 二層監視モデル（v1指摘#1を解決）

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: ルールエンジン監視（15分間隔、9:30-16:00 ET）           │
│  - FMP API: VIX, 10Y利回り, 指数                                │
│  - Alpaca API: ETF価格, ポジション評価額                         │
│  - 決定論的チェック: 閾値突破、ストップロス、ドリフト              │
│  - Claudeは使わない（コストゼロ、遅延なし）                       │
│                                                                  │
│  トリガー発火時のみ ↓                                            │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Claudeエージェント（トリガー時 + 朝6:30 ET定時）        │
│  - ブログ解釈、シナリオ判定、戦略意図(strategy_intent)出力        │
│  - 注文APIは直接呼ばない（v1指摘#2を解決）                       │
│                                                                  │
│  strategy_intent ↓                                               │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: ルールエンジン最終検証 + 決定論的注文生成                │
│  - 許可シンボルリスト検証                                         │
│  - 最大逸脱検証（active scenario配分から±3%以内）                  │
│  - 日次注文上限検証（10注文/日、30%/日）                          │
│  - シナリオ整合検証（提案がブログのシナリオ内か）                  │
│  - プレイベントフリーズ検証                                       │
│  - キルスイッチ最終確認                                           │
│  - client_order_id生成（二重送信防止）（v1指摘#8を解決）          │
│  - 不承認 → ALERT_ONLY（通知+監査ログ、注文なし）                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 データフロー

```
[FMP API]──────┐
  VIX           │
  10Y Yield     │   ┌─────────────────────┐
  S&P/NDX/DJI   ├──→│ Layer 1             │──→ NO_ACTION (95%)
  Gold/Oil/Cu   │   │ ルールエンジン       │
[Alpaca API]───┘   │ (15分間隔)           │──→ TRIGGER_FIRED (5%)
  ETF prices        └────────┬────────────┘         │
  Positions                  │                      ▼
                             │            ┌─────────────────────┐
                             │            │ Layer 2              │
                             │            │ Claude Agent         │
                             │            │ (strategy_intent)    │
                             │            └────────┬────────────┘
                             │                     ▼
                             │            ┌─────────────────────┐
                             │            │ Layer 3              │
                             │            │ Order Validator      │
                             │            │ + Order Generator    │
                             │            └────────┬────────────┘
                             │                     │
                             │         ┌───────────┴───────────┐
                             │         ▼                       ▼
                             │    APPROVED              REJECTED
                             │    → Alpaca注文           → ALERT_ONLY
                             │    → 約定確認              → 監査ログ
                             │    → DB更新                → メール通知
                             ▼
                        [SQLite DB]
                        decisions, trades, market_states
```

---

## 2. 市場データ基盤（v1指摘#3, #4を解決）

### 2.1 データソースと単位正規化

| 指標 | ソース | エンドポイント | 単位 | 正規化後の単位 |
|------|--------|---------------|------|---------------|
| VIX | FMP API | /api/v3/quote/^VIX | ポイント (20.59) | そのまま使用 |
| 10Y利回り | FMP API | /api/v3/treasury | パーセント (4.36 = 4.36%) | そのまま使用 (4.36) |
| S&P 500 | FMP API | /api/v3/quote/^GSPC | 絶対値 (6828.3) | そのまま使用 |
| Nasdaq 100 | FMP API | /api/v3/quote/^NDX | 絶対値 (24700.9) | そのまま使用 |
| Dow | FMP API | /api/v3/quote/^DJI | 絶対値 (49438.0) | そのまま使用 |
| Gold | FMP API | /api/v3/quote/GCUSD | USD/oz (5046.3) | そのまま使用 |
| Oil (WTI) | FMP API | /api/v3/quote/CLUSD | USD/bbl (62.80) | そのまま使用 |
| Copper | FMP API | /api/v3/quote/HGUSD | USD/lb (5.80) | そのまま使用 |
| ETF価格 | Alpaca API | Market Data REST | USD | そのまま使用 |
| ETFポジション | Alpaca API | Trading REST | shares, USD | そのまま使用 |
| Breadth 200MA | ブログ参照値 | blogs/ 内の記載値 | パーセント (60.7) | そのまま使用 |
| Uptrend Ratio | ブログ参照値 | blogs/ 内の記載値 | パーセント (32.0) | そのまま使用 |

単位正規化ルール（コード必須）:

```python
# FMP Treasury APIは year10: 4.36 (=4.36%) を返す
# 閾値比較はそのまま: if yield_10y > 4.50: ...
# 万が一 436.0 等が返った場合のバリデーション:
assert 0.0 < yield_10y < 20.0, f"10Y yield out of range: {yield_10y}"
```

### 2.2 データ取得スケジュール

| タイミング | 取得対象 | ソース | 目的 |
|-----------|---------|--------|------|
| 15分間隔 (9:30-16:00 ET) | VIX, ETF価格, ポジション | FMP + Alpaca | 閾値監視 |
| 朝6:30 ET | 全指標 + 前日終値 | FMP + Alpaca | Claude定時チェック |
| 週末（ブログ作成時） | Breadth, Uptrend Ratio | OpenCVスクリプト | 週次分析 |

### 2.3 データ信頼性保証

```python
class MarketDataValidator:
    """全取得値にバリデーションを適用"""
    VALID_RANGES = {
        "vix": (5.0, 90.0),           # VIX歴史的範囲
        "us10y": (0.0, 20.0),          # 10Y利回り
        "sp500": (1000.0, 20000.0),    # S&P 500
        "nasdaq": (3000.0, 50000.0),   # Nasdaq 100
        "gold": (500.0, 10000.0),      # Gold USD/oz
    }

    def validate(self, indicator: str, value: float) -> bool:
        low, high = self.VALID_RANGES[indicator]
        return low <= value <= high

    # FMP API失敗時: 前回値を保持し、ALERT_ONLY通知（フォールバックなし）
    # yfinanceはバックアップソースとして使用しない（v2指摘#7を解決）
    # 理由: 依存を最小化し、障害時は「安全側に停止」を原則とする

    # エスカレーションポリシー（v4指摘#3を解決）:
    # 古い値で監視継続するリスクを制限するため、段階的に格上げ
    STALE_ESCALATION = {
        "warn":  3,    # カウンタ>=3 → ALERT_ONLY（前回値保持で監視継続）
        "halt":  6,    # カウンタ>=6 → HALT_AND_NOTIFY（全取引停止）
    }
    # 所要時間の目安（v9指摘#2: +2加算を考慮）:
    #   片方のみ失敗(+1/回): warn=45分、halt=90分
    #   両方同時失敗(+2/回): warn=最短23分、halt=最短45分
    # 回復時: 成功1回で失敗カウンタリセット、HALT解除は手動確認後
    #
    # API失敗カウンタの管理（v7指摘#4, v8指摘#4を解決）:
    # 更新元: market_monitor.py の fetch_market_data() 内
    # 永続化: SQLite state テーブル (key="consecutive_api_failures", value=int)
    #
    # ソース別重み付け:
    #   FMP失敗（VIX/指数/コモディティ） → +1（クリティカル: 閾値判定の基盤）
    #   Alpaca失敗（ETF価格/ポジション） → +1（クリティカル: 注文生成の基盤）
    #   FMP+Alpaca両方失敗 → +2（市場データ全喪失）
    #   FMP Treasury失敗（日次更新） → +0（次回日次更新まで前日値で代替可）
    #
    # インクリメント: 15分チェック毎にクリティカルソース失敗なら加算
    # リセット: 全クリティカルソース成功時に 0 にリセット
    # 参照: KillSwitch.check() が self.state.consecutive_api_failures で読み取り
```

### 2.4 データ鮮度規約（v2指摘#6を解決）

```python
class DataFreshnessPolicy:
    """データのタイムスタンプと鮮度を管理"""

    # 各ソースの許容遅延（秒）
    MAX_STALENESS = {
        "fmp_quote": 300,        # FMP quote: 5分以内
        "fmp_treasury": 86400,   # FMP treasury: 24時間以内（日次データ）
        "alpaca_position": 60,   # Alpacaポジション: 1分以内
        "alpaca_quote": 120,     # Alpaca ETF quote: 2分以内
    }

    def is_fresh(self, source: str, timestamp: datetime) -> bool:
        """データが許容遅延内かチェック"""
        age_seconds = (datetime.now(timezone.utc) - timestamp).total_seconds()
        return age_seconds <= self.MAX_STALENESS[source]

    def resolve_conflict(self, fmp_data, alpaca_data) -> dict:
        """FMPとAlpacaで値が異なる場合の優先ルール（v9指摘#3: 仕様明文化）

        入力:
          fmp_data: {"vix": 20.5, "us10y": 4.36, "sp500": 6828, ...} or None（失敗時）
          alpaca_data: {"SPY": 683.1, "QQQ": 531.2, ..., "positions": {...}} or None

        出力:
          {"vix": 20.5, "us10y": 4.36, "sp500": 6828, "SPY": 683.1, ...}

        優先ルール:
        1. VIX, 10Y利回り, 指数, コモディティ → FMPのみ（Alpacaに同等データなし）
        2. ETF価格 → Alpaca優先（取引と同一ソースで整合性確保）
        3. ポジション/評価額 → Alpaca（信頼の唯一ソース）

        欠損時の処理:
        - FMP失敗: VIX/指数/コモディティは前回値を返す（stateテーブルから）
        - Alpaca失敗: ETF価格/ポジションは前回値を返す
        - 前回値もない（初回起動等）: 該当フィールドをNoneとし、
          ルールエンジンはNoneフィールドに依存するチェックをスキップ
        """
        result = {}
        # FMPソース（VIX/指数/コモディティ）
        fmp_keys = ["vix", "us10y", "sp500", "nasdaq", "dow", "gold", "oil", "copper"]
        for key in fmp_keys:
            result[key] = (fmp_data or {}).get(key) or self.get_previous(key)
        # Alpacaソース（ETF価格/ポジション）
        alpaca_keys = list(self.ALLOWED_SYMBOLS)
        for key in alpaca_keys:
            result[key] = (alpaca_data or {}).get(key) or self.get_previous(key)
        result["positions"] = (alpaca_data or {}).get("positions") or self.get_previous("positions")
        return result

    # セッション別鮮度規約（v3指摘#5を解決）:
    # - 市場時間中(9:30-16:00): fmp_quote <= 5分、alpaca_quote <= 2分
    # - プレマーケット(6:30): 前日終値を「正」とする。stale判定しない。
    #   fmp_quoteのtimestampが前日16:00台なら正常（市場外データ）
    # - ポストマーケット(16:00最終チェック): 当日終値。fmp_quoteが当日16:00台なら正常
    #
    # 5分以上古いデータで閾値判定を行う場合:
    # - NO_ACTION判定 → 許可（安全側）
    # - TRIGGER_FIRED判定 → 最新データ再取得を試み、失敗時はTRIGGER保留+ALERT通知
```

---

## 3. コンポーネント詳細設計

### 3.0 ストップロスの即応設計（v2指摘#3を解決）

15分ポーリングの限界: 急落・ギャップで最大15分遅延。ストップロスは唯一の時間最優先要件。

**解決策: Alpacaサーバーサイド逆指値注文の常設**

```python
class StopLossManager:
    """ブログの売買レベルをAlpacaサーバーサイド逆指値として常設"""

    def sync_stop_orders(self, strategy_spec, portfolio):
        """ブログ更新時（週1回）にAlpacaの逆指値を同期

        ブログの "今週の売買レベル > ストップロス" から:
        - S&P 500: 6,685 → SPYの対応価格で逆指値
        - Nasdaq:  23,758 → QQQの対応価格で逆指値
        - Dow:     47,064 → DIAの対応価格で逆指値

        これらはAlpacaサーバー上で常時有効（システム停止中も発動）。
        呼び出し元: 週次(ブログ更新時) + resync_after_fill_or_rebalance()
        """
        # 先に孤立ストップを掃除（v8指摘#3: 常時保証）
        self._cleanup_orphaned_stops(portfolio)
        # Alpaca PATCH /v2/orders/{id} (replace_order) でアトミック置換（v5指摘#2を解決）
        # 二重発火リスク回避: 旧ストップを新条件で上書き（常に1注文のみ有効）
        for symbol, position in portfolio.positions.items():
            stop_price = self._index_to_etf_stop(symbol, strategy_spec.stop_losses)
            if stop_price:
                # 複数ストップの異常系処理（v6指摘#3を解決）
                existing_stops = self.alpaca.list_open_stop_orders(symbol)
                seq = self._next_seq(symbol, strategy_spec.blog_date)
                new_id = f"stop_{symbol}_{strategy_spec.blog_date}_{seq}"

                if len(existing_stops) == 1:
                    # 正常系: アトミック置換
                    try:
                        self.alpaca.replace_order(
                            order_id=existing_stops[0].id,
                            qty=position.shares,
                            stop_price=stop_price,
                            client_order_id=new_id,
                        )
                    except AlpacaAPIError as e:
                        # replace失敗フォールバック（v6指摘#2を解決）
                        # 原因: 約定済み、部分約定、状態不整合等
                        self._handle_replace_failure(symbol, position, stop_price, new_id, existing_stops[0].id, e)
                elif len(existing_stops) > 1:
                    # 異常系: 複数ストップ残存 → 全キャンセル後に新規設定
                    self.notify.alert(f"Multiple stops found for {symbol}: {len(existing_stops)}")
                    for old in existing_stops:
                        self.alpaca.cancel_order(old.id)
                    self.alpaca.submit_order(
                        symbol=symbol, qty=position.shares, side="sell",
                        type="stop", stop_price=stop_price,
                        time_in_force="gtc", client_order_id=new_id,
                    )
                else:
                    # 初回設定 or ストップ約定後の新規作成
                    self.alpaca.submit_order(
                        symbol=symbol, qty=position.shares, side="sell",
                        type="stop", stop_price=stop_price,
                        time_in_force="gtc", client_order_id=new_id,
                    )

    def _handle_replace_failure(self, symbol, position, stop_price, new_id, old_order_id, error):
        """replace_order失敗時のフォールバック（v6指摘#2を解決）

        1. 旧注文IDで現在状態を再取得（v7指摘#3: order_idベースで一意特定）
        2. filled/partially_filled → 新規submitのみ（旧は約定済み）
        3. canceled/expired → 新規submitのみ
        4. それ以外 → ALERT_ONLY通知（手動確認を促す）
        """
        old_order = self.alpaca.get_order(old_order_id)
        old_status = old_order.status
        if old_status == "partially_filled":
            # v8指摘#2: 残数量をまずcancel（二重ストップ防止）
            self.alpaca.cancel_order(old_order_id)
        if old_status in ("filled", "partially_filled", "canceled", "expired"):
            # v9指摘#1: 古いportfolioを使わず、Alpacaから最新ポジションを再取得
            current_pos = self.alpaca.get_position(symbol)
            if current_pos and float(current_pos.qty) > 0:
                self.alpaca.submit_order(
                    symbol=symbol, qty=float(current_pos.qty), side="sell",
                    type="stop", stop_price=stop_price,
                    time_in_force="gtc", client_order_id=new_id + "_retry",
                )
            # ポジションなし（全量約定済み）→ 新ストップ不要
        else:
            self.notify.critical(
                f"Stop replace failed for {symbol}: {error}. "
                f"Old order status: {old_status}. Manual review required."
            )

    def _next_seq(self, symbol: str, blog_date: str) -> int:
        """seq番号の生成と永続化（v5指摘#3を解決）

        SQLiteテーブル stop_seq に (symbol, blog_date, seq) を保存。
        同一(symbol, blog_date)に対してINSERT時にseq+1を返す。
        blog_dateが変わると（新しいブログ）seq=0にリセット。
        """
        return self.db.increment_stop_seq(symbol, blog_date)

    def resync_after_fill_or_rebalance(self, portfolio, strategy_spec):
        """通常注文約定後にストップ注文の数量を再同期（v3指摘#3を解決）

        トリガー:
        - Layer 3のリバランス注文が約定した後
        - 手動取引がAlpaca側で検出された後
        - ストップ注文が部分約定した後

        処理: replace_orderでアトミック置換（二重発火なし）
        """
        self.sync_stop_orders(strategy_spec, portfolio)
        self._cleanup_orphaned_stops(portfolio)

    def _cleanup_orphaned_stops(self, portfolio):
        """保有がなくなった銘柄のストップ注文を掃除（v7指摘#2を解決）

        ポジション売却後にGTCストップが残ると、再購入時に不要約定→
        意図しないショート化のリスク。全GTC stop注文を走査し、
        ポートフォリオに存在しない銘柄の注文をキャンセル。
        """
        all_stops = self.alpaca.list_all_open_stop_orders()
        held_symbols = set(portfolio.positions.keys())
        for stop in all_stops:
            if stop.symbol not in held_symbols:
                self.alpaca.cancel_order(stop.id)
                self.notify.info(f"Orphaned stop canceled: {stop.symbol} (no position)")
```

**結果**: ストップロスはブローカー常設（遅延ゼロ）。15分ポーリングはVIX/ドリフト/シナリオ変更の検知に専念。

### 3.0.1 指数→ETF価格変換（v4指摘#4を解決）

ブログの売買レベルは指数ベース（S&P 500: 6,685等）だが、実際の注文はETF（SPY等）で行う。変換ロジックを厳密に定義:

```python
class IndexToETFConverter:
    """指数レベル → ETF価格の変換"""

    # 基準比率: ETF価格 / 指数値（おおよそ1/10だが、正確な比率は毎日更新）
    # 例: SPY ≈ S&P 500 / 10, QQQ ≈ Nasdaq 100 / 40, DIA ≈ Dow / 100

    def calc_ratio(self, etf_price: float, index_value: float) -> float:
        """当日の終値ペアから変換比率を算出"""
        return etf_price / index_value

    def convert(self, index_level: float, ratio: float) -> float:
        """指数レベルをETF価格に変換"""
        return round(index_level * ratio, 2)

    def daily_calibration(self, market_data) -> dict:
        """毎日9:30 ETにFMP指数値 + Alpaca ETF価格から比率を再計算

        例（2026-02-16時点）:
        - SPY $683.10 / ^GSPC 6,828.30 → ratio = 0.10004
        - QQQ $531.20 / ^NDX 21,704.10 → ratio = 0.02447
        - DIA $441.30 / ^DJI 44,546.00 → ratio = 0.009907

        保存先: SQLite calibration テーブル（日付, symbol, ratio）
        """
        ratios = {}
        pairs = [
            ("SPY", "^GSPC"), ("QQQ", "^NDX"), ("DIA", "^DJI")
        ]
        for etf, index in pairs:
            etf_price = market_data.alpaca_quote(etf)
            index_value = market_data.fmp_quote(index)
            ratios[etf] = self.calc_ratio(etf_price, index_value)
        return ratios

    # 許容誤差: 変換後のETF価格と実際のETF価格の乖離が0.5%以上なら
    # ALERT_ONLY通知（配当落ち・リバランス等で比率がズレた可能性）
    TOLERANCE_PCT = 0.5

    # 使用箇所:
    # 1. StopLossManager._index_to_etf_stop() — ストップ価格変換
    # 2. RuleEngine.index_hit_level() — 売買レベル到達判定
    # 3. OrderGenerator — ブログの配分(%)→株数変換時の参照価格
```

### 3.1 Layer 1: ルールエンジン（15分間隔監視）

Claudeを使わない決定論的チェック。Python関数のみで実装。

キルスイッチとストップロスの経路分離（v2指摘#2を解決）:
- キルスイッチ → HALT_AND_NOTIFY（停止+通知のみ、ポジション変更なし）
- ストップロス → Alpacaサーバーサイドで常設済み（Layer 1では検知+通知のみ）
- シナリオトリガー → TRIGGER_FIRED → Claude起動

```python
class RuleEngine:
    """15分間隔で実行される決定論的チェッカー"""

    def check(self, market_data, portfolio, strategy_spec, state) -> CheckResult:
        """
        Returns:
          CheckResult.HALT - キルスイッチ発動（全取引停止+通知、ポジション変更なし）
          CheckResult.TRIGGER_FIRED - Claude起動が必要
          CheckResult.STOP_TRIGGERED - ストップロス発動を検知（通知のみ、Alpaca側で約定済み）
          CheckResult.NO_ACTION - トリガーなし
        """
        # 1. キルスイッチ（最優先）→ 停止+通知のみ
        kill = self.kill_switch.check(market_data, portfolio)
        if kill:
            return CheckResult.HALT(kill)  # ポジション変更なし

        # 2. ストップロス発動検知（Alpacaサーバー側で既に約定済みか確認）
        stop_fills = self.check_stop_order_fills()
        if stop_fills:
            return CheckResult.STOP_TRIGGERED(stop_fills)  # 通知のみ

        # 3. VIX閾値クロス判定
        if self.vix_crossed_threshold(market_data, state):
            return CheckResult.TRIGGER_FIRED("vix_threshold_cross")

        # 4. 指数が売買レベルに到達
        if self.index_hit_level(market_data, strategy_spec):
            return CheckResult.TRIGGER_FIRED("index_level_hit")

        # 5. ポートフォリオドリフト > 3%
        if self.drift_exceeded(portfolio, strategy_spec, threshold=3.0):
            return CheckResult.TRIGGER_FIRED("drift_exceeded")

        return CheckResult.NO_ACTION
```

### 3.2 Layer 2: Claudeエージェント（strategy_intent出力）

Claudeは注文APIを呼ばない。strategy_intent構造体のみ出力する。

```python
# Claudeが出力するstrategy_intent構造体
@dataclass
class StrategyIntent:
    run_id: str                # 一意の実行ID（v2指摘#1を解決）
    scenario: str              # "base" / "bull" / "bear" / "tail_risk"
    rationale: str             # 判断根拠（自然言語）
    target_allocation: dict    # {symbol: target_pct} e.g. {"SPY": 22, "QQQ": 4, ...}
    priority_actions: list     # 優先順に [{symbol, side, urgency, reason}]
    confidence: str            # "high" / "medium" / "low"
    blog_reference: str        # 参照したブログのセクション名
```

**Claude MCP Tools（6ツール、全てread-only）:**
1. `get_market_data` - FMP/Alpaca経由の市場データ取得
2. `get_strategy_spec` - ブログパーサー
3. `get_portfolio_state` - ポジション取得
4. `get_signal_status` - ルールエンジンのシグナル状態取得
5. `get_trade_history` - SQLite取引履歴
6. `emit_strategy_intent` - strategy_intent構造体を出力（注文ではない）

**Claudeのシステムプロンプト核心部分:**

```
あなたは戦略実行エージェントです。
- ブログの戦略を解釈し、strategy_intentを出力してください
- 注文の実行はあなたの役割ではありません
- emit_strategy_intentツールでのみ判断を出力してください
- 判断が不確実な場合はconfidence="low"として、ルールエンジンに委ねてください
```

### 3.3 Layer 3: Order Validator + Generator（v1指摘#2を解決）

```python
class OrderValidator:
    """Claudeのstrategy_intentを検証し、合格時のみ注文を生成"""

    ALLOWED_SYMBOLS = {"SPY", "QQQ", "DIA", "XLV", "XLP", "GLD", "XLE", "BIL", "TLT", "URA", "SH", "SDS"}
    MAX_DEVIATION_PCT = 3.0       # active scenario配分から±3%以内
    MAX_DAILY_ORDERS = 10
    MAX_DAILY_TURNOVER_PCT = 30.0  # ポートフォリオの30%/日
    MAX_SINGLE_ORDER_PCT = 15.0    # 単一注文はポートフォリオの15%まで

    def validate(self, intent: StrategyIntent, strategy_spec, portfolio, state) -> ValidationResult:
        errors = []

        # 1. 許可シンボルチェック
        for symbol in intent.target_allocation:
            if symbol not in self.ALLOWED_SYMBOLS:
                errors.append(f"Unauthorized symbol: {symbol}")

        # 2. シナリオ整合チェック（v3指摘#6を解決: #3から繰り上げ）
        #    get_scenario_allocationを呼ぶ前にシナリオ存在を確認
        if intent.scenario not in strategy_spec.scenarios:
            errors.append(f"Unknown scenario: {intent.scenario}")
            return ValidationResult.REJECTED(errors)  # 以降のチェックは不可能

        # 3. 最大逸脱チェック（active scenario配分から）（v2指摘#5を解決）
        #    ブログのbase配分ではなく、intent.scenarioに対応するシナリオ配分と比較
        scenario_allocation = strategy_spec.get_scenario_allocation(intent.scenario)
        for symbol, target_pct in intent.target_allocation.items():
            scenario_pct = scenario_allocation.get(symbol, 0)
            if abs(target_pct - scenario_pct) > self.MAX_DEVIATION_PCT:
                errors.append(
                    f"{symbol}: {target_pct}% deviates >{self.MAX_DEVIATION_PCT}% "
                    f"from {intent.scenario} scenario {scenario_pct}%"
                )

        # 4. プレイベントフリーズチェック
        if self.is_pre_event_freeze(strategy_spec):
            if intent.scenario != state.current_scenario:  # シナリオ変更は禁止
                errors.append("Pre-event freeze active: no scenario change allowed")

        # 5. 日次注文数チェック
        daily_orders = self.count_today_orders()
        if daily_orders >= self.MAX_DAILY_ORDERS:
            errors.append(f"Daily order limit reached: {daily_orders}/{self.MAX_DAILY_ORDERS}")

        # 6. 日次売買金額チェック（v2指摘#4を解決）
        daily_turnover = self.calc_today_turnover()
        planned_turnover = self._calc_planned_turnover(intent, portfolio)
        total_turnover_pct = ((daily_turnover + planned_turnover) / portfolio.account_value) * 100
        if total_turnover_pct > self.MAX_DAILY_TURNOVER_PCT:
            errors.append(f"Daily turnover {total_turnover_pct:.1f}% exceeds {self.MAX_DAILY_TURNOVER_PCT}%")

        # 7. 単一注文金額チェック（v2指摘#4を解決）
        for symbol, target_pct in intent.target_allocation.items():
            current_pct = portfolio.get_position_pct(symbol)
            order_pct = abs(target_pct - current_pct)
            if order_pct > self.MAX_SINGLE_ORDER_PCT:
                errors.append(f"{symbol}: single order {order_pct:.1f}% exceeds {self.MAX_SINGLE_ORDER_PCT}%")

        # 8. 合計100%チェック
        total = sum(intent.target_allocation.values())
        if abs(total - 100.0) > 0.5:
            errors.append(f"Allocation total {total}% != 100%")

        if errors:
            return ValidationResult.REJECTED(errors)

        return ValidationResult.APPROVED


class OrderGenerator:
    """検証済みintentから決定論的に注文を生成"""

    def generate(self, intent: StrategyIntent, portfolio, prices) -> list[Order]:
        orders = []
        for symbol, target_pct in intent.target_allocation.items():
            target_value = portfolio.account_value * (target_pct / 100.0)
            current_value = portfolio.positions.get(symbol, {}).get("market_value", 0)
            delta = target_value - current_value

            # 最小取引閾値: ポートフォリオの0.5%未満 or $100未満はスキップ
            if abs(delta) < max(portfolio.account_value * 0.005, 100):
                continue

            # Alpaca fractional shares: ETFは対応（SPY, QQQ等）。
            # 万一非対応銘柄が追加された場合はint()で切り捨て（v6指摘#4を解決）
            raw_shares = delta / prices[symbol]
            if self._supports_fractional(symbol):
                shares = round(raw_shares, 2)
            else:
                shares = int(raw_shares)  # 整数のみ（端数切捨て）
                if shares == 0:
                    continue  # 1株未満はスキップ
            order_id = self._generate_client_order_id(symbol, intent)  # 冪等性保証

            orders.append(Order(
                client_order_id=order_id,  # 二重送信防止（v1指摘#8）
                symbol=symbol,
                side="buy" if shares > 0 else "sell",
                quantity=abs(shares),
                order_type="limit",
                limit_price=self._calc_limit_price(prices[symbol], "buy" if shares > 0 else "sell"),
            ))

        # 売り注文を先に実行（現金確保）
        orders.sort(key=lambda o: (0 if o.side == "sell" else 1))
        return orders

    def _generate_client_order_id(self, symbol, intent) -> str:
        """冪等な注文ID: 同一判断からの再実行で同じIDを生成"""
        # format: {date}_{run_id}_{symbol}_{scenario}（v4指摘#6: コメントと実装を統一）
        return f"{date.today()}_{intent.run_id}_{symbol}_{intent.scenario}"
```

---

## 4. リスク管理（v1指摘#5, #7を解決）

### 4.1 キルスイッチ（統一仕様）

| 条件 | 閾値 | アクション | 詳細 |
|------|------|-----------|------|
| 日次損失 | -3% | HALT_AND_NOTIFY | 新規注文停止、既存ポジション維持、CRITICAL通知 |
| 週次損失 | -7% | HALT_AND_NOTIFY | 同上 |
| ドローダウン | -15% (HWMから) | HALT_AND_NOTIFY | 同上 |
| VIX極端値 | > 40 | HALT_AND_NOTIFY | 同上（防御化は人間判断を待つ） |
| 日次注文数超過 | >= 10 | BLOCK_NEW_ORDERS | 新規注文のみ停止、ストップロスは例外（§3.3と統一） |
| 日次売買金額超過 | > 30% of portfolio | BLOCK_NEW_ORDERS | 同上 |
| API連続エラー | 3回→ALERT_ONLY、6回→HALT_AND_NOTIFY | 段階的エスカレーション（§2.3と統一、v5指摘#1を解決） | |

**統一原則**: キルスイッチは「停止+通知」のみ。ポジション変更（防御化含む）は自動で行わない。

```python
# None値の安全な扱い（v5指摘#4を解決）:
class KillSwitch:
    def check(self, market_data, portfolio) -> Optional[str]:
        loss_calc = LossCalculator(self.db)

        # daily/weekly が None（プレマーケット等）→ そのチェックをスキップ
        daily = loss_calc.daily_loss_pct(portfolio)
        if daily is not None and daily <= -3.0:
            return "daily_loss_exceeded"

        weekly = loss_calc.weekly_loss_pct(portfolio)
        if weekly is not None and weekly <= -7.0:
            return "weekly_loss_exceeded"

        # drawdown は常に有効（HWMは全期間で保持）
        dd = loss_calc.drawdown_pct(portfolio)
        if dd <= -15.0:
            return "drawdown_exceeded"

        # VIXチェック
        if market_data.vix and market_data.vix > 40:
            return "vix_extreme"

        # API連続エラーチェック（§2.3エスカレーションと統一、v6指摘#1を解決）
        api_fail_count = self.state.consecutive_api_failures
        if api_fail_count >= 6:
            return "api_consecutive_failures_halt"  # → HALT_AND_NOTIFY
        # 3回はRuleEngine側でALERT_ONLY通知（キルスイッチ=HALT閾値は6回）

        return None  # キルスイッチ非発動
```

### 4.2 損失計算の厳密定義（v1指摘#7を解決）

```python
class LossCalculator:
    """損失指標の計算基準を厳密に定義"""

    def daily_loss_pct(self, portfolio) -> float | None:
        """日次損失 = (現在評価額 - 当日寄付時評価額) / 当日寄付時評価額 × 100

        基準時刻: 当日9:30 ET（最初の15分チェック時のスナップショット）
        計算対象: 評価損益（未実現+実現）

        プレマーケット(6:30 ET等): 9:30スナップショット未作成のためNone返却
        → キルスイッチは前日終値ベースのdrawdown_pctのみ適用
        → 9:30の最初のチェックでスナップショット作成後、daily_loss有効化
        """
        snapshot = self.db.get_opening_snapshot(date.today())
        if snapshot is None:
            return None  # プレマーケット: daily_loss判定スキップ
        return ((portfolio.account_value - snapshot.account_value) / snapshot.account_value) * 100

    def weekly_loss_pct(self, portfolio) -> float | None:
        """週次損失 = (現在評価額 - 月曜寄付時評価額) / 月曜寄付時評価額 × 100

        週の開始: 月曜日9:30 ET（月曜休場時は火曜日）

        月曜6:30 ET等（週初スナップショット未作成時）: None返却（v4指摘#1を解決）
        → キルスイッチはdrawdown_pctのみ適用（daily_loss_pctと同様の安全策）
        → 月曜9:30の最初のチェックでスナップショット作成後、weekly_loss有効化
        """
        snapshot = self.db.get_week_opening_snapshot()
        if snapshot is None:
            return None  # 週初プレマーケット: weekly_loss判定スキップ
        return ((portfolio.account_value - snapshot.account_value) / snapshot.account_value) * 100

    def drawdown_pct(self, portfolio) -> float:
        """ドローダウン = (現在評価額 - HWM) / HWM × 100

        HWM: 15分チェック時の評価額の全期間最大値
        更新タイミング: 15分チェック毎に、現在値 > HWMなら更新
        """
        hwm = self.db.get_high_water_mark()
        return ((portfolio.account_value - hwm) / hwm) * 100
```

---

## 5. 注文の冪等性と障害復旧（v1指摘#8を解決）

### 5.1 client_order_id による二重送信防止

```
# 注文IDフォーマット: {YYYYMMDD}_{run_id}_{symbol}_{scenario}
# 例: "20260217_run1708_SPY_base"
# 同一run_id + symbol + scenarioからは同じIDが生成される
# Alpaca APIはclient_order_idの重複を拒否 → 二重送信を物理的に防止
```

### 5.2 障害復旧手順

| 障害 | 検知方法 | 復旧手順 |
|------|---------|---------|
| API タイムアウト | HTTPタイムアウト (10秒) | 30秒待って再試行（同じclient_order_id）。連続失敗は§2.3エスカレーション（3回→ALERT_ONLY、6回→HALT_AND_NOTIFY）に準拠 |
| 部分約定 | order.status == "partially_filled" | 残数量は次回15分チェックで再評価。手動介入不要 |
| 注文拒否 | order.status == "rejected" | ログに記録、ALERT通知。自動リトライなし |
| DB書き込み失敗 | SQLite exception | 注文は送信済み。次回チェックでAlpacaポジションから状態復元 |
| プロセスクラッシュ | ファイルロック消失 | 次回起動時にAlpacaポジションとDB差分を検出→メール通知 |

---

## 6. スケジューラ設計（v1指摘#9を解決）

### 6.1 排他制御（v2指摘#8を解決）

```python
import fcntl

class SchedulerGuard:
    """OSレベルファイルロックで重複起動を防止"""

    LOCK_FILE = "data/.scheduler.lock"

    def acquire(self) -> bool:
        """fcntl.flock()によるOSレベル排他ロック
        プロセスクラッシュ時はOSが自動解放（stale問題なし）"""
        self.lock_fd = open(self.LOCK_FILE, 'w')
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_fd.write(f"{os.getpid()}\n{datetime.now().isoformat()}")
            self.lock_fd.flush()
            return True
        except (IOError, OSError):
            # 別プロセスがロック中
            self.lock_fd.close()
            return False

    def release(self):
        fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
        self.lock_fd.close()
```

### 6.2 ミスジョブ検知

```
# 朝6:30 ETの定時チェックが実行されなかった場合:
# - 次回15分チェック時にlast_daily_check timestampを確認
# - 当日未実行なら即座にClaude起動（遅延実行）
# - ALERT通知: "定時チェック未実行。{delay}分遅延で実行"
```

### 6.3 APScheduler設定（v2指摘#9を解決）

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler(
    timezone="US/Eastern",           # ET固定（DST自動対応）
    job_defaults={
        "coalesce": True,            # 溜まったジョブは1回にまとめる
        "max_instances": 1,          # 同一ジョブの並行実行禁止
        "misfire_grace_time": 900,   # 15分以内の遅延は実行（それ以上はスキップ）
    }
)

# 15分間隔チェック（市場時間中のみ）（v3指摘#2を解決）
# 9:30開始、16:00終了。9:00/9:15は市場前なので除外。
scheduler.add_job(
    rule_engine_check,
    "cron",
    day_of_week="mon-fri",
    hour="10-15",                    # 10:00-15:45（フル稼働）
    minute="0,15,30,45",
)
# 9:30と9:45は別途追加（hour=9だと9:00/9:15も発火するため）
scheduler.add_job(rule_engine_check, "cron", day_of_week="mon-fri", hour=9, minute="30,45")
# 最終チェック 16:00（クローズ直後）
scheduler.add_job(rule_engine_check, "cron", day_of_week="mon-fri", hour=16, minute=0)

# 朝のClaude定時チェック
scheduler.add_job(daily_claude_check, "cron", day_of_week="mon-fri", hour=6, minute=30)
```

半日取引（Thanksgiving前日等）: `core/holidays.py` に早期閉場日リストを保持。15分チェック時にクローズ時刻を確認し、早期終了。

---

## 7. bubble_scorer.py の扱い（v1指摘#6を解決）

**方針: ブログに記載されたバブルスコアを参照する（自前計算しない）**

ブログは毎週「バブルスコア 9/15点（Elevated Risk）」等を記載する。strategy_parser がこの値を抽出し、ルールエンジンの判断材料にする。bubble_scorer.py の自動実行は行わない。

理由: バブルスコアの8指標のうち半数（大衆浸透度、メディア飽和、新規参入、新規発行氾濫）は定量APIで自動取得できず、LLMによる定性判断が必要。週次ブログ作成時にus-market-analystエージェントが既にこの判断を行っているため、そこで確定した値を使う。

---

## 8. ファイル構成

```
weekly-trade-strategy/
├── trading/                              # NEW: 自動トレードシステム
│   ├── __init__.py
│   ├── main.py                           # エントリポイント + APScheduler
│   ├── config.py                         # 設定（API keys, 閾値, モード）
│   │
│   ├── layer1/                           # Layer 1: ルールエンジン（15分間隔）
│   │   ├── __init__.py
│   │   ├── rule_engine.py                # 15分間隔チェッカー
│   │   ├── kill_switch.py                # キルスイッチ（統一仕様: HALT_AND_NOTIFY）
│   │   ├── stop_loss_manager.py          # Alpacaサーバーサイド逆指値の常設管理
│   │   ├── loss_calculator.py            # 損失計算（厳密定義）
│   │   └── market_monitor.py             # FMP/Alpacaデータ取得+バリデーション
│   │
│   ├── layer2/                           # Layer 2: Claudeエージェント
│   │   ├── __init__.py
│   │   ├── agent_runner.py               # ClaudeSDKClient管理
│   │   ├── system_prompt.py              # エージェントプロンプト
│   │   └── tools/                        # MCP Tools（read-only 6ツール）
│   │       ├── __init__.py
│   │       ├── market_data.py            # get_market_data
│   │       ├── strategy_parser.py        # get_strategy_spec（ブログパーサー）
│   │       ├── portfolio.py              # get_portfolio_state
│   │       ├── signal_status.py          # get_signal_status
│   │       ├── trade_history.py          # get_trade_history
│   │       └── strategy_intent.py        # emit_strategy_intent
│   │
│   ├── layer3/                           # Layer 3: 注文検証+生成
│   │   ├── __init__.py
│   │   ├── order_validator.py            # ルールエンジン最終検証
│   │   ├── order_generator.py            # 決定論的注文生成
│   │   └── order_executor.py             # Alpaca API注文送信+約定確認
│   │
│   ├── services/                         # 外部サービスクライアント
│   │   ├── __init__.py
│   │   ├── fmp_client.py                 # FMP API（VIX/利回り/指数/コモディティ）
│   │   ├── alpaca_client.py              # Alpaca API（ETF取引+データ）
│   │   ├── email_notifier.py             # Gmail SMTP通知
│   │   └── data_validator.py             # 全データのバリデーション
│   │
│   ├── data/                             # データ永続化
│   │   ├── __init__.py
│   │   ├── database.py                   # SQLite接続+マイグレーション
│   │   ├── models.py                     # dataclass定義
│   │   └── migrations/
│   │       └── 001_initial.sql
│   │
│   ├── core/                             # 共通ユーティリティ
│   │   ├── __init__.py
│   │   ├── holidays.py                   # 米国市場休日カレンダー
│   │   ├── scheduler_guard.py            # ファイルロック排他制御
│   │   └── constants.py                  # 閾値定数（Monty Style）
│   │
│   └── tests/                            # テストスイート
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_rule_engine.py
│       ├── test_kill_switch.py
│       ├── test_loss_calculator.py
│       ├── test_order_validator.py
│       ├── test_order_generator.py
│       ├── test_strategy_parser.py
│       ├── test_fmp_client.py
│       ├── test_data_validator.py
│       ├── test_scheduler_guard.py
│       ├── test_e2e_failures.py          # 障害系E2Eテスト（v1指摘#10）
│       └── fixtures/
│           ├── sample_blog.md            # 2026-02-16ブログのコピー
│           ├── sample_market_data.json
│           ├── sample_portfolio.json
│           └── sample_fmp_responses.json
│
├── data/                                 # ランタイムデータ（.gitignore）
│   ├── trading_system.db
│   ├── .scheduler.lock
│   └── logs/
│       └── YYYY-MM-DD.json
│
├── .env                                  # API keys
└── pyproject.toml
```

### 8.1 SQLiteスキーマ（001_initial.sql）（v8指摘#1を解決）

```sql
-- 市場データスナップショット（日次/週次の基準値）
CREATE TABLE snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,           -- 'daily_open' / 'weekly_open'
    date TEXT NOT NULL,           -- YYYY-MM-DD
    account_value REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(type, date)
);

-- ハイウォーターマーク
CREATE TABLE high_water_mark (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- 常に1行
    value REAL NOT NULL,
    updated_at TEXT NOT NULL
);

-- システム状態（キー/バリュー）
CREATE TABLE state (
    key TEXT PRIMARY KEY,         -- 'consecutive_api_failures', 'current_scenario', etc.
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ストップ注文シーケンス
CREATE TABLE stop_seq (
    symbol TEXT NOT NULL,
    blog_date TEXT NOT NULL,      -- YYYY-MM-DD
    seq INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (symbol, blog_date)
);

-- 指数→ETFキャリブレーション比率
CREATE TABLE calibration (
    date TEXT NOT NULL,           -- YYYY-MM-DD
    symbol TEXT NOT NULL,         -- 'SPY', 'QQQ', 'DIA'
    index_symbol TEXT NOT NULL,   -- '^GSPC', '^NDX', '^DJI'
    ratio REAL NOT NULL,
    PRIMARY KEY (date, symbol)
);

-- トレード決定ログ
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    run_id TEXT,
    trigger_type TEXT NOT NULL,   -- 'scheduled', 'vix_cross', 'drift', etc.
    result TEXT NOT NULL,         -- 'NO_ACTION', 'APPROVED', 'REJECTED', 'HALT'
    scenario TEXT,
    rationale TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 約定済み注文
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_order_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    filled_price REAL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    filled_at TEXT
);

-- 市場データ履歴（15分間隔）
CREATE TABLE market_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    vix REAL,
    us10y REAL,
    sp500 REAL,
    nasdaq REAL,
    dow REAL,
    gold REAL,
    oil REAL
);
```

### 再利用する既存コード

| ファイル | 再利用箇所 |
|---------|-----------|
| `.claude/skills/economic-calendar-fetcher/scripts/get_economic_calendar.py` | FMP APIの呼び出しパターン（`urllib.request` + `FMP_API_KEY`） |
| `.claude/skills/breadth-chart-analyst/scripts/detect_breadth_values.py` | 週次分析時のBreadth検出 |
| `.claude/skills/breadth-chart-analyst/scripts/detect_uptrend_ratio.py` | 週次分析時のUptrend Ratio検出 |
| ブログのバブルスコア値 | `strategy_parser.py`でブログから抽出（`bubble_scorer.py`は呼ばない） |

---

## 9. 開発フェーズ

### Phase 1: Layer 1 + データ基盤（3週間）

**目標**: 15分間隔の決定論的監視が正しく動作することを検証。

実装順序:
1. `config.py` + `.env` — 設定管理
2. `data/database.py` + `models.py` — SQLiteスキーマ
3. `services/fmp_client.py` — FMP API統合（既存パターン流用）
4. `services/data_validator.py` — 全取得値のバリデーション
5. `services/alpaca_client.py` — Alpaca Market Data API
6. `core/holidays.py` + `core/constants.py` — 休日・閾値定数
7. `layer2/tools/strategy_parser.py` — ブログパーサー（最重要モジュール）
8. `layer1/loss_calculator.py` — 損失計算
9. `layer1/kill_switch.py` — キルスイッチ
10. `layer1/rule_engine.py` — 15分間隔チェッカー
11. `core/scheduler_guard.py` — 排他制御
12. `main.py` — APScheduler統合

**検証**: 2週間、ログ出力のみで並行稼働。15分毎のチェック結果とブログの閾値判定が一致するか確認。

### Phase 2: Layer 2 + Layer 3 + ペーパートレード（4週間）

**目標**: Claude → ルールエンジン → 注文のパイプライン検証。

追加実装:
1. `layer2/` — Claudeエージェント統合
2. `layer3/order_validator.py` — 注文検証
3. `layer3/order_generator.py` — 注文生成（client_order_id）
4. `layer3/order_executor.py` — Alpaca Paper Account注文
5. `services/email_notifier.py` — メール通知

**検証**: Alpacaペーパーアカウントで3-4週間稼働。注文の正確性、ストップロス発動、キルスイッチ動作を確認。

### Phase 3: ライブトレード（段階的スケール）

スケーリング: 20% → 50% → 100%（各2週間）

---

## 10. テスト計画（v1指摘#10を解決）

### ユニットテスト

| テストファイル | 対象 | 主要テストケース |
|--------------|------|----------------|
| `test_rule_engine.py` | Layer 1 | VIX各閾値クロス、ストップ発動検知、ドリフト検出 |
| `test_stop_loss_manager.py` | ストップロス常設 | replace_order成功/失敗、複数ストップ異常系、seq一意性、リバランス後再同期 |
| `test_kill_switch.py` | キルスイッチ | 日次/週次損失、ドローダウン、VIX>40、API連続3回ALERT/6回HALT、daily=None時スキップ、weekly=None時スキップ |
| `test_loss_calculator.py` | 損失計算 | 評価損益ベース、寄付時基準、HWM更新 |
| `test_order_validator.py` | Layer 3 | 許可シンボル外拒否、最大逸脱拒否、日次上限、100%チェック |
| `test_order_generator.py` | 注文生成 | client_order_id冪等性、売り先行、最小閾値スキップ |
| `test_strategy_parser.py` | ブログパーサー | 実ブログ（2026-02-16）のアロケーション/シナリオ/トリガー抽出 |
| `test_fmp_client.py` | FMP API | レスポンスパース、単位正規化、バリデーション |
| `test_data_validator.py` | データ検証 | 範囲外値、null値、API失敗時の前回値保持+ALERT_ONLY |
| `test_scheduler_guard.py` | 排他制御 | ロック取得/解放、重複起動拒否、OS自動解放確認 |

### 障害系E2Eテスト（`test_e2e_failures.py`）

| テストケース | 内容 |
|-------------|------|
| `test_fmp_api_timeout` | FMP API 10秒タイムアウト時の前回値保持+ALERT_ONLY動作 |
| `test_alpaca_order_rejected` | Alpaca注文拒否時のログ+通知 |
| `test_partial_fill_recovery` | 部分約定後の次回チェック時の正しい評価 |
| `test_email_send_failure` | SMTP失敗時にログへフォールバック（取引は継続） |
| `test_db_lock_contention` | SQLiteロック時のリトライ動作 |
| `test_duplicate_order_prevention` | 同一client_order_idの二重送信がAlpacaで拒否されること |
| `test_process_crash_recovery` | ロックファイル残存からの復旧 |
| `test_stale_blog_handling` | 5日以上古いブログ使用時の保守的動作 |
| `test_holiday_detection` | 祝日にチェックがスキップされること |
| `test_kill_switch_overrides_claude` | キルスイッチ発動時にClaude提案が無視されること |
| `test_api_escalation_3_then_6` | API連続3回でALERT_ONLY、6回でHALT_AND_NOTIFY、回復でリセット |
| `test_replace_order_failure_fallback` | replace_order失敗時に状態確認→新規submit or 手動通知 |
| `test_session_freshness_premarket` | プレマーケット6:30 ETで前日終値がstale判定されないこと |
| `test_fractional_vs_whole_shares` | fractional非対応銘柄で整数切捨て+0株スキップ |

---

## 11. 依存パッケージ

```toml
[project]
name = "weekly-trade-strategy-bot"
requires-python = ">=3.10"
dependencies = [
    "claude-agent-sdk>=0.1.35",
    "alpaca-py>=0.30",
    "apscheduler>=3.10",
    "aiosqlite>=0.20",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
]
```

yfinanceは使用しない。FMP API失敗時は前回値を保持しALERT_ONLY通知。フォールバック先を持たず「安全側に停止」を原則とする。

---

## 12. 検証方法

### Phase 1 完了基準

- 15分間隔チェックが2週間安定稼働
- FMP APIからVIX/10Y利回り/指数が正しい単位で取得できること
- ブログパーサーが2026-02-16ブログの全セクションを正しく抽出
- キルスイッチの全条件が正しく発火すること（テストで確認）
- ログ出力が手動トレード判断と80%以上一致

### Phase 2 完了基準

- Alpacaペーパーアカウントで3週間稼働
- Claude → ルールエンジン検証 → 注文生成の全パイプライン動作
- Alpacaサーバーサイド逆指値が正しく常設され、指数ストップ到達時に即時発動
- client_order_idによる二重送信防止が動作
- メール通知が全決定タイプ（NO_ACTION/ALERT_ONLY/REBALANCE/HALT_AND_NOTIFY）で送信

### Phase 3 移行基準

- Phase 2で重大バグなし（HALT_AND_NOTIFY以外で意図しない注文なし）
- ペーパートレードのリターンが手動トレードと±5%以内の乖離
