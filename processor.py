import feedparser
import sqlite3
import re
import time
from datetime import datetime
from typing import List, Dict

# Configuration
DB_PATH = "data/sentiment.db"
RSS_FEEDS = [
    {"name": "Antara Ekonomi", "url": "https://www.antaranews.com/rss/ekonomi.xml"},
    {"name": "CNBC Indonesia", "url": "https://www.cnbcindonesia.com/news/rss"},
    {"name": "CNN Indonesia", "url": "https://www.cnnindonesia.com/ekonomi/rss"},
    {"name": "Detik Finance", "url": "https://finance.detik.com/rss"},
    {"name": "Kontan Keuangan", "url": "https://rss.kontan.co.id/news/keuangan"},
]

# Economic Lexicon
LEXICON = {
    "positive": [
        "menguat", "naik", "surplus", "tumbuh", "stabil", "optimis", "ekspansi", 
        "membaik", "terkendali", "apresiasi", "investasi", "pemulihan", "untung", 
        "bergairah", "melesat", "positif", "cerah", "meningkat"
    ],
    "negative": [
        "melemah", "turun", "defisit", "inflasi", "kontraksi", "pesimis", "krisis", 
        "anjlok", "terpuruk", "depresiasi", "ketidakpastian", "perlambatan", "rugi", 
        "waspada", "tekanan", "tertekan", "negatif", "suram", "menurun"
    ]
}

def init_db():
    with open("schema.sql", "r") as f:
        schema = f.read()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema)
    conn.close()

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text

def calculate_sentiment(text: str) -> Dict:
    cleaned = clean_text(text)
    words = cleaned.split()
    
    pos_count = sum(1 for word in words if word in LEXICON["positive"])
    neg_count = sum(1 for word in words if word in LEXICON["negative"])
    
    total = pos_count + neg_count
    if total == 0:
        score = 0.0
        label = "Neutral"
    else:
        score = (pos_count - neg_count) / total
        if score > 0.05:
            label = "Positive"
        elif score < -0.05:
            label = "Negative"
        else:
            label = "Neutral"
            
    return {"score": score, "label": label}

def fetch_news():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for feed in RSS_FEEDS:
        print(f"Fetching from {feed['name']}...")
        parsed = feedparser.parse(feed['url'])
        
        for entry in parsed.entries:
            title = entry.title
            link = entry.link
            published = entry.get('published', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            content = entry.get('summary', '')
            
            # Sentiment Analysis
            sentiment = calculate_sentiment(title + " " + content)
            
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO news (title, link, published_at, source, content, sentiment_score, sentiment_label)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (title, link, published, feed['name'], content, sentiment['score'], sentiment['label']))
            except Exception as e:
                print(f"Error inserting {link}: {e}")
                
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    while True:
        print(f"[{datetime.now()}] Starting news fetch...")
        fetch_news()
        print(f"[{datetime.now()}] Fetch complete. Sleeping for 30 minutes.")
        time.sleep(1800)
