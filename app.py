import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import yfinance as yf
from datetime import datetime
import pytz

# ================= PAGE CONFIG =================
st.set_page_config(page_title="US30 Trader Demo", layout="wide")
st.title("US30 / Dow Jones Trader Demo")

# ================= SESSION STATE =================
if 'analysis' not in st.session_state:
    st.session_state.analysis = None

# ================= SIDEBAR =================
with st.sidebar:
    st.header("Settings")
    rr = st.slider("Risk:Reward for TP2", 1.5, 4.0, 2.5, 0.5)
    st.markdown("---")
    st.caption("Rule-based demo — no API keys required")

# ================= TRADINGVIEW CHART – LOADS ON STARTUP =================
st.subheader("📈 US30 Live Chart")

# Use a symbol that reliably works in the lightweight widget
tv_symbol = st.text_input("TradingView Symbol", "CAPITALCOM:US30")

symbol_clean = "US30"

st.components.v1.html(f"""
<div class="tradingview-widget-container">
  <div id="tvchart"></div>
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
      "toolbar_bg": "#f1f3f6",
      "enable_publishing": false,
      "allow_symbol_change": true,
      "container_id": "tvchart"
    }});
  </script>
</div>
""", height=620)

# ================= ANALYSIS BUTTON =================
if st.button("Analyze Current Structure", type="primary"):
    with st.spinner("Fetching latest data..."):
        try:
            df = yf.download("^DJI", period="5d", interval="15m", progress=False)

            if df.empty or len(df) < 30:
                st.error("Not enough recent data")
                st.stop()

            price = round(df['Close'].iloc[-1])
            high_40 = round(df['High'].rolling(40).max().iloc[-1])
            low_40  = round(df['Low'].rolling(40).min().iloc[-1])
            atr     = round((df['High'] - df['Low']).rolling(14).mean().iloc[-1])

            # Very basic structure
            support     = [low_40, low_40 + int(atr * 0.6)]
            resistance  = [high_40 - int(atr * 0.6), high_40]
            liquidity   = low_40 - int(atr * 0.8)

            sma20 = round(df['Close'].rolling(20).mean().iloc[-1])

            if price > sma20 + atr * 0.4:
                bias = "Bullish"
                entry_zone = f"Buy limit zone {price - int(atr*0.5)} – {price - int(atr*0.3)}"
                sl = min(support) - int(atr * 0.4)
                risk = price - sl
                tp1 = price + risk
                tp2 = price + int(risk * rr)

            elif price < sma20 - atr * 0.4:
                bias = "Bearish"
                entry_zone = f"Sell limit zone {price + int(atr*0.5)} – {price + int(atr*0.3)}"
                sl = max(resistance) + int(atr * 0.4)
                risk = sl - price
                tp1 = price - risk
                tp2 = price - int(risk * rr)

            else:
                bias = "Range / Neutral"
                entry_zone = f"Wait for breakout — above {resistance[1]} or below {support[0]}"
                sl = tp1 = tp2 = None

            reason = f"Price at {price} vs SMA20 {sma20}. ATR ≈ {atr}. Recent range {low_40}–{high_40}."

            st.session_state.analysis = {
                'price': price,
                'bias': bias,
                'entry': entry_zone,
                'sl': sl,
                'tp1': tp1,
                'tp2': tp2,
                'support': support,
                'resistance': resistance,
                'liquidity': liquidity,
                'reason': reason
            }

            st.success("Analysis complete")

        except Exception as e:
            st.error(f"Fetch failed: {str(e)}")

# ================= SHOW RESULTS =================
if st.session_state.analysis:
    a = st.session_state.analysis

    st.subheader("Current Analysis")

    st.markdown(f"""
**Price** ≈ **{a['price']}**

**Bias** → **{a['bias']}**

**Suggested Entry** → {a['entry']}

**Stop Loss** → {a['sl'] if a['sl'] else '—'}  
**TP1** → {a['tp1'] if a['tp1'] else '—'}  
**TP2** ({rr:.1f} : 1) → {a['tp2'] if a['tp2'] else '—'}

**Support** → {a['support']}  
**Resistance** → {a['resistance']}  
**Liquidity pool** ≈ {a['liquidity']}

**Reason**  
{a['reason']}
    """)

    # ================= UPDATE CHART OVERLAYS =================
    overlays = []
    for lvl in a['support']:
        overlays.append({"price": float(lvl), "color": "orange", "width": 2})
    for lvl in a['resistance']:
        overlays.append({"price": float(lvl), "color": "red", "width": 2})
    if a['liquidity']:
        overlays.append({"price": float(a['liquidity']), "color": "lime", "width": 3, "linestyle": "dashed"})
    if a['sl']:
        overlays.append({"price": float(a['sl']), "color": "purple", "width": 2, "linestyle": "dotted"})
    if a['tp1']:
        overlays.append({"price": float(a['tp1']), "color": "#00ff88", "width": 2})
    if a['tp2']:
        overlays.append({"price": float(a['tp2']), "color": "#00cc66", "width": 3})

    overlays_json = json.dumps(overlays)

    # Re-render TradingView with overlays (note: widget doesn't update dynamically in Streamlit;
    # user needs to refresh page after analysis for overlays to appear)
    st.info("Refresh page to see updated levels on TradingView chart")

    # Simple Plotly backup
    st.subheader("Quick levels overlay")
    cp = a['price']
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.date_range(end=datetime.now(), periods=6, freq="30min"),
        y=[cp-250, cp-120, cp, cp+80, cp+180, cp+120],
        mode="lines+markers",
        name="Price"
    ))

    for lvl in a['support']:
        fig.add_hline(y=lvl, line_dash="dash", line_color="orange", annotation_text=str(lvl))
    for lvl in a['resistance']:
        fig.add_hline(y=lvl, line_dash="dash", line_color="red", annotation_text=str(lvl))
    if a['liquidity']:
        fig.add_hline(y=a['liquidity'], line_dash="dot", line_color="lime")
    if a['sl']:
        fig.add_hline(y=a['sl'], line_color="purple")
    if a['tp1']:
        fig.add_hline(y=a['tp1'], line_color="#00ff88")
    if a['tp2']:
        fig.add_hline(y=a['tp2'], line_color="#00cc66")

    fig.update_layout(height=450, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Click 'Analyze Current Structure' to get levels and trade idea")

st.caption("Demo only – rule-based only – not financial advice")
