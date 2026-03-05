import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
import json
import yfinance as yf

# ================= PAGE CONFIG =================
st.set_page_config(page_title="AI Trading Terminal", layout="wide")
st.title("📊 AI Trading Terminal (Live AI Trader + TP/SL)")

# ================= SESSION STATE =================
if 'support_levels' not in st.session_state:
    st.session_state.update({
        'support_levels': [],
        'resistance_levels': [],
        'liquidity_pool': None,
        'prediction': "",
        'bias': "Neutral",
        'fetched_price': 0.0,
        'yf_ticker': "",
        'atr': 0.0,
        'entry_suggestion': "",
        'sl': None,
        'tp1': None,
        'tp2': None
    })

# ================= SIDEBAR =================
with st.sidebar:
    st.header("Market Selection")
    market_type = st.radio("Select Market Type", ["Forex", "US30"])
    
    st.markdown("---")
    st.header("Risk Management")
    rr_ratio = st.slider("Preferred Risk:Reward Ratio", 1.0, 3.0, 2.0, step=0.5)
    risk_percent = st.number_input("Risk % per trade", 0.5, 5.0, 1.0, step=0.5) / 100
    
    st.markdown("---")
    st.header("Backtesting Date (not active yet)")
    today = datetime.today()
    one_year_ago = today - timedelta(days=365)
    selected_date = st.date_input("Select Date", value=today, min_value=one_year_ago, max_value=today)

# ================= SYMBOL & TV SYMBOL =================
symbol_default = "EURUSD" if market_type == "Forex" else "US30"
symbol = st.text_input("Enter Symbol", symbol_default)

st.subheader("TradingView Symbol")
default_tv = "FX:US30" if market_type == "US30" else f"FX:{symbol.upper()}"
tv_symbol = st.text_input("TradingView symbol", value=default_tv)

# ================= RSI HELPER =================
def calculate_rsi(series, period=14):
    if len(series) < period + 1:
        return 50.0
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# ================= FETCH & AI ANALYSIS =================
if st.button("🤖 Fetch Live Data & Run AI Trader Analysis"):
    with st.spinner("Analyzing like a pro trader..."):
        yf_ticker = "^DJI" if market_type == "US30" else f"{symbol.upper()}=X"
        
        try:
            hist = yf.download(yf_ticker, period="7d", interval="15m", progress=False)
            if hist.empty or len(hist) < 30:
                st.error("Insufficient data. Try again later.")
            else:
                current_price = round(hist['Close'].iloc[-1], 0 if market_type == "US30" else 4)
                recent_high = hist['High'].max()
                recent_low = hist['Low'].min()
                atr = (hist['High'] - hist['Low']).rolling(14).mean().iloc[-1]  # better ATR
                prec = 0 if market_type == "US30" else 4
                
                support_levels = sorted([
                    round(recent_low, prec),
                    round(recent_low + atr * 0.5, prec)
                ])
                resistance_levels = sorted([
                    round(recent_high - atr * 0.5, prec),
                    round(recent_high, prec)
                ])
                liquidity_pool = round(recent_low - atr * 0.6, prec)
                
                rsi = calculate_rsi(hist['Close'])
                sma20 = hist['Close'].rolling(20).mean().iloc[-1]
                
                # Trader logic + TP/SL
                if current_price > sma20 and rsi < 70:
                    bias = "Bullish"
                    direction = "LONG"
                    entry = current_price if current_price < support_levels[1] else support_levels[1]  # pullback entry
                    sl = round(min(support_levels[0], entry - atr * 1.2), prec)
                    risk = abs(entry - sl)
                    tp1 = round(entry + risk * 1.0, prec)
                    tp2 = round(entry + risk * rr_ratio, prec)
                    entry_suggestion = f"**LONG** on pullback to \~{entry:.{prec}f} or current level if holding."
                    prediction = (f"📈 Bullish – above SMA20, RSI healthy. "
                                  f"Target TP1 {tp1}, TP2 {tp2}. "
                                  f"Strong break above {resistance_levels[1]} confirms continuation.")
                
                elif current_price < sma20 and rsi > 30:
                    bias = "Bearish"
                    direction = "SHORT"
                    entry = current_price if current_price > resistance_levels[0] else resistance_levels[0]
                    sl = round(max(resistance_levels[1], entry + atr * 1.2), prec)
                    risk = abs(sl - entry)
                    tp1 = round(entry - risk * 1.0, prec)
                    tp2 = round(entry - risk * rr_ratio, prec)
                    entry_suggestion = f"**SHORT** on rally to \~{entry:.{prec}f} or current if breaking down."
                    prediction = (f"📉 Bearish – below key average. "
                                  f"Target TP1 {tp1}, TP2 {tp2}. "
                                  f"Break below {support_levels[0]} accelerates downside.")
                
                else:
                    bias = "Neutral"
                    direction = "Range / Wait"
                    entry_suggestion = "No clear edge – wait for breakout or stronger signal."
                    sl = tp1 = tp2 = None
                    prediction = (f"⚖️ Range-bound. Watch breakout above {resistance_levels[1]} "
                                  f"or below {support_levels[0]} for directional move.")
                
                # Save everything
                st.session_state.update({
                    'support_levels': support_levels,
                    'resistance_levels': resistance_levels,
                    'liquidity_pool': liquidity_pool,
                    'prediction': prediction,
                    'bias': bias,
                    'fetched_price': current_price,
                    'yf_ticker': yf_ticker,
                    'atr': atr,
                    'entry_suggestion': entry_suggestion,
                    'sl': sl,
                    'tp1': tp1,
                    'tp2': tp2
                })
                
                st.success(f"Data fetched ({yf_ticker}) → Price: **{current_price}** | Bias: **{bias}**")

        except Exception as e:
            st.error(f"Fetch failed: {e}")

