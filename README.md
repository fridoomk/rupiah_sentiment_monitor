# 🇮🇩 Rupiah & Inflation Sentiment Monitor

An automated pipeline that tracks Indonesian economic news sentiment in real-time and correlates it against live USD/IDR exchange rate movements. Built for self-hosting on a Linux VPS using Docker.

---

## Overview

The system continuously pulls economic news from major Indonesian outlets via RSS, scores each article using a domain-specific Indonesian lexicon, and surfaces the results through an interactive Streamlit dashboard — including a dual-axis sentiment vs. exchange rate chart and Pearson correlation analysis.

### Features

- **Automated ingestion** — fetches and stores headlines every 30 minutes from five RSS sources (CNBC Indonesia, Antara, CNN Indonesia, Detik Finance, Kontan)
- **Domain-tuned sentiment engine** — rule-based scoring calibrated for Indonesian economic vocabulary (e.g. `menguat`, `melemah`, `inflasi`, `depresiasi`)
- **SQL-level filtering** — all date-range queries are pushed to SQLite with indexed lookups; no full-table scans
- **Macro correlation chart** — synchronized dual-axis Plotly chart overlaying daily sentiment averages against live USD/IDR rates from Yahoo Finance
- **Pearson correlation metric** — quantifies and explains the relationship between media sentiment and currency movement for the selected window
- **Word cloud with N-gram support** — unigram, bigram, and trigram frequency analysis across headline text, with curated stopword filtering
- **Extreme sentiment highlights** — surfaces the top 3 most positive and most negative headlines for any selected date range
- **Dynamic KPI cards** — metric deltas comparing current vs. prior period for news volume and average sentiment score
- **Production-ready stack** — containerized with Docker, served behind an Nginx reverse proxy with WebSocket support for Streamlit

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Docker Host (VPS)                │
│                                                     │
│  ┌──────────────┐      ┌──────────────────────────┐ │
│  │ processor.py │      │        app.py            │ │
│  │  (ingestion) │      │   (Streamlit dashboard)  │ │
│  │              │      │                          │ │
│  │ RSS → SQLite │      │  SQLite → Plotly / WC    │ │
│  └──────┬───────┘      └──────────┬───────────────┘ │
│         │                         │                  │
│         └──────── ./data/ ────────┘  (bind mount)   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │              Nginx (port 80)                 │   │
│  │        reverse proxy → :8501                 │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

| Component | Role |
|---|---|
| `processor.py` | Background worker: RSS ingestion, sentiment scoring, SQLite writes |
| `app.py` | Streamlit dashboard: visualization, correlation, word cloud |
| `schema.sql` | SQLite schema with indexes on `created_at`, `published_at`, `sentiment_label` |
| `docker-compose.yml` | Orchestrates three services: dashboard, ingestion, nginx |
| `nginx.conf` | Reverse proxy with WebSocket upgrade headers for Streamlit |

---

## Tech Stack

- **Python 3.11** — runtime
- **Streamlit** — dashboard UI
- **Plotly** — interactive dual-axis charts
- **feedparser** — RSS ingestion
- **yfinance** — live USD/IDR exchange rate data
- **wordcloud + matplotlib** — N-gram word cloud rendering
- **SQLite** — lightweight embedded database
- **Docker + Nginx** — containerization and reverse proxy

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Git
- A Linux VPS (tested on Ubuntu 22.04; 1GB RAM is sufficient)

### Deployment

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/rupiah-sentiment-monitor.git
cd rupiah-sentiment-monitor

# 2. Start all services
docker-compose up -d

# 3. Verify containers are running
docker-compose ps
```

The dashboard will be available at `http://your-vps-ip` (port 80 via Nginx) or directly at `http://your-vps-ip:8501`.

On first boot, `processor.py` initializes the SQLite database and runs the first ingestion cycle automatically. The dashboard will display data within a few minutes.

### Stopping the stack

```bash
docker-compose down
```

Data persists in `./data/sentiment.db` across restarts via the bind mount.

---

## Dashboard Walkthrough

**Sidebar** — a day-range slider (1–120 days) controls the date window globally across all tabs.

**Tab 1 — Macro Trends Correlation**
Dual-axis chart showing daily average sentiment (left axis) alongside the USD/IDR closing rate (right axis) for the selected window. Below the chart, the Pearson correlation coefficient is displayed with a contextual macro interpretation (e.g. negative correlation = Rupiah weakens as pessimism rises).

**Tab 2 — Word Cloud**
N-gram frequency word cloud generated from headline text for the selected period, with curated stopword filtering to suppress media noise and retail terms. Below it, the three most positive and three most negative headlines are displayed for qualitative context.

**Tab 3 — Latest News**
Sortable table of the most recent 50 headlines with source, timestamp, sentiment label, and score.

---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS news (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    link            TEXT UNIQUE NOT NULL,
    published_at    DATETIME,
    source          TEXT,
    content         TEXT,
    sentiment_score REAL,
    sentiment_label TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_created_at      ON news(created_at);
CREATE INDEX IF NOT EXISTS idx_published_at    ON news(published_at);
CREATE INDEX IF NOT EXISTS idx_sentiment_label ON news(sentiment_label);
```

The `created_at` index is critical — all dashboard SQL queries filter on this column.

> **Existing database migration:** If upgrading from an earlier version that lacked the `idx_created_at` index, run this once:
> ```bash
> sqlite3 data/sentiment.db "CREATE INDEX IF NOT EXISTS idx_created_at ON news(created_at);"
> ```

---

## RSS Sources

| Source | Feed |
|---|---|
| Antara Ekonomi | `https://www.antaranews.com/rss/ekonomi.xml` |
| CNBC Indonesia | `https://www.cnbcindonesia.com/news/rss` |
| CNN Indonesia | `https://www.cnnindonesia.com/ekonomi/rss` |
| Detik Finance | `https://finance.detik.com/rss` |
| Kontan Keuangan | `https://rss.kontan.co.id/news/keuangan` |

---

## Production Notes

- **Memory footprint** — the rule-based sentiment engine requires no GPU or transformer model; the full stack runs comfortably on a 1GB RAM VPS
- **Caching** — `load_data()` and exchange rate fetches are cached with `@st.cache_data` (5-minute and 1-hour TTLs respectively) to minimize disk I/O and external API calls
- **Data persistence** — SQLite is mounted as a host bind volume at `./data/`, surviving container rebuilds and restarts
- **Duplicate prevention** — `INSERT OR IGNORE` on the `link UNIQUE` constraint ensures re-runs never double-count articles
- **Timezone handling** — `published_at` is normalized via feedparser's `published_parsed` struct to plain `YYYY-MM-DD HH:MM:SS`; `created_at` is set by SQLite as UTC and always timezone-naive

---

## Project Structure

```
rupiah-sentiment-monitor/
├── app.py               # Streamlit dashboard
├── processor.py         # RSS ingestion + sentiment engine
├── schema.sql           # SQLite schema and indexes
├── requirements.txt     # Python dependencies (pinned)
├── Dockerfile           # Python 3.11-slim image
├── docker-compose.yml   # Three-service orchestration
├── nginx.conf           # Reverse proxy config
└── data/                # Runtime only — gitignored
    └── sentiment.db
```

---

## License

MIT
