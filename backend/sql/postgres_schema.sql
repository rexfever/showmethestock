-- PostgreSQL schema for stock-finder (generated from SQLite analysis)
-- Step 2: draft schema for migration

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id                  BIGSERIAL PRIMARY KEY,
    email               TEXT NOT NULL UNIQUE,
    phone               TEXT,
    notification_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    name                TEXT,
    provider            TEXT NOT NULL DEFAULT 'local',
    provider_id         TEXT,
    membership_tier     TEXT NOT NULL DEFAULT 'free',
    subscription_status TEXT NOT NULL DEFAULT 'active',
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    payment_method      TEXT,
    is_admin            BOOLEAN NOT NULL DEFAULT FALSE,
    last_login          TIMESTAMP WITH TIME ZONE,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    password_hash       TEXT,
    is_email_verified   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    plan_id         TEXT NOT NULL,
    payment_id      TEXT,
    amount          NUMERIC(12,2) NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    started_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    cancelled_at    TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);

CREATE TABLE IF NOT EXISTS payments (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    subscription_id BIGINT REFERENCES subscriptions (id) ON DELETE SET NULL,
    payment_id      TEXT NOT NULL,
    amount          NUMERIC(12,2) NOT NULL,
    method          TEXT NOT NULL,
    status          TEXT NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_subscription_id ON payments(subscription_id);

CREATE TABLE IF NOT EXISTS maintenance_settings (
    id          BIGSERIAL PRIMARY KEY,
    is_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    end_date    TIMESTAMP WITH TIME ZONE,
    message     TEXT NOT NULL DEFAULT '서비스 점검 중입니다.',
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS popup_notice (
    id          BIGSERIAL PRIMARY KEY,
    is_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    start_date  TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date    TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scanner_settings (
    id          SERIAL PRIMARY KEY,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    description TEXT,
    updated_by  TEXT,
    updated_at  TIMESTAMP DEFAULT NOW(),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scanner_settings_key ON scanner_settings(setting_key);

CREATE TABLE IF NOT EXISTS market_conditions (
    date                DATE PRIMARY KEY,
    market_sentiment    TEXT NOT NULL,
    kospi_return        DOUBLE PRECISION,
    volatility          DOUBLE PRECISION,
    rsi_threshold       DOUBLE PRECISION,
    sector_rotation     TEXT,
    foreign_flow        TEXT,
    volume_trend        TEXT,
    min_signals         INTEGER,
    macd_osc_min        DOUBLE PRECISION,
    vol_ma5_mult        DOUBLE PRECISION,
    gap_max             DOUBLE PRECISION,
    ext_from_tema20_max DOUBLE PRECISION,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS send_logs (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMP WITH TIME ZONE NOT NULL,
    to_no           TEXT NOT NULL,
    matched_count   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_send_logs_ts ON send_logs(ts);

CREATE TABLE IF NOT EXISTS positions (
    id                  BIGSERIAL PRIMARY KEY,
    ticker              TEXT NOT NULL,
    name                TEXT NOT NULL,
    entry_date          DATE NOT NULL,
    quantity            INTEGER NOT NULL,
    score               INTEGER,
    strategy            TEXT,
    current_return_pct  DOUBLE PRECISION,
    max_return_pct      DOUBLE PRECISION,
    exit_date           DATE,
    status              TEXT NOT NULL DEFAULT 'open',
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_entry_date ON positions(entry_date);

CREATE TABLE IF NOT EXISTS scan_rank (
    date                DATE NOT NULL,
    code                TEXT NOT NULL,
    name                TEXT,
    score               DOUBLE PRECISION,
    score_label         TEXT,
    current_price       DOUBLE PRECISION,
    close_price         DOUBLE PRECISION,
    volume              BIGINT,
    change_rate         DOUBLE PRECISION,
    market              TEXT,
    strategy            TEXT,
    indicators          JSONB,
    trend               TEXT,
    flags               TEXT,
    details             JSONB,
    returns             JSONB,
    recurrence          JSONB,
    scanner_version     TEXT NOT NULL DEFAULT 'v1',
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (date, code, scanner_version)
);

CREATE INDEX IF NOT EXISTS idx_scan_rank_score ON scan_rank(score);
CREATE INDEX IF NOT EXISTS idx_scan_rank_market ON scan_rank(market);
CREATE INDEX IF NOT EXISTS idx_scan_rank_scanner_version ON scan_rank(scanner_version);
CREATE INDEX IF NOT EXISTS idx_scan_rank_date_version ON scan_rank(date, scanner_version);

CREATE TABLE IF NOT EXISTS portfolio (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    ticker              TEXT NOT NULL,
    name                TEXT NOT NULL,
    entry_price         DOUBLE PRECISION,
    quantity            INTEGER,
    entry_date          DATE,
    current_price       DOUBLE PRECISION,
    total_investment    DOUBLE PRECISION,
    current_value       DOUBLE PRECISION,
    profit_loss         DOUBLE PRECISION,
    profit_loss_pct     DOUBLE PRECISION,
    status              TEXT NOT NULL DEFAULT 'watching',
    source              TEXT NOT NULL DEFAULT 'recommended',
    recommendation_score INTEGER,
    recommendation_date DATE,
    daily_return_pct    DOUBLE PRECISION,
    max_return_pct      DOUBLE PRECISION,
    min_return_pct      DOUBLE PRECISION,
    holding_days        INTEGER,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_user_id ON portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_status ON portfolio(status);
CREATE INDEX IF NOT EXISTS idx_portfolio_source ON portfolio(source);

CREATE TABLE IF NOT EXISTS trading_history (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    ticker          TEXT NOT NULL,
    name            TEXT NOT NULL,
    trade_type      TEXT NOT NULL,
    quantity        INTEGER NOT NULL,
    price           DOUBLE PRECISION NOT NULL,
    trade_date      DATE NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trading_history_user_id ON trading_history(user_id);
CREATE INDEX IF NOT EXISTS idx_trading_history_trade_date ON trading_history(trade_date);

CREATE TABLE IF NOT EXISTS email_verifications (
    id                  BIGSERIAL PRIMARY KEY,
    email               TEXT NOT NULL,
    verification_code   TEXT NOT NULL,
    verification_type   TEXT NOT NULL DEFAULT 'signup',
    is_verified         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_email_verifications_email ON email_verifications(email);
CREATE INDEX IF NOT EXISTS idx_email_verifications_expires_at ON email_verifications(expires_at);

CREATE TABLE IF NOT EXISTS news_data (
    id              BIGSERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL,
    title           TEXT NOT NULL,
    content         TEXT,
    source          TEXT,
    published_at    TIMESTAMP WITH TIME ZONE,
    sentiment_score DOUBLE PRECISION,
    relevance_score DOUBLE PRECISION,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_data_ticker ON news_data(ticker);
CREATE INDEX IF NOT EXISTS idx_news_data_published_at ON news_data(published_at);

CREATE TABLE IF NOT EXISTS search_trends (
    id              BIGSERIAL PRIMARY KEY,
    ticker          TEXT NOT NULL,
    search_volume   INTEGER,
    trend_score     DOUBLE PRECISION,
    date            DATE,
    source          TEXT,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_trends_ticker ON search_trends(ticker);
CREATE INDEX IF NOT EXISTS idx_search_trends_date ON search_trends(date);


