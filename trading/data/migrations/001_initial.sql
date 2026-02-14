-- Initial schema for the trading system

-- Market data snapshots (daily/weekly baselines)
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,           -- 'daily_open' / 'weekly_open'
    date TEXT NOT NULL,           -- YYYY-MM-DD
    account_value REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(type, date)
);

-- High water mark (always exactly 1 row)
CREATE TABLE IF NOT EXISTS high_water_mark (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    value REAL NOT NULL,
    updated_at TEXT NOT NULL
);

-- System state (key/value store)
CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Stop order sequence numbers
CREATE TABLE IF NOT EXISTS stop_seq (
    symbol TEXT NOT NULL,
    blog_date TEXT NOT NULL,
    seq INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (symbol, blog_date)
);

-- Index-to-ETF calibration ratios
CREATE TABLE IF NOT EXISTS calibration (
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,         -- 'SPY', 'QQQ', 'DIA'
    index_symbol TEXT NOT NULL,   -- '^GSPC', '^NDX', '^DJI'
    ratio REAL NOT NULL,
    PRIMARY KEY (date, symbol)
);

-- Trade decision log
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    run_id TEXT,
    trigger_type TEXT NOT NULL,
    result TEXT NOT NULL,         -- 'NO_ACTION', 'APPROVED', 'REJECTED', 'HALT'
    scenario TEXT,
    rationale TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Filled orders
CREATE TABLE IF NOT EXISTS trades (
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

-- Market data history (15-min intervals)
CREATE TABLE IF NOT EXISTS market_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    vix REAL,
    us10y REAL,
    sp500 REAL,
    nasdaq REAL,
    dow REAL,
    gold REAL,
    oil REAL,
    copper REAL
);
