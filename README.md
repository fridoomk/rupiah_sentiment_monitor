# 🇮🇩 Rupiah & Inflation Sentiment Monitor

A professional Data Science portfolio project designed to monitor and analyze sentiment regarding the Indonesian Rupiah and inflation trends in real-time. This system is optimized for self-hosting on a Linux VPS using Docker.

## 🚀 Overview

The **Rupiah Sentiment Monitor** is an automated pipeline that fetches economic news from major Indonesian news outlets, performs rule-based sentiment analysis using a specialized economic lexicon, and visualizes the results in an interactive Streamlit dashboard.

### Key Features
- **Real-time Ingestion:** Fetches news every 30 minutes via RSS feeds from CNBC Indonesia, Antara, CNN Indonesia, and more.
- **Efficient Sentiment Engine:** Uses a dictionary-based approach tailored for Indonesian economic contexts (e.g., "menguat", "melemah", "inflasi").
- **Interactive Dashboard:** Built with Streamlit, featuring metric cards, time-series trends, and word clouds.
- **Production Ready:** Fully containerized with Docker and Nginx reverse proxy for easy deployment on VPS providers like Biznet.

## 🏗️ System Architecture

The project follows a modular architecture designed for low resource consumption:

1.  **Data Ingestion (`processor.py`):** A background worker that scrapes RSS feeds and stores data in SQLite.
2.  **Sentiment Engine:** A rule-based classifier that calculates sentiment scores based on a curated Indonesian economic lexicon.
3.  **Database (SQLite):** A lightweight, file-based database for portability and ease of sharing.
4.  **Dashboard (`app.py`):** A Streamlit application for data visualization.
5.  **Orchestration (Docker):** Containers for the application and Nginx reverse proxy.

## 📊 Economic Analysis: Rupiah Depreciation (May 2026)

As of May 2026, the Indonesian Rupiah has faced significant pressure, surpassing the psychological level of **Rp 17,500 per USD**. This depreciation is driven by several factors:
- **Global Monetary Policy:** Sustained high interest rates from the US Federal Reserve.
- **Geopolitical Tensions:** Instability in the Middle East leading to capital outflows from emerging markets.
- **Inflationary Pressure:** The weakening currency has increased the cost of imported goods and energy, putting upward pressure on domestic inflation.

This dashboard provides a quantitative look at how these events are reflected in public sentiment and media coverage.

## 🛠️ Installation & Deployment

### Prerequisites
- Docker and Docker Compose installed on your VPS.
- Git.

### Quick Start
1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/rupiah-sentiment-monitor.git
    cd rupiah_sentiment_monitor
    ```
2.  Deploy with a single command:
    ```bash
    docker-compose up -d
    ```
3.  Access the dashboard at `http://your-vps-ip`.

## ⚙️ Production Notes

- **Memory Efficiency:** By using a rule-based sentiment engine instead of a heavy LLM or Transformer model, the entire stack runs comfortably on a VPS with as little as 1GB of RAM.
- **Persistence:** The SQLite database is mounted as a Docker volume in `./data`, ensuring data persists across container restarts.
- **Reverse Proxy:** Nginx handles incoming traffic and provides a layer of security and scalability, with WebSocket support enabled for Streamlit's interactive features.

---
*Developed for professional Data Science portfolio demonstration.*
