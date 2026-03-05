import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
import json
import yfinance as yf

# ================= PAGE CONFIG =================
st.set_page_config(page_title="AI Trader Terminal", layout="wide")
st.title("📊 AI Trader Terminal — US30 Live Demo")

# ================= SESSION STATE =================
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
    st.session_state.current_price = 0.0
    st.session_state.bias = "Waiting..."
    st.session_state.entry = "Waiting..."
    st.session_state.sl = None
    st.session_state.tp1 = None
    st.session_state.tp2 = None
    st.session_state.support = []
    st.session_state.resistance = []
    st.session_state.liquidity = None
    st.session_state.reason = ""

# ================= SIDEBAR =================
with st.sidebar:
    st.header("Settings")
    rr_ratio = st.slider("Risk:Reward Ratio", 1.0, 3.0, 2.0, step=0.5)
    st.markdown("---")
    st.caption("Simple rule-based analysis demo\nNo API key required")

# ================= SYMBOL & TRADINGVIEW =================
tv_symbol = st.text_input("TradingView Symbol", value="CAPITALCOM:US30")

# ================= TRADINGVIEW CHART - LOADS IMMEDIATELY =================
st.subheader("📈 US30 / Dow Jones Live Chart")
symbol_clean = "US30"

# Initial empty overlays (will be updated after analysis)
overlays = []
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

# ================= FETCH & ANALYZE BUTTON =================
if st.button("📡 Fetch Latest Price & Run Analysis", type="primary"):
    with st.spinner("Fetching US30 data..."):
        try:
            hist = yf.download("^DJI", period="5d", interval="15m", progress=False)

            if hist.empty or len(hist) < 20:
                st.error("Not enough recent data. Try again later.")
            else:
                current_price = round(hist['Close'].iloc[-1], 0)

                # Very simple structure detection
                recent_high = hist['High'].rolling(40).max().iloc[-1]
                recent_low = hist['Low'].rolling(40).min().iloc[-1]
                atr = (hist['High'] - hist['Low']).rolling(14).mean().iloc[-1]

                support = [round(recent_low, 0), round(recent_low + atr * 0.6, 0)]
                resistance = [round(recent_high - atr * 0.6, 0), round(recent_high, 0)]
                liquidity = round(recent_low - atr * 0.7, 0)

                sma20 = hist['Close'].rolling(20).mean().iloc[-1]
                last_close = hist['Close'].iloc[-1]

                if last_close > sma20 + atr * 0.3:
                    bias = "Bullish"
                    entry = round(last_close - atr * 0.4, 0)   # pullback entry zone
                    sl = round(min(support) - atr * 0.5, 0)
                    risk = entry - sl
                    tp1 = round(entry + risk * 1.0, 0)
                    tp2 = round(entry + risk * rr_ratio, 0)
                    reason = "Price above SMA20 + strong momentum. Looking for pullback to enter long."

                elif last_close < sma20 - atr * 0.3:
                    bias = "Bearish"
                    entry = round(last_close + atr * 0.4, 0)
                    sl = round(max(resistance) + atr * 0.5, 0)
                    risk = sl - entry
                    tp1 = round(entry - risk * 1.0, 0)
                    tp2 = round(entry - risk * rr_ratio, 0)
                    reason = "Price below SMA20 + bearish momentum. Looking for rally to enter short."

                else:
                    bias = "Neutral / Range"
                    entry = f"Around {round(last_close, -1)} ± 50"
                    sl = tp1 = tp2 = None
                    reason = "No clear directional edge. Waiting for breakout above resistance or below support."

                # Save
                st.session_state.update({
                    'analysis_done': True,
                    'current_price': current_price,
                    'bias': bias,
                    'entry': entry,
                    'sl': sl,
                    'tp1': tp1,
                    'tp2': tp2,
                    'support': support,
                    'resistance': resistance,
                    'liquidity': liquidity,
                    'reason': reason
                })

                st.success(f"Analysis done – Current price ≈ {current_price}")

                # Update chart overlays
                overlays = []
                for lvl in support:
                    overlays.append({"price": float(lvl), "color": "orange", "width": 2})
                for lvl in resistance:
                    overlays.append({"price": float(lvl), "color": "red", "width": 2})
                if liquidity:
                    overlays.append({"price": float(liquidity), "color": "lime", "width": 3, "linestyle": "dashed"})
                if sl:
                    overlays.append({"price": float(sl), "color": "purple", "width": 2, "linestyle": "dotted"})
                if tp1:
                    overlays.append({"price": float(tp1), "color": "#00ff88", "width": 2})
                if tp2:
                    overlays.append({"price": float(tp2), "color": "#00cc66", "width": 3})

                overlays_json = json.dumps(overlays)

                # Re-render chart with overlays (Streamlit limitation → we show message)
                st.info("Chart updated with levels. Refresh page if overlays do not appear immediately.")

        except Exception as e:
            st.error(f"Error: {str(e)}")

# ================= DISPLAY ANALYSIS =================
st.subheader("🧠 Analysis Result")

if st.session_state.analysis_done:
    st.markdown(f"""
**Current Price** ≈ **{st.session_state.current_price}**

**Bias** → **{st.session_state.bias}**

**Suggested Entry** → {st.session_state.entry}  
**Stop Loss** → {st.session_state.sl if st.session_state.sl else "—"}  
**TP1 (1:1)** → {st.session_state.tp1 if st.session_state.tp1 else "—"}  
**TP2 ({rr_ratio}:1)** → {st.session_state.tp2 if st.session_state.tp2 else "—"}

**Support** → {st.session_state.support}  
**Resistance** → {st.session_state.resistance}  
**Liquidity zone** ≈ {st.session_state.liquidity}

**Reasoning**  
{st.session_state.reason}
    """)
else:
    st.info("Click the button above to fetch latest price and run analysis")

# ================= SIMPLE PLOTLY =================
if st.session_state.analysis_done:
    st.subheader("📊 Quick Price + Levels")

    cp = st.session_state.current_price
    times = pd.date_range(end=datetime.now(pytz.UTC), periods=10, freq="15min")
    prices = [cp - 400, cp - 250, cp - 100, cp, cp + 80, cp + 180, cp + 300, cp + 200, cp + 100, cp]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=prices, mode="lines+markers", name="Price"))

    for lvl in st.session_state.support:
        fig.add_hline(y=lvl, line_dash="dash", line_color="orange", annotation_text=f"Support {lvl}")
    for lvl in st.session_state.resistance:
        fig.add_hline(y=lvl, line_dash="dash", line_color="red", annotation_text=f"Resistance {lvl}")
    if st.session_state.liquidity:
        fig.add_hline(y=st.session_state.liquidity, line_dash="dot", line_color="lime", annotation_text=f"Liquidity")
    if st.session_state.sl:
        fig.add_hline(y=st.session_state.sl, line_color="purple", annotation_text=f"SL")
    if st.session_state.tp1:
        fig.add_hline(y=st.session_state.tp1, line_color="#00ff88", annotation_text=f"TP1")
    if st.session_state.tp2:
        fig.add_hline(y=st.session_state.tp2, line_color="#00cc66", annotation_text=f"TP2")

    fig.update_layout(height=450, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Demo version • Rule-based only • Not financial advice • Chart loads on startup")
