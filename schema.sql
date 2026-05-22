CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    link TEXT UNIQUE NOT NULL,
    published_at DATETIME,
    source TEXT,
    content TEXT,
    sentiment_score REAL,
    sentiment_label TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_published_at ON news(published_at);
CREATE INDEX IF NOT EXISTS idx_sentiment_label ON news(sentiment_label);
