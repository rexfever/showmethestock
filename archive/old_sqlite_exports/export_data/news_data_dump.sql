PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE news_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                source TEXT,
                published_at TIMESTAMP,
                sentiment_score REAL,
                relevance_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
CREATE TABLE search_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                search_volume INTEGER,
                trend_score REAL,
                date DATE,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
DELETE FROM sqlite_sequence;
COMMIT;
