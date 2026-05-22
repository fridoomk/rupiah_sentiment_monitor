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
    df['created_at'] = pd.to_datetime(df['created_at'])
    df_filtered = df[df['created_at'] > (datetime.now() - timedelta(days=days))]

    # Metric Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total News (Today)", len(df[df['created_at'] > (datetime.now() - timedelta(days=1))]))
    with col2:
        avg_sentiment = df_filtered['sentiment_score'].mean()
        st.metric("Avg Sentiment Score", f"{avg_sentiment:.2f}")
    with col3:
        sentiment_label = "Neutral"
        if avg_sentiment > 0.05: sentiment_label = "Positive"
        elif avg_sentiment < -0.05: sentiment_label = "Negative"
        st.metric("Overall Sentiment", sentiment_label)

    # Main Layout
    tab1, tab2, tab3 = st.tabs(["📈 Trends", "☁️ Word Cloud", "📰 Latest News"])

    with tab1:
        st.subheader("Sentiment Trends (Last 24 Hours)")
        df_24h = df[df['created_at'] > (datetime.now() - timedelta(days=1))]
        if not df_24h.empty:
            df_24h = df_24h.set_index('created_at').resample('H')['sentiment_score'].mean().reset_index()
            fig = px.line(df_24h, x='created_at', y='sentiment_score', title="Hourly Sentiment Score")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for the last 24 hours.")

    with tab2:
        st.subheader("Dominant Economic Issues")
        text = " ".join(df_filtered['title'].tolist())
        if text:
            wordcloud = WordCloud(width=800, height=400, background_color='white', colormap='viridis').generate(text)
            fig, ax = plt.subplots()
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis("off")
            st.pyplot(fig)
        else:
            st.info("Not enough data to generate word cloud.")

    with tab3:
        st.subheader("Latest Economic Headlines")
        st.dataframe(df_filtered[['created_at', 'source', 'title', 'sentiment_label']].head(20), use_container_width=True)

except Exception as e:
    st.error(f"Database not initialized or empty. Please run the processor script first. Error: {e}")

# Footer
st.markdown("---")
st.caption("Data source: RSS Feeds from Antara, CNBC Indonesia, CNN Indonesia, Detik Finance, and Kontan.")
