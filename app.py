import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
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

# Custom Indonesian Stopwords (Diperluas untuk membersihkan residu teks media & promo retail)
INDONESIAN_STOPWORDS = set([
    'yang', 'di', 'dan', 'itu', 'with', 'dengan', 'untuk', 'ini', 'dari', 'dalam', 
    'akan', 'ke', 'adalah', 'bisa', 'jadi', 'diri', 'pada', 'sebagai', 
    'oleh', 'juga', 'telah', 'ia', 'saat', 'hal', 'bukan', 'tak', 'namun', 
    'serta', 'atau', 'karena', 'bila', 'jika', 'hingga', 'sebut', 'makin', 
    'usai', 'warga', 'kena', 'bikin', 'mau', 'masih', 'ada', 'soal', 'lagi', 
    'baru', 'hari', 'pakai', 'cuma', 'lewat', 'begini', 'punya', 'ungkap',
    'banyak', 'secara', 'tersebut', 'juta', 'ribu', 'minta', 'kembali', 
    'terkait', 'dapat', 'para', 'sebuah', 'menurut', 'kata', 'maupun', 'serta',
    # Tambahan Filter Media, Istilah Klik & Promo Retail
    'video', 'full', 'day', 'sale', 'diskon', 'breaking', 'news', 'live', 
    'transmart', 'cnbc', 'cnn', 'antara', 'detik', 'kontan', 'baca', 'klik', 
    'lihat', 'pantau', 'simak', 'berikut', 'menurut', 'terbaru', 'update',
    # Filter Noise Non-Ekonomi Baru
    'bos', 'buat', 'tiba', 'orang', 'jelang', 'per', 'buka'
])

def load_data():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM news ORDER BY created_at DESC"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Fungsi Mengambil Data Kurs USD/IDR dari Yahoo Finance secara otomatis
@st.cache_data(ttl=3600)
def get_usd_idr_data(start_date="2026-02-01"):
    try:
        ticker = "IDR=X"
        df_kurs = yf.download(ticker, start=start_date)
        df_kurs = df_kurs.reset_index()
        # Handle potensi multi-index columns dari yfinance versi terbaru
        df_kurs.columns = [col[0] if isinstance(col, tuple) else col for col in df_kurs.columns]
        df_kurs = df_kurs[['Date', 'Close']].rename(columns={'Date': 'date', 'Close': 'kurs_rupiah'})
        df_kurs['date'] = pd.to_datetime(df_kurs['date']).dt.date
        return df_kurs
    except Exception as e:
        st.warning(f"Gagal mengambil data kurs live dari Yahoo Finance: {e}")
        return pd.DataFrame(columns=['date', 'kurs_rupiah'])

# Header
st.title("🇮🇩 Rupiah & Inflation Sentiment Monitor")
st.markdown("Real-time sentiment analysis of Indonesian economic news for professional portfolio monitoring.")

# Sidebar
st.sidebar.header("Filters")
days = st.sidebar.slider("Select Data Range (Days) for Cloud & Headlines", 1, 30, 7)

