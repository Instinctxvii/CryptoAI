import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
import json
import yfinance as yf

# Workaround for yfinance cache permission issue on Streamlit Cloud
import appdirs
appdirs.user_cache_dir = lambda *args: "/tmp"

# ================= PAGE CONFIG =================
st.set_page_config(page_title="AI Trading Terminal", layout="wide")
st.title("📊 AI Trading Terminal — Live AI Trader + TP/SL")

# ================= SESSION STATE =================
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
    st.session_state.support_levels = []
    st.session_state.resistance_levels = []
    st.session_state.liquidity_pool = None
    st.session_state.bias = "Neutral"
    st.session_state.prediction = ""
    st.session_state.entry_suggestion = ""
    st.session_state.sl = None
    st.session_state.tp1 = None
    st.session_state.tp2 = None
    st.session_state.current_price = 0.0
    st.session_state.atr = 0.0
    st.session_state.yf_ticker = ""

# ================= SIDEBAR =================
with st.sidebar:
    st.header("Settings")
    market_type = st.radio("Market Type", ["Forex", "US30"], index=1)

    st.markdown("---")
    st.header("Risk Management")
    rr_ratio = st.slider("Risk:Reward Ratio", 1.0, 3.5, 2.0, step=0.5)
    risk_percent = st.number_input("Risk per trade (%)", 0.3, 5.0, 1.0, step=0.1) / 100

    st.markdown("---")
    st.caption("Data from Yahoo Finance • 15-min candles • Last 7 days")

# ================= SYMBOL INPUTS =================
symbol_default = "EURUSD" if market_type == "Forex" else "US30"
symbol = st.text_input("Symbol", value=symbol_default)

tv_default = "FX:US30" if market_type == "US30" else f"FX:{symbol.upper()}"
tv_symbol = st.text_input("TradingView Symbol (if different)", value=tv_default)

# ================= MAIN BUTTON =================
if st.button("📡 Fetch Data & Run AI Trader Analysis", type="primary"):
    with st.spinner("Fetching market data and analyzing..."):
        # Select Yahoo Finance ticker
        if market_type == "US30":
            yf_ticker = "^DJI"          # Dow Jones
        else:
            yf_ticker = f"{symbol.upper()}=X"   # e.g. EURUSD=X

        try:
            hist = yf.download(yf_ticker, period="7d", interval="15m", progress=False)

            if hist.empty or len(hist) < 40:
                st.error("Not enough recent data. Try again later.")
            else:
                current_price = hist['Close'].iloc[-1]
                prec = 0 if market_type == "US30" else 4
                current_price_display = round(current_price, prec)

                recent_high  = hist['High'].rolling(40).max().iloc[-1]
                recent_low   = hist['Low'].rolling(40).min().iloc[-1]
                atr = (hist['High'] - hist['Low']).rolling(14).mean().iloc[-1]

                support_levels = sorted([
                    round(recent_low, prec),
                    round(recent_low + atr * 0.6, prec)
                ])
                resistance_levels = sorted([
                    round(recent_high - atr * 0.6, prec),
                    round(recent_high, prec)
                ])
                liquidity_pool = round(recent_low - atr * 0.7, prec)

                # Simple RSI
                delta = hist['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = -delta.where(delta < 0, 0).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]

                sma20 = hist['Close'].rolling(20).mean().iloc[-1]

                if current_price > sma20 and rsi < 68:
                    bias = "Bullish"
                    entry = max(current_price, support_levels[1])
                    sl    = round(min(support_levels[0], entry - atr * 1.3), prec)
                    risk  = entry - sl
                    tp1   = round(entry + risk * 1.0, prec)
                    tp2   = round(entry + risk * rr_ratio, prec)
                    entry_text = f"**LONG** — consider entry near **{entry:.{prec}f}**"
                    pred_text  = f"Uptrend likely. Targets: TP1 **{tp1:.{prec}f}**, TP2 **{tp2:.{prec}f}**"

                elif current_price < sma20 and rsi > 32:
                    bias = "Bearish"
                    entry = min(current_price, resistance_levels[0])
                    sl    = round(max(resistance_levels[1], entry + atr * 1.3), prec)
                    risk  = sl - entry
                    tp1   = round(entry - risk * 1.0, prec)
                    tp2   = round(entry - risk * rr_ratio, prec)
                    entry_text = f"**SHORT** — consider entry near **{entry:.{prec}f}**"
                    pred_text  = f"Downtrend likely. Targets: TP1 **{tp1:.{prec}f}**, TP2 **{tp2:.{prec}f}**"

                else:
                    bias = "Neutral"
                    entry_text = "Wait for breakout"
                    pred_text  = f"Range-bound. Watch **{resistance_levels[1]:.{prec}f}** up or **{support_levels[0]:.{prec}f}** down"
                    sl = tp1 = tp2 = None

                st.session_state.update({
                    'analysis_done': True,
                    'support_levels': support_levels,
                    'resistance_levels': resistance_levels,
                    'liquidity_pool': liquidity_pool,
                    'bias': bias,
                    'prediction': pred_text,
                    'entry_suggestion': entry_text,
                    'sl': sl,
                    'tp1': tp1,
                    'tp2': tp2,
                    'current_price': current_price_display,
                    'atr': atr,
                    'yf_ticker': yf_ticker
                })

                st.success(f"Done — {yf_ticker} @ **{current_price_display}** • {bias}")

        except Exception as e:
            st.error(f"Data fetch failed: {str(e)}")

# ================= DISPLAY =================
st.subheader("🧠 AI Trader Analysis")

if st.session_state.analysis_done:
    st.markdown(f"""
**Price**: **{st.session_state.current_price}**  
**Bias**: **{st.session_state.bias}**  

**Support**: {st.session_state.support_levels}  
**Resistance**: {st.session_state.resistance_levels}  
**Liquidity \~**: {st.session_state.liquidity_pool}

**Entry**: {st.session_state.entry_suggestion}  
**SL**: {st.session_state.sl if st.session_state.sl else "—"}  
**TP1 (1:1)**: {st.session_state.tp1 if st.session_state.tp1 else "—"}  
**TP2 ({rr_ratio}:1)**: {st.session_state.tp2 if st.session_state.tp2 else "—"}

**Outlook**: {st.session_state.prediction}
    """)
else:
    st.info("Press the button above to analyze")

# (The rest — TradingView widget + Plotly chart — remains the same as before.
#  If you need that part too, let me know and I'll paste the complete version again.)

st.caption("Not financial advice — verify independently")
