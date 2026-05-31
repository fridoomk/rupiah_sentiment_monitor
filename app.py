import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import re
from collections import Counter
import yfinance as yf

# Page Config
st.set_page_config(page_title="Rupiah & Inflation Sentiment Monitor", layout="wide")

# Database Connection
DB_PATH = "data/sentiment.db"

# Custom Indonesian Stopwords
INDONESIAN_STOPWORDS = set([
    'yang', 'di', 'dan', 'itu', 'with', 'dengan', 'untuk', 'ini', 'dari', 'dalam', 
    'akan', 'ke', 'adalah', 'bisa', 'jadi', 'diri', 'pada', 'sebagai', 
    'oleh', 'juga', 'telah', 'ia', 'saat', 'hal', 'bukan', 'tak', 'namun', 
    'serta', 'atau', 'karena', 'bila', 'jika', 'hingga', 'sebut', 'makin', 
    'usai', 'warga', 'kena', 'bikin', 'mau', 'masih', 'ada', 'soal', 'lagi', 
    'baru', 'hari', 'pakai', 'cuma', 'lewat', 'begini', 'punya', 'ungkap',
    'banyak', 'secara', 'tersebut', 'juta', 'ribu', 'minta', 'kembali', 
    'terkait', 'dapat', 'para', 'sebuah', 'menurut', 'kata', 'maupun', 'serta',
    # Filter Media, Istilah Klik & Promo Retail
    'video', 'full', 'day', 'sale', 'diskon', 'breaking', 'news', 'live', 
    'transmart', 'cnbc', 'cnn', 'antara', 'detik', 'kontan', 'baca', 'klik', 
    'lihat', 'pantau', 'simak', 'berikut', 'menurut', 'terbaru', 'update',
    # Filter Noise Non-Ekonomi Baru
    'bos', 'buat', 'tiba', 'orang', 'jelang', 'per', 'buka'
])

# =============================================================================
# IMPROVEMENT 1: SQL-Level Filtering & Caching Optimization
# =============================================================================

def get_latest_time() -> datetime:
    """Lightweight scalar query to find the anchor timestamp without loading rows."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(created_at) FROM news")
        result = cursor.fetchone()[0]
        conn.close()
        if result:
            return pd.to_datetime(result).tz_localize(None)
    except Exception:
        pass
    return datetime.now()

@st.cache_data(ttl=300)
def load_data(start_date_str: str) -> pd.DataFrame:
    """Load news filtered at SQL level. Cached for 5 minutes to reduce disk I/O."""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM news WHERE created_at >= ? ORDER BY created_at DESC"
    df = pd.read_sql(query, conn, params=(start_date_str,))
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_today_yesterday_counts(today_str: str, yesterday_str: str) -> tuple:
    """Scalar query for metric card delta — avoids loading full rows."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM news WHERE created_at >= ?", (today_str,))
        today_count = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM news WHERE created_at >= ? AND created_at < ?",
            (yesterday_str, today_str)
        )
        yesterday_count = cursor.fetchone()[0]
        conn.close()
        return today_count, yesterday_count
    except Exception:
        return 0, 0

@st.cache_data(ttl=3600)
def get_usd_idr_data(start_date: str) -> pd.DataFrame:
    try:
        ticker = "IDR=X"
        df_kurs = yf.download(ticker, start=start_date, progress=False)
        df_kurs = df_kurs.reset_index()
        # Handle potensi multi-index columns dari yfinance versi terbaru
        df_kurs.columns = [col[0] if isinstance(col, tuple) else col for col in df_kurs.columns]
        df_kurs = df_kurs[['Date', 'Close']].rename(columns={'Date': 'date', 'Close': 'kurs_rupiah'})
        df_kurs['date'] = pd.to_datetime(df_kurs['date']).dt.date
        return df_kurs
    except Exception as e:
        st.warning(f"Gagal mengambil data kurs live dari Yahoo Finance: {e}")
        return pd.DataFrame(columns=['date', 'kurs_rupiah'])


