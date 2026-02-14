"""SQLite database connection and operations."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from trading.data.models import AccountSnapshot


MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Database:
    """Synchronous SQLite wrapper for the trading system."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._conn

    def migrate(self) -> None:
        migration_file = MIGRATIONS_DIR / "001_initial.sql"
        sql = migration_file.read_text()
        self.conn.executescript(sql)
        self.conn.commit()

    # --- Snapshots ---

    def get_opening_snapshot(self, target_date: date) -> Optional[AccountSnapshot]:
        row = self.conn.execute(
            "SELECT type, date, account_value, created_at FROM snapshots "
            "WHERE type = 'daily_open' AND date = ?",
            (target_date.isoformat(),),
        ).fetchone()
        if row is None:
            return None
        return AccountSnapshot(
            snapshot_type=row["type"],
            date=row["date"],
            account_value=row["account_value"],
            created_at=row["created_at"],
        )

    def save_opening_snapshot(self, snapshot_type: str, target_date: date, account_value: float) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO snapshots (type, date, account_value) VALUES (?, ?, ?)",
            (snapshot_type, target_date.isoformat(), account_value),
        )
        self.conn.commit()

    def get_week_opening_snapshot(self) -> Optional[AccountSnapshot]:
        today = date.today()
        weekday = today.weekday()  # 0=Mon
        monday = today if weekday == 0 else date.fromordinal(today.toordinal() - weekday)

        for offset in range(5):
            check_date = date.fromordinal(monday.toordinal() + offset)
            row = self.conn.execute(
                "SELECT type, date, account_value, created_at FROM snapshots "
                "WHERE type = 'weekly_open' AND date = ?",
                (check_date.isoformat(),),
            ).fetchone()
            if row:
                return AccountSnapshot(
                    snapshot_type=row["type"],
                    date=row["date"],
                    account_value=row["account_value"],
                    created_at=row["created_at"],
                )
        return None

    # --- High Water Mark ---

    def get_high_water_mark(self) -> float:
        row = self.conn.execute(
            "SELECT value FROM high_water_mark WHERE id = 1"
        ).fetchone()
        if row is None:
            return 0.0
        return row["value"]

    def update_high_water_mark(self, value: float) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO high_water_mark (id, value, updated_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at "
            "WHERE excluded.value > high_water_mark.value",
            (value, now),
        )
        self.conn.commit()

    # --- State (key/value) ---

    def get_state(self, key: str, default: str = "0") -> str:
        row = self.conn.execute(
            "SELECT value FROM state WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return row["value"]

    def set_state(self, key: str, value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO state (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, now),
        )
        self.conn.commit()

    # --- Stop Sequence ---

    def increment_stop_seq(self, symbol: str, blog_date: str) -> int:
        row = self.conn.execute(
            "SELECT seq FROM stop_seq WHERE symbol = ? AND blog_date = ?",
            (symbol, blog_date),
        ).fetchone()
        if row is None:
            self.conn.execute(
                "INSERT INTO stop_seq (symbol, blog_date, seq) VALUES (?, ?, 0)",
                (symbol, blog_date),
            )
            self.conn.commit()
            return 0
        new_seq = row["seq"] + 1
        self.conn.execute(
            "UPDATE stop_seq SET seq = ? WHERE symbol = ? AND blog_date = ?",
            (new_seq, symbol, blog_date),
        )
        self.conn.commit()
        return new_seq

    # --- Calibration ---

    def get_calibration(self, target_date: date, symbol: str) -> Optional[float]:
        row = self.conn.execute(
            "SELECT ratio FROM calibration WHERE date = ? AND symbol = ?",
            (target_date.isoformat(), symbol),
        ).fetchone()
        return row["ratio"] if row else None

    def save_calibration(self, target_date: date, symbol: str, index_symbol: str, ratio: float) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO calibration (date, symbol, index_symbol, ratio) VALUES (?, ?, ?, ?)",
            (target_date.isoformat(), symbol, index_symbol, ratio),
        )
        self.conn.commit()

    # --- Decisions ---

    def log_decision(self, timestamp: str, run_id: Optional[str], trigger_type: str,
                     result: str, scenario: Optional[str] = None, rationale: Optional[str] = None) -> None:
        self.conn.execute(
            "INSERT INTO decisions (timestamp, run_id, trigger_type, result, scenario, rationale) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, run_id, trigger_type, result, scenario, rationale),
        )
        self.conn.commit()

    def count_today_orders(self) -> int:
        today_str = date.today().isoformat()
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM trades WHERE date(created_at) = ?",
            (today_str,),
        ).fetchone()
        return row["cnt"] if row else 0

    def get_today_turnover(self) -> float:
        today_str = date.today().isoformat()
        row = self.conn.execute(
            "SELECT COALESCE(SUM(ABS(quantity * filled_price)), 0) as total "
            "FROM trades WHERE date(created_at) = ? AND filled_price IS NOT NULL",
            (today_str,),
        ).fetchone()
        return row["total"] if row else 0.0

    # --- Trades ---

    def save_trade(self, client_order_id: str, symbol: str, side: str,
                   quantity: float, status: str, filled_price: Optional[float] = None,
                   filled_at: Optional[str] = None) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO trades "
            "(client_order_id, symbol, side, quantity, filled_price, status, filled_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (client_order_id, symbol, side, quantity, filled_price, status, filled_at),
        )
        self.conn.commit()

    def update_trade_status(self, client_order_id: str, status: str,
                            filled_price: Optional[float] = None,
                            filled_at: Optional[str] = None) -> None:
        if filled_price is not None:
            self.conn.execute(
                "UPDATE trades SET status = ?, filled_price = ?, filled_at = ? "
                "WHERE client_order_id = ?",
                (status, filled_price, filled_at, client_order_id),
            )
        else:
            self.conn.execute(
                "UPDATE trades SET status = ? WHERE client_order_id = ?",
                (status, client_order_id),
            )
        self.conn.commit()

    # --- Market States ---

    def save_market_state(self, timestamp: str, vix: Optional[float] = None,
                          us10y: Optional[float] = None, sp500: Optional[float] = None,
                          nasdaq: Optional[float] = None, dow: Optional[float] = None,
                          gold: Optional[float] = None, oil: Optional[float] = None,
                          copper: Optional[float] = None) -> None:
        self.conn.execute(
            "INSERT INTO market_states (timestamp, vix, us10y, sp500, nasdaq, dow, gold, oil, copper) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (timestamp, vix, us10y, sp500, nasdaq, dow, gold, oil, copper),
        )
        self.conn.commit()

    def get_previous_market_state(self, key: str) -> Optional[float]:
        col_map = {
            "vix": "vix", "us10y": "us10y", "sp500": "sp500",
            "nasdaq": "nasdaq", "dow": "dow", "gold": "gold", "oil": "oil",
            "copper": "copper",
        }
        col = col_map.get(key)
        if not col:
            return None
        row = self.conn.execute(
            f"SELECT {col} FROM market_states WHERE {col} IS NOT NULL "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None

    def get_recent_decisions(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM decisions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recent_trades(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