# Load Data
try:
    df = load_data()
    
    # Memastikan format datetime aman & menangani fluktuasi format string timezone
    df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize(None)
    
    # Ambil titik waktu acuan dari data terbaru yang masuk di database
    latest_time = df['created_at'].max() if not df.empty else datetime.now()
    
    # Filter data berdasarkan slider di sidebar (untuk Tab 2 & Tab 3)
    df_filtered = df[df['created_at'] > (latest_time - timedelta(days=days))]

    # Metric Cards (Tetap berbasis data terkini)
    col1, col2, col3 = st.columns(3)
    with col1:
        total_today = len(df[df['created_at'] > (latest_time - timedelta(days=1))])
        st.metric("Total News (Today)", total_today)
    with col2:
        avg_sentiment = df_filtered['sentiment_score'].mean() if not df_filtered.empty else 0.0
        st.metric("Avg Sentiment Score", f"{avg_sentiment:.2f}")
    with col3:
        sentiment_label = "Neutral"
        if avg_sentiment > 0.05: sentiment_label = "Positive"
        elif avg_sentiment < -0.05: sentiment_label = "Negative"
        st.metric("Overall Sentiment", sentiment_label)

    # Main Layout
    tab1, tab2, tab3 = st.tabs(["📈 Macro Trends Correlation", "☁️ Word Cloud", "📰 Latest News"])

    with tab1:
        st.subheader("Analisis Korelasi Tren Sentimen vs Nilai Tukar Rupiah (USD/IDR)")
        st.markdown("Grafik historis sumbu ganda memetakan dampak krisis eksogen sejak awal gejolak geopolitik (Februari 2026).")
        
        # Filter data sentimen khusus dari jangkar waktu Februari 2026 untuk menyandingkan data makro
        df_macro_news = df[df['created_at'] >= '2026-02-01'].copy()
        
        if not df_macro_news.empty:
            df_macro_news['date'] = df_macro_news['created_at'].dt.date
            # Agregasi skor sentimen harian
            df_sentiment_daily = df_macro_news.groupby('date')['sentiment_score'].mean().reset_index().rename(columns={'sentiment_score': 'avg_sentiment'})
            
            # Ambil data kurs USD/IDR dari Yahoo Finance
            df_kurs = get_usd_idr_data(start_date="2026-02-01")
            
            if not df_kurs.empty:
                # Gabungkan data berdasarkan tanggal berita dan tanggal pasar finansial terbuka
                df_merged = pd.merge(df_sentiment_daily, df_kurs, on='date', how='outer').sort_values('date')
                # Interpolasi linear jika ada gap hari libur pasar finansial (weekend)
                df_merged['kurs_rupiah'] = df_merged['kurs_rupiah'].interpolate(method='linear')
                df_merged['avg_sentiment'] = df_merged['avg_sentiment'].interpolate(method='linear')
                
                # Membuat Grafik Sumbu Ganda (Dual-Axis Chart)
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Trace 1: Rata-rata Skor Sentimen Berita (Sumbu Kiri)
                fig.add_trace(
                    go.Scatter(x=df_merged['date'], y=df_merged['avg_sentiment'], name='Rata-rata Sentimen Media',
                               line=dict(color='#1f77b4', width=2.5)),
                    secondary_y=False,
                )
                
                # Trace 2: Nilai Kurs USD/IDR (Sumbu Kanan)
                fig.add_trace(
                    go.Scatter(x=df_merged['date'], y=df_merged['kurs_rupiah'], name='Kurs USD/IDR (Yahoo Finance)',
                               line=dict(color='#d62728', width=2.5, dash='dash')),
                    secondary_y=True,
                )
                
                # Atur Layout Grafis
                fig.update_layout(
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=40, r=40, t=40, b=40)
                )
                
                fig.update_yaxes(title_text="<b>Skor Sentimen</b> (-1 Negatif s/d 1 Positif)", color="#1f77b4", secondary_y=False)
                fig.update_yaxes(title_text="<b>Nilai Kurs (IDR per 1 USD)</b>", color="#d62728", secondary_y=True)
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Gagal menyandingkan data karena data kurs finansial kosong.")
        else:
            st.info("Belum ada data berita ekonomi di database sejak Februari 2026.")

    with tab2:
        st.subheader("Dominant Economic Issues")
        if not df_filtered.empty:
            text = " ".join(df_filtered['title'].astype(str).tolist())
            if text.strip():
                # --- PROSESING N-GRAM KUSTOM ---
                cleaned_text = text.lower()
                cleaned_text = re.sub(r'[^\w\s]', ' ', cleaned_text)
                
                # Hapus Angka Berdiri Sendiri (Mencegah residu '2026', '000')
                cleaned_text = re.sub(r'\b\d+\b', ' ', cleaned_text)
                
                raw_words = cleaned_text.split()
                
                # Filter kata tunggal bermakna (bukan stopword & panjang > 2 karakter)
                filtered_words = [w for w in raw_words if w not in INDONESIAN_STOPWORDS and len(w) > 2]
                
                # Hitung frekuensi baseline kata tunggal (1-Gram)
                word_frequencies = Counter(filtered_words)
                
                # Ekstrak & gabungkan kombinasi 2 Kata (Bigrams)
                if len(filtered_words) >= 2:
                    bigrams = [" ".join(filtered_words[i:i+2]) for i in range(len(filtered_words)-1)]
                    word_frequencies.update(bigrams)
                    
                # Ekstrak & gabungkan kombinasi 3 Kata (Trigrams)
                if len(filtered_words) >= 3:
                    trigrams = [" ".join(filtered_words[i:i+3]) for i in range(len(filtered_words)-2)]
                    word_frequencies.update(trigrams)
                
                # Render Word Cloud menggunakan Dictionary Frekuensi Kustom
                wordcloud = WordCloud(
                    width=800, 
                    height=400, 
                    background_color='white', 
                    colormap='viridis'
                ).generate_from_frequencies(word_frequencies)
                
                fig, ax = plt.subplots()
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis("off")
                st.pyplot(fig)
            else:
                st.info("Not enough textual data to generate word cloud.")
        else:
            st.info("No data available to generate word cloud.")

    with tab3:
        st.subheader("Latest Economic Headlines")
        if not df_filtered.empty:
            available_cols = [col for col in ['created_at', 'source', 'title', 'sentiment_label'] if col in df_filtered.columns]
            st.dataframe(df_filtered[available_cols].head(20), use_container_width=True)
        else:
            st.info("No headlines found for this date range.")

except Exception as e:
    st.error(f"Database error or uninitialized. Technical Details: {e}")

# Footer
st.markdown("---")
st.caption("Data source: RSS Feeds from Antara, CNBC Indonesia, CNN Indonesia, Detik Finance, and Kontan. Financial data from Yahoo Finance API.")