# =============================================================================
# Header
# =============================================================================
st.title("🇮🇩 Rupiah & Inflation Sentiment Monitor")
st.markdown("Real-time sentiment analysis of Indonesian economic news for professional portfolio monitoring.")

# Sidebar
st.sidebar.header("Filters")
days = st.sidebar.slider("Select Data Range (Days) for Dashboard", 1, 120, 7)


# =============================================================================
# Main Logic
# =============================================================================
try:
    # Lightweight scalar query — no rows loaded yet
    latest_time = get_latest_time()

    start_date_target = (latest_time - timedelta(days=days)).date()
    start_date_str = start_date_target.strftime('%Y-%m-%d')

    today_str = latest_time.strftime('%Y-%m-%d')
    yesterday_str = (latest_time - timedelta(days=1)).strftime('%Y-%m-%d')

    # SQL-level filtered load (cached)
    df_filtered = load_data(start_date_str)
    if not df_filtered.empty:
        df_filtered['created_at'] = pd.to_datetime(df_filtered['created_at']).dt.tz_localize(None)

    # =========================================================================
    # IMPROVEMENT 4: Dynamic KPI Metric Cards with Delta Signaling
    # =========================================================================
    total_today, total_yesterday = load_today_yesterday_counts(today_str, yesterday_str)
    news_delta = total_today - total_yesterday

    avg_sentiment = df_filtered['sentiment_score'].mean() if not df_filtered.empty else 0.0
    avg_sentiment = float(avg_sentiment) if not pd.isna(avg_sentiment) else 0.0

    # Compute prior-period sentiment for delta comparison
    prior_start_str = (start_date_target - timedelta(days=days)).strftime('%Y-%m-%d')
    df_prior = load_data(prior_start_str)
    if not df_prior.empty:
        df_prior['created_at'] = pd.to_datetime(df_prior['created_at']).dt.tz_localize(None)
        df_prior_window = df_prior[df_prior['created_at'] < pd.to_datetime(start_date_str)]
        prior_sentiment = float(df_prior_window['sentiment_score'].mean()) if not df_prior_window.empty else 0.0
        if pd.isna(prior_sentiment):
            prior_sentiment = 0.0
    else:
        prior_sentiment = 0.0

    sentiment_delta = avg_sentiment - prior_sentiment

    sentiment_label = "Neutral"
    if avg_sentiment > 0.05:
        sentiment_label = "🟢 Positive"
    elif avg_sentiment < -0.05:
        sentiment_label = "🔴 Negative"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Total News (Today)",
            value=total_today,
            delta=f"{news_delta:+d} vs yesterday",
            delta_color="normal"
        )
    with col2:
        st.metric(
            label=f"Avg Sentiment Score ({days}d)",
            value=f"{avg_sentiment:.3f}",
            delta=f"{sentiment_delta:+.3f} vs prior period",
            delta_color="inverse" if avg_sentiment < -0.05 else "normal"
        )
    with col3:
        st.metric(
            label="Overall Sentiment",
            value=sentiment_label,
            delta=f"Score: {avg_sentiment:.3f}",
            delta_color="inverse" if avg_sentiment < -0.05 else "off"
        )

    # =========================================================================
    # Main Tabs
    # =========================================================================
    tab1, tab2, tab3 = st.tabs(["📈 Macro Trends Correlation", "☁️ Word Cloud", "📰 Latest News"])

    # =========================================================================
    # Tab 1: Macro Trends Correlation
    # =========================================================================
    with tab1:
        st.subheader("Analisis Korelasi Tren Sentimen vs Nilai Tukar Rupiah (USD/IDR)")
        st.markdown(
            f"Visualisasi sinkron bersumbu ganda menampilkan data selama "
            f"**{days} hari terakhir** (sejak {start_date_str})."
        )

        if not df_filtered.empty:
            df_macro_news = df_filtered.copy()
            df_macro_news['date'] = df_macro_news['created_at'].dt.date

            df_sentiment_daily = (
                df_macro_news.groupby('date')['sentiment_score']
                .mean()
                .reset_index()
                .rename(columns={'sentiment_score': 'avg_sentiment'})
            )

            df_kurs = get_usd_idr_data(start_date=start_date_str)

            if not df_kurs.empty:
                df_merged = pd.merge(
                    df_sentiment_daily, df_kurs, on='date', how='outer'
                ).sort_values('date')

                df_merged['kurs_rupiah'] = df_merged['kurs_rupiah'].interpolate(method='linear')
                df_merged['avg_sentiment'] = df_merged['avg_sentiment'].interpolate(method='linear')

                # Dual-axis chart
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                fig.add_trace(
                    go.Scatter(
                        x=df_merged['date'], y=df_merged['avg_sentiment'],
                        name='Rata-rata Sentimen Media',
                        line=dict(color='#1f77b4', width=2.5)
                    ),
                    secondary_y=False,
                )
                fig.add_trace(
                    go.Scatter(
                        x=df_merged['date'], y=df_merged['kurs_rupiah'],
                        name='Kurs USD/IDR (Yahoo Finance)',
                        line=dict(color='#d62728', width=2.5, dash='dash')
                    ),
                    secondary_y=True,
                )

                fig.update_layout(
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=40, r=40, t=40, b=40)
                )
                fig.update_yaxes(
                    title_text="<b>Skor Sentimen</b> (-1 Negatif s/d 1 Positif)",
                    color="#1f77b4", secondary_y=False
                )
                fig.update_yaxes(
                    title_text="<b>Nilai Kurs (IDR per 1 USD)</b>",
                    color="#d62728", secondary_y=True
                )

                st.plotly_chart(fig, use_container_width=True)

                # =============================================================
                # IMPROVEMENT 2: Pearson Correlation Metric
                # =============================================================
                df_corr = df_merged[['avg_sentiment', 'kurs_rupiah']].dropna()
                if len(df_corr) >= 3:
                    pearson_corr = df_corr['avg_sentiment'].corr(df_corr['kurs_rupiah'])

                    corr_col1, corr_col2 = st.columns([1, 3])
                    with corr_col1:
                        st.metric(
                            label="📐 Pearson Correlation\n(Sentiment vs USD/IDR)",
                            value=f"{pearson_corr:.4f}",
                            delta=(
                                "Negative = Rupiah weakens as sentiment drops"
                                if pearson_corr < 0
                                else "Positive = Rupiah strengthens as sentiment rises"
                            ),
                            delta_color="inverse" if pearson_corr < 0 else "normal"
                        )
                    with corr_col2:
                        if pearson_corr < -0.3:
                            st.info(
                                f"**Macroeconomic Insight:** A negative correlation of **{pearson_corr:.4f}** "
                                "indicates that as media sentiment drops (increased pessimism in coverage), "
                                "the USD/IDR exchange rate tends to rise — meaning the Rupiah weakens against "
                                "the Dollar. This is consistent with capital flight behavior during periods of "
                                "negative economic news coverage."
                            )
                        elif pearson_corr > 0.3:
                            st.success(
                                f"**Macroeconomic Insight:** A positive correlation of **{pearson_corr:.4f}** "
                                "suggests that improving media sentiment is tracking alongside Rupiah "
                                "appreciation — consistent with favorable investor confidence during "
                                "the selected period."
                            )
                        else:
                            st.warning(
                                f"**Note:** The correlation of **{pearson_corr:.4f}** is weak for this window, "
                                "suggesting sentiment and exchange rate movements are not strongly coupled. "
                                "Consider widening the date range slider for a more statistically meaningful sample."
                            )
                else:
                    st.info(
                        "Insufficient overlapping data points to compute Pearson correlation. "
                        "Try expanding the date range."
                    )
            else:
                st.info("Gagal menyandingkan data karena data kurs finansial kosong.")
        else:
            st.info(f"Belum ada data berita ekonomi di database untuk rentang {days} hari terakhir.")

    # =========================================================================
    # Tab 2: Word Cloud + Extreme Sentiment Context Highlights
    # =========================================================================
    with tab2:
        st.subheader("Dominant Economic Issues")
        if not df_filtered.empty:
            text = " ".join(df_filtered['title'].astype(str).tolist())
            if text.strip():
                # Preserve exact N-Gram processing logic (untouched)
                cleaned_text = text.lower()
                cleaned_text = re.sub(r'[^\w\s]', ' ', cleaned_text)
                cleaned_text = re.sub(r'\b\d+\b', ' ', cleaned_text)

                raw_words = cleaned_text.split()
                filtered_words = [w for w in raw_words if w not in INDONESIAN_STOPWORDS and len(w) > 2]

                word_frequencies = Counter(filtered_words)

                if len(filtered_words) >= 2:
                    bigrams = [" ".join(filtered_words[i:i+2]) for i in range(len(filtered_words)-1)]
                    word_frequencies.update(bigrams)

                if len(filtered_words) >= 3:
                    trigrams = [" ".join(filtered_words[i:i+3]) for i in range(len(filtered_words)-2)]
                    word_frequencies.update(trigrams)

                wordcloud = WordCloud(
                    width=800,
                    height=400,
                    background_color='white',
                    colormap='viridis'
                ).generate_from_frequencies(word_frequencies)

                fig_wc, ax = plt.subplots(figsize=(10, 5))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis("off")
                st.pyplot(fig_wc)
            else:
                st.info("Not enough textual data to generate word cloud.")

            # =================================================================
            # IMPROVEMENT 3: Extreme Sentiment Context Highlights
            # =================================================================
            st.markdown("---")
            st.markdown("### 🔍 Extreme Sentiment Context Highlights")
            st.caption(f"Top signal articles from the selected {days}-day window.")

            df_headlines = df_filtered[
                ['title', 'source', 'sentiment_score', 'sentiment_label', 'created_at']
            ].copy()
            df_headlines['created_at'] = pd.to_datetime(
                df_headlines['created_at']
            ).dt.strftime('%Y-%m-%d %H:%M')

            top_positive = df_headlines.nlargest(3, 'sentiment_score')
            top_negative = df_headlines.nsmallest(3, 'sentiment_score')

            hl_col1, hl_col2 = st.columns(2)

            with hl_col1:
                st.markdown("#### 🟢 Top 3 Positive Headlines")
                for _, row in top_positive.iterrows():
                    st.markdown(
                        f"""
                        <div style="border-left:4px solid #2ecc71; padding:8px 12px;
                                    margin-bottom:10px; background:rgba(46,204,113,0.07);
                                    border-radius:4px;">
                            <strong>{row['title']}</strong><br>
                            <small>📰 {row['source']} &nbsp;|&nbsp; 🕒 {row['created_at']}
                            &nbsp;|&nbsp; Score:
                            <b style="color:#27ae60">{row['sentiment_score']:.3f}</b></small>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            with hl_col2:
                st.markdown("#### 🔴 Top 3 Negative Headlines")
                for _, row in top_negative.iterrows():
                    st.markdown(
                        f"""
                        <div style="border-left:4px solid #e74c3c; padding:8px 12px;
                                    margin-bottom:10px; background:rgba(231,76,60,0.07);
                                    border-radius:4px;">
                            <strong>{row['title']}</strong><br>
                            <small>📰 {row['source']} &nbsp;|&nbsp; 🕒 {row['created_at']}
                            &nbsp;|&nbsp; Score:
                            <b style="color:#c0392b">{row['sentiment_score']:.3f}</b></small>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
        else:
            st.info("No data available to generate word cloud.")

    # =========================================================================
    # Tab 3: Latest News
    # =========================================================================
    with tab3:
        st.subheader("Latest Economic Headlines")
        if not df_filtered.empty:
            available_cols = [
                col for col in
                ['created_at', 'source', 'title', 'sentiment_label', 'sentiment_score']
                if col in df_filtered.columns
            ]
            st.dataframe(df_filtered[available_cols].head(50), use_container_width=True)
        else:
            st.info("No headlines found for this date range.")

except Exception as e:
    st.error(f"Database error or uninitialized. Technical Details: {e}")

# Footer
st.markdown("---")
st.caption(
    "Data source: RSS Feeds from Antara, CNBC Indonesia, CNN Indonesia, Detik Finance, and Kontan. "
    "Financial data from Yahoo Finance API."
)