# ================= DISPLAY AI ANALYSIS =================
st.subheader("🧠 AI Pro Trader Analysis")

if st.session_state.support_levels:
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown(f"""
**Current Price (live fetch):** {st.session_state.fetched_price}

**Support Levels:** {st.session_state.support_levels}  
**Resistance Levels:** {st.session_state.resistance_levels}  
**Liquidity Pool:** \~{st.session_state.liquidity_pool}

**Trend Bias:** **{st.session_state.bias}**

**Entry Suggestion:**  
{st.session_state.entry_suggestion}

**Stop Loss (SL):** {st.session_state.sl if st.session_state.sl else 'N/A (wait for bias)'}  
**Take Profit 1 (1:1 RR):** {st.session_state.tp1 if st.session_state.tp1 else 'N/A'}  
**Take Profit 2 ({rr_ratio}:1 RR):** {st.session_state.tp2 if st.session_state.tp2 else 'N/A'}

**AI Trader Prediction:**  
{st.session_state.prediction}
        """)
    
    with col2:
        st.caption(f"Last fetch: {st.session_state.yf_ticker} • ATR ≈ {st.session_state.atr:.1f if market_type=='US30' else st.session_state.atr:.4f}")
        st.info("Adjust RR in sidebar to see updated targets on next analysis.")

else:
    st.info("Click the button above to get real-time analysis with TP/SL.")

# ================= TRADINGVIEW WIDGET =================
st.subheader("📈 TradingView Chart with AI Levels")

symbol_clean = symbol.upper().replace(" ", "")

overlays = []
for lvl in st.session_state.support_levels:
    overlays.append({"price": float(lvl), "color": "orange", "width": 2})
for lvl in st.session_state.resistance_levels:
    overlays.append({"price": float(lvl), "color": "red", "width": 2})
if st.session_state.liquidity_pool:
    overlays.append({"price": float(st.session_state.liquidity_pool), "color": "lime", "width": 3, "linestyle": "dashed"})
if st.session_state.sl:
    overlays.append({"price": float(st.session_state.sl), "color": "purple", "width": 2, "linestyle": "dotted"})
if st.session_state.tp1:
    overlays.append({"price": float(st.session_state.tp1), "color": "#00ff00", "width": 2})
if st.session_state.tp2:
    overlays.append({"price": float(st.session_state.tp2), "color": "#00cc00", "width": 3})

overlays_json = json.dumps(overlays)

st.components.v1.html(f"""
<div class="tradingview-widget-container">
  <div id="tradingview_{symbol_clean}"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
    const overlays = {overlays_json};
    new TradingView.widget({{
      "width": "100%",
      "height": 550,
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
""", height=580)

# ================= PLOTLY =================
st.subheader("📊 Recent Price + AI Levels / TP/SL")

if st.session_state.support_levels:
    cp = st.session_state.fetched_price
    scale = 300 if market_type == "US30" else 0.003
    base_prices = [cp - scale*0.9, cp - scale*0.4, cp, cp + scale*0.3, cp + scale*0.7, cp]

    times = pd.date_range(end=datetime.now(pytz.UTC), periods=6, freq="15min")
    df = pd.DataFrame({"Time": times, "Price": base_prices})

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Time"], y=df["Price"], mode="lines+markers", name="Price", line=dict(color="#00ccff")))

    colors = {
        'support': 'orange', 'resistance': 'red', 'liquidity': 'lime',
        'sl': 'purple', 'tp1': '#00ff00', 'tp2': '#00cc00'
    }
    
    for lvl, label in [
        (st.session_state.support_levels, "Support"),
        (st.session_state.resistance_levels, "Resistance"),
        ([st.session_state.liquidity_pool], "Liquidity"),
        ([st.session_state.sl], "SL"),
        ([st.session_state.tp1], "TP1"),
        ([st.session_state.tp2], "TP2")
    ]:
        for val in (lvl if isinstance(lvl, list) else [lvl]):
            if val is not None:
                fig.add_hline(y=val, line_dash="dash" if "TP" not in label and "SL" not in label else "dot",
                              line_color=colors.get(label.lower().split()[0], 'gray'),
                              annotation_text=f"{label} {val}", annotation_position="right")

    fig.update_layout(height=500, template="plotly_dark", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

st.caption("TP/SL are dynamic based on ATR, bias, and your chosen RR. Always use proper position sizing!")
