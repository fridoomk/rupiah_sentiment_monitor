import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Page Config
st.set_page_config(page_title="Rupiah & Inflation Sentiment Monitor", layout="wide")

# Database Connection
DB_PATH = "data/sentiment.db"

# Custom Indonesian Stopwords untuk membersihkan Word Cloud
INDONESIAN_STOPWORDS = set([
    'yang', 'di', 'dan', 'itu', 'dengan', 'untuk', 'ini', 'dari', 'dalam', 
    'akan', 'ke', 'adalah', 'bisa', 'jadi', 'diri', 'pada', 'sebagai', 
    'oleh', 'juga', 'telah', 'ia', 'saat', 'hal', 'bukan', 'tak', 'namun', 
    'serta', 'atau', 'karena', 'bila', 'jika', 'hingga', 'sebut', 'makin', 
    'usai', 'warga', 'kena', 'bikin', 'mau', 'masih', 'ada', 'soal', 'lagi', 
    'baru', 'hari', 'pakai', 'cuma', 'lewat', 'begini', 'punya', 'ungkap',
    'banyak', 'secara', 'tersebut', 'juta', 'ribu', 'minta', 'kembali', 
    'terkait', 'dapat', 'para', 'sebuah', 'menurut', 'kata', 'ke', 'ia'
])

def load_data():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM news ORDER BY created_at DESC"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Header
st.title("🇮🇩 Rupiah & Inflation Sentiment Monitor")
st.markdown("Real-time sentiment analysis of Indonesian economic news for professional portfolio monitoring.")

# Sidebar
st.sidebar.header("Filters")
days = st.sidebar.slider("Select Data Range (Days)", 1, 30, 7)

# Load Data
try:
    df = load_data()
    
    # Memastikan format datetime aman & menangani fluktuasi format string timezone
    df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize(None)
    
    # Ambil titik waktu acuan dari data terbaru yang masuk di database (Lebih aman dari timezone server)
    latest_time = df['created_at'].max() if not df.empty else datetime.now()
    
    # Filter data berdasarkan slider di sidebar
    df_filtered = df[df['created_at'] > (latest_time - timedelta(days=days))]

    # Metric Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        # Menghitung total berita dalam 24 jam terakhir dari waktu data terbaru
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
    tab1, tab2, tab3 = st.tabs(["📈 Trends", "☁️ Word Cloud", "📰 Latest News"])

    with tab1:
        st.subheader(f"Sentiment Trends (Last {days} Days)")
        if not df_filtered.empty:
            # PERBAIKAN: Menggunakan 'h' kecil untuk resample hourly dan basis data dinamis sesuai slider
            df_trends = df_filtered.set_index('created_at').resample('h')['sentiment_score'].mean().reset_index()
            
            # Jika rentang hari terlalu panjang, resample diubah ke harian ('d') otomatis agar grafik rapi
            if days > 7:
                df_trends = df_filtered.set_index('created_at').resample('d')['sentiment_score'].mean().reset_index()
            
            # Interpolasi linear jika ada jam kosong tanpa berita agar grafik tidak putus
            df_trends['sentiment_score'] = df_trends['sentiment_score'].interpolate(method='linear')
            
            fig = px.line(df_trends, x='created_at', y='sentiment_score', title="Sentiment Score Timeline")
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for the selected range.")

    with tab2:
        st.subheader("Dominant Economic Issues")
        if not df_filtered.empty:
            text = " ".join(df_filtered['title'].astype(str).tolist())
            if text.strip():
                # PERBAIKAN: Menyisipkan parameter stopwords di sini
                wordcloud = WordCloud(
                    width=800, 
                    height=400, 
                    background_color='white', 
                    colormap='viridis',
                    stopwords=INDONESIAN_STOPWORDS
                ).generate(text)
                
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
            # Memastikan kolom yang dipanggil ada di dataframe
            available_cols = [col for col in ['created_at', 'source', 'title', 'sentiment_label'] if col in df_filtered.columns]
            st.dataframe(df_filtered[available_cols].head(20), use_container_width=True)
        else:
            st.info("No headlines found for this date range.")

except Exception as e:
    st.error(f"Database error or uninitialized. Please ensure the ingestion script has run. Technical Details: {e}")

# Footer
st.markdown("---")
st.caption("Data source: RSS Feeds from Antara, CNBC Indonesia, CNN Indonesia, Detik Finance, and Kontan.")