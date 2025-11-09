PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    entry_price REAL,
                    quantity INTEGER,
                    entry_date TEXT,
                    current_price REAL,
                    total_investment REAL,
                    current_value REAL,
                    profit_loss REAL,
                    profit_loss_pct REAL,
                    status TEXT DEFAULT 'watching',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, ticker)
                );
DELETE FROM sqlite_sequence;
CREATE INDEX idx_portfolio_user_id ON portfolio(user_id);
CREATE INDEX idx_portfolio_ticker ON portfolio(ticker);
CREATE INDEX idx_portfolio_status ON portfolio(status);
COMMIT;
