import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
import json
import yfinance as yf

# ================= PAGE CONFIG =================
st.set_page_config(page_title="AI Trading Terminal", layout="wide")
st.title("📊 AI Trading Terminal  — Live AI Trader + TP/SL")

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
            yf_ticker = "^DJI"          # Dow Jones Industrial Average
        else:
            yf_ticker = f"{symbol.upper()}=X"   # e.g. EURUSD=X

        try:
            # Download recent 15-min data
            hist = yf.download(yf_ticker, period="7d", interval="15m", progress=False)

            if hist.empty or len(hist) < 40:
                st.error("Not enough recent data available. Try again later.")
            else:
                # Latest values
                current_price = hist['Close'].iloc[-1]
                prec = 0 if market_type == "US30" else 4
                current_price_display = round(current_price, prec)

                # Key levels from recent price action
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

                # Indicators
                sma20 = hist['Close'].rolling(20).mean().iloc[-1]
                rsi   = 50.0  # fallback
                delta = hist['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = -delta.where(delta < 0, 0).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]

                # Trading logic
                if current_price > sma20 and rsi < 68:
                    bias = "Bullish"
                    entry = max(current_price, support_levels[1])   # better to enter near support
                    sl    = round(min(support_levels[0], entry - atr * 1.3), prec)
                    risk  = entry - sl
                    tp1   = round(entry + risk * 1.0, prec)
                    tp2   = round(entry + risk * rr_ratio, prec)
                    entry_text = f"**LONG** — consider entry near **{entry:.{prec}f}** (pullback to support or current if strong)"
                    pred_text  = f"Uptrend intact (above SMA20, RSI not overbought). Targets: TP1 **{tp1:.{prec}f}**, TP2 **{tp2:.{prec}f}**"

                elif current_price < sma20 and rsi > 32:
                    bias = "Bearish"
                    entry = min(current_price, resistance_levels[0])
                    sl    = round(max(resistance_levels[1], entry + atr * 1.3), prec)
                    risk  = sl - entry
                    tp1   = round(entry - risk * 1.0, prec)
                    tp2   = round(entry - risk * rr_ratio, prec)
                    entry_text = f"**SHORT** — consider entry near **{entry:.{prec}f}** (rally to resistance or current if weak)"
                    pred_text  = f"Downtrend developing (below SMA20, RSI not oversold). Targets: TP1 **{tp1:.{prec}f}**, TP2 **{tp2:.{prec}f}**"

                else:
                    bias = "Neutral"
                    entry_text = "No clear directional edge — wait for breakout"
                    pred_text  = f"Range market. Key breakout levels: above **{resistance_levels[1]:.{prec}f}** or below **{support_levels[0]:.{prec}f}**"
                    sl = tp1 = tp2 = None

                # Save results
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

                st.success(f"Analysis complete — {yf_ticker} @ **{current_price_display}** • Bias: **{bias}**")

        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")

# ================= DISPLAY RESULTS =================
st.subheader("🧠 AI Trader Analysis")

if st.session_state.analysis_done:
    col1, col2 = st.columns([5, 3])

    with col1:
        st.markdown(f"""
**Current Price** (last 15-min close): **{st.session_state.current_price}**

**Support Levels** → {st.session_state.support_levels}  
**Resistance Levels** → {st.session_state.resistance_levels}  
**Liquidity Pool** ≈ {st.session_state.liquidity_pool}

**Market Bias** → **{st.session_state.bias}**

**Entry Suggestion**  
{st.session_state.entry_suggestion}

**Stop Loss** → {st.session_state.sl if st.session_state.sl is not None else "—"}  
**Take Profit 1** (1:1) → {st.session_state.tp1 if st.session_state.tp1 is not None else "—"}  
**Take Profit 2** ({rr_ratio}:1) → {st.session_state.tp2 if st.session_state.tp2 is not None else "—"}

**AI Trader Outlook**  
{st.session_state.prediction}
        """)

    with col2:
        st.caption(f"Data: {st.session_state.yf_ticker} • ATR ≈ {st.session_state.atr:.1f if market_type=='US30' else st.session_state.atr:.4f}")
        st.info("Re-run analysis to refresh with latest data")

else:
    st.info("Click the button above to start real-time analysis")

# ================= TRADINGVIEW WIDGET =================
st.subheader("📈 TradingView Chart with AI Levels")

symbol_clean = symbol.upper().replace(" ", "")

overlays = []
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

# ================= PLOTLY VISUAL =================
if st.session_state.analysis_done:
    st.subheader("📊 Recent Price Action + AI Levels")

    cp = st.session_state.current_price
    scale = 400 if market_type == "US30" else 0.004

    times = pd.date_range(end=datetime.now(pytz.UTC), periods=8, freq="15min")
    prices = [cp - scale*1.1, cp - scale*0.6, cp - scale*0.2, cp,
              cp + scale*0.3, cp + scale*0.7, cp + scale*1.0, cp]

    df = pd.DataFrame({"Time": times, "Price": prices})

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Price"],
                            mode="lines+markers", name="Price",
                            line=dict(color="#00ddff", width=2.5)))

    # Add levels
    level_styles = {
        "Support": ("orange", "dash"),
        "Resistance": ("red", "dash"),
        "Liquidity": ("lime", "dot"),
        "SL": ("purple", "dot"),
        "TP1": ("#00ff99", "solid"),
        "TP2": ("#00cc77", "solid")
    }

    for label, values, color, dash in [
        ("Support", st.session_state.support_levels, "orange", "dash"),
        ("Resistance", st.session_state.resistance_levels, "red", "dash"),
        ("Liquidity", [st.session_state.liquidity_pool], "lime", "dot"),
        ("SL", [st.session_state.sl], "purple", "dot"),
        ("TP1", [st.session_state.tp1], "#00ff99", "solid"),
        ("TP2", [st.session_state.tp2], "#00cc77", "solid"),
    ]:
        for v in values:
            if v is not None:
                fig.add_hline(y=v, line_dash=dash, line_color=color,
                              annotation_text=f"{label} {v:.{prec}f}",
                              annotation_position="right")

    fig.update_layout(
        height=520,
        template="plotly_dark",
        hovermode="x unified",
        xaxis_title="Time (approx)",
        yaxis_title="Price"
    )

    st.plotly_chart(fig, use_container_width=True)

st.caption("This is not financial advice • Always verify levels and use proper risk management")
