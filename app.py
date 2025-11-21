import streamlit as st
import yfinance as yf
from textblob import TextBlob
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# Page Config
st.set_page_config(page_title="Stock Sentiment Agent", page_icon="📈", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
        margin-bottom: 10px;
    }
    .stMetric {
        background-color: #0e1117;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Helper Functions
def get_sentiment_color(score):
    if score > 0.1: return "green"
    elif score < -0.1: return "red"
    else: return "orange"

def get_sentiment_label(score):
    if score > 0.1: return "BULLISH 🚀"
    elif score < -0.1: return "BEARISH 📉"
    else: return "NEUTRAL 😐"

def format_large_number(num):
    if num is None: return "N/A"
    if num >= 1_000_000_000_000: return f"${num/1_000_000_000_000:.2f}T"
    if num >= 1_000_000_000: return f"${num/1_000_000_000:.2f}B"
    if num >= 1_000_000: return f"${num/1_000_000:.2f}M"
    return f"${num:.2f}"

# Sidebar
with st.sidebar:
    st.title("🤖 Stock Agent")
    
    # Pre-defined lists
    popular_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]
    
    selected_tickers = st.multiselect(
        "Select Stocks", 
        options=popular_tickers + ["AMD", "INTC", "NFLX", "SPY", "QQQ"],
        default=["TSLA"]
    )
    
    custom_ticker = st.text_input("Or type a ticker (e.g. COIN)")
    if custom_ticker:
        custom_ticker = custom_ticker.upper()
        if custom_ticker not in selected_tickers:
            selected_tickers.append(custom_ticker)

    st.markdown("---")
    st.markdown("### Features")
    st.markdown("- **Multi-Stock Comparison**")
    st.markdown("- **Real-time Prices**")
    st.markdown("- **Sentiment Analysis**")
    st.markdown("- **Fundamental Data**")

if not selected_tickers:
    st.info("👈 Select or enter a stock ticker to get started!")
    st.stop()

# Data Fetching
data = {}
for ticker in selected_tickers:
    data[ticker] = yf.Ticker(ticker)

# --- COMPARISON MODE (If > 1 ticker) ---
if len(selected_tickers) > 1:
    st.header("📊 Market Comparison")
    
    # Metrics Table
    cols = st.columns(len(selected_tickers))
    for idx, ticker in enumerate(selected_tickers):
        stock = data[ticker]
        info = stock.info
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        previous_close = info.get('previousClose', current_price)
        delta = current_price - previous_close
        delta_percent = (delta / previous_close) * 100 if previous_close else 0
        
        with cols[idx]:
            st.metric(
                label=ticker, 
                value=f"${current_price:.2f}", 
                delta=f"{delta_percent:.2f}%"
            )

    # Comparison Chart
    st.subheader("Price History Comparison (1 Month)")
    fig = go.Figure()
    for ticker in selected_tickers:
        hist = data[ticker].history(period="1mo")
        # Normalize to percentage change for better comparison
        if not hist.empty:
            start_price = hist['Close'].iloc[0]
            normalized_close = ((hist['Close'] - start_price) / start_price) * 100
            fig.add_trace(go.Scatter(x=hist.index, y=normalized_close, mode='lines', name=ticker))
    
    fig.update_layout(
        yaxis_title="Change (%)", 
        hovermode="x unified",
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- DEEP DIVE MODE (Iterate through tickers) ---
st.markdown("---")
st.header("🔎 Deep Dive Analysis")

tabs = st.tabs(selected_tickers)

for i, ticker in enumerate(selected_tickers):
    with tabs[i]:
        stock = data[ticker]
        info = stock.info
        
        # Fundamentals
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Market Cap", format_large_number(info.get('marketCap')))
        with col2: st.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")
        with col3: st.metric("52W High", f"${info.get('fiftyTwoWeekHigh', 0):.2f}")
        with col4: st.metric("Volume", format_large_number(info.get('volume')))

        # Sentiment
        news = stock.news
        total_polarity = 0
        analyzed_news = []
        
        if news:
            for item in news:
                title = item.get('title', '')
                if not title and 'content' in item: title = item['content'].get('title', '')
                link = item.get('link', '')
                publisher = item.get('publisher', 'Unknown')
                
                blob = TextBlob(title)
                polarity = blob.sentiment.polarity
                total_polarity += polarity
                analyzed_news.append({'title': title, 'link': link, 'publisher': publisher, 'polarity': polarity})
            
            avg_polarity = total_polarity / len(news)
        else:
            avg_polarity = 0

        st.subheader("Sentiment Analysis")
        s_col1, s_col2 = st.columns([1, 3])
        with s_col1:
            st.markdown(f"## {get_sentiment_label(avg_polarity)}")
            st.progress((avg_polarity + 1) / 2) # Normalize -1 to 1 -> 0 to 1
        
        with s_col2:
            with st.expander("Latest News & Sentiment Scores", expanded=True):
                for item in analyzed_news[:5]:
                    p_score = item['polarity']
                    p_emoji = "🟢" if p_score > 0.1 else "🔴" if p_score < -0.1 else "🟡"
                    st.markdown(f"{p_emoji} **[{item['title']}]({item['link']})**")
                    st.caption(f"Source: {item['publisher']} | Score: {p_score:.2f}")

        # Individual Chart
        st.subheader("Price Chart")
        hist = stock.history(period="6mo")
        if not hist.empty:
            fig = go.Figure(data=[go.Candlestick(x=hist.index,
                open=hist['Open'], high=hist['High'],
                low=hist['Low'], close=hist['Close'])])
            fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
