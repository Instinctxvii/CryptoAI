import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
import json
import yfinance as yf

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

# ================= SYMBOL INPUTS =================
symbol_default = "EURUSD" if market_type == "Forex" else "US30"
symbol = st.text_input("Symbol", value=symbol_default)

# Reliable fallback symbols for TradingView widget
tv_fallback = "TVC:DJI" if market_type == "US30" else "FX:EURUSD"
tv_default = tv_fallback if market_type == "US30" else f"FX:{symbol.upper()}"
tv_symbol_input = st.text_input("TradingView Symbol", value=tv_default)

# Use fallback if input looks invalid/empty
tv_symbol = tv_symbol_input.strip() if tv_symbol_input.strip() else tv_fallback

# ================= MAIN BUTTON =================
if st.button("📡 Fetch Data & Run AI Trader Analysis", type="primary"):
    with st.spinner("Fetching & analyzing..."):
        yf_ticker = "^DJI" if market_type == "US30" else f"{symbol.upper()}=X"

        try:
            hist = yf.download(yf_ticker, period="7d", interval="15m", progress=False)

            if hist.empty or len(hist) < 20:
                st.error(f"Not enough data for {yf_ticker}. Check symbol or try later.")
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

                # Safer RSI calculation
                delta = hist['Close'].diff(1)
                gain = delta.where(delta > 0, 0.0)
                loss = -delta.where(delta < 0, 0.0)

                avg_gain = gain.rolling(window=14, min_periods=1).mean()
                avg_loss = loss.rolling(window=14, min_periods=1).mean()

                rs = avg_gain / avg_loss.where(avg_loss != 0, 1e-10)  # tiny value to avoid inf
                rsi_series = 100.0 - (100.0 / (1.0 + rs))

                rsi = rsi_series.iloc[-1] if len(rsi_series) > 0 and not pd.isna(rsi_series.iloc[-1]) else 50.0

                sma20 = hist['Close'].rolling(20, min_periods=1).mean().iloc[-1]

                # Trading logic
                if current_price > sma20 and rsi < 68:
                    bias = "Bullish"
                    entry = max(current_price, support_levels[1])
                    sl    = round(min(support_levels[0], entry - atr * 1.3), prec)
                    risk  = entry - sl
                    tp1   = round(entry + risk * 1.0, prec)
                    tp2   = round(entry + risk * rr_ratio, prec)
                    entry_text = f"**LONG** near **{entry:.{prec}f}**"
                    pred_text  = f"Uptrend likely. TP1 **{tp1:.{prec}f}** • TP2 **{tp2:.{prec}f}**"

                elif current_price < sma20 and rsi > 32:
                    bias = "Bearish"
                    entry = min(current_price, resistance_levels[0])
                    sl    = round(max(resistance_levels[1], entry + atr * 1.3), prec)
                    risk  = sl - entry
                    tp1   = round(entry - risk * 1.0, prec)
                    tp2   = round(entry - risk * rr_ratio, prec)
                    entry_text = f"**SHORT** near **{entry:.{prec}f}**"
                    pred_text  = f"Downtrend likely. TP1 **{tp1:.{prec}f}** • TP2 **{tp2:.{prec}f}**"

                else:
                    bias = "Neutral"
                    entry_text = "Wait for breakout"
                    pred_text  = f"Range. Watch **{resistance_levels[1]:.{prec}f}** up or **{support_levels[0]:.{prec}f}** down"
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

                st.success(f"Done — {yf_ticker} @ **{current_price_display}** • **{bias}**")

        except Exception as e:
            st.error(f"Fetch/analysis failed: {str(e)}\nTicker used: {yf_ticker}")

# ================= DISPLAY ANALYSIS =================
st.subheader("🧠 AI Trader Analysis")

if st.session_state.analysis_done:
    st.markdown(f"""
**Price**: **{st.session_state.current_price}**  
**Bias**: **{st.session_state.bias}**  

**Support**: {st.session_state.support_levels}  
**Resistance**: {st.session_state.resistance_levels}  
**Liquidity ≈**: {st.session_state.liquidity_pool}

**Entry**: {st.session_state.entry_suggestion}  
**SL**: {st.session_state.sl if st.session_state.sl is not None else "—"}  
**TP1 (1:1)**: {st.session_state.tp1 if st.session_state.tp1 is not None else "—"}  
**TP2 ({rr_ratio}:1)**: {st.session_state.tp2 if st.session_state.tp2 is not None else "—"}

**Outlook**: {st.session_state.prediction}
    """)
else:
    st.info("Click the button to fetch live data and get analysis.")

# ================= TRADINGVIEW CHART – ALWAYS VISIBLE =================
st.subheader("📈 TradingView Chart")

symbol_clean = symbol.replace(" ", "").upper()

overlays = []
if st.session_state.analysis_done:
    for lvl in st.session_state.support_levels:
        overlays.append({"price": float(lvl), "color": "orange", "width": 2})
    for lvl in st.session_state.resistance_levels:
        overlays.append({"price": float(lvl), "color": "red", "width": 2})
    if st.session_state.liquidity_pool is not None:
        overlays.append({"price": float(st.session_state.liquidity_pool), "color": "lime", "width": 3, "linestyle": "dashed"})
    if st.session_state.sl is not None:
        overlays.append({"price": float(st.session_state.sl), "color": "purple", "width": 2, "linestyle": "dotted"})
    if st.session_state.tp1 is not None:
        overlays.append({"price": float(st.session_state.tp1), "color": "#00ff88", "width": 2})
    if st.session_state.tp2 is not None:
        overlays.append({"price": float(st.session_state.tp2), "color": "#00cc66", "width": 3})

overlays_json = json.dumps(overlays)

st.components.v1.html(f"""
<div class="tradingview-widget-container">
  <div id="tradingview_{symbol_clean}"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
    new TradingView.widget({{
      "width": "100%",
      "height": 580,
      "symbol": "{tv_symbol}",
      "interval": "5",
      "timezone": "Etc/UTC",
      "theme": "dark",
      "style": "1",
      "locale": "en",
      "enable_publishing": false,
      "allow_symbol_change": true,
      "container_id": "tradingview_{symbol_clean}"
    }});
  </script>
</div>
""", height=620)

st.caption("Tip: If chart shows AAPL → check/change the TradingView Symbol field above to a valid one like TVC:DJI or FX:EURUSD")
