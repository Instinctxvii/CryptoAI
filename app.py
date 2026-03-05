import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import yfinance as yf
from datetime import datetime

# ────────────────────────────────────────────────
# PAGE CONFIG
# ────────────────────────────────────────────────
st.set_page_config(page_title="US30 Trader Demo", layout="wide")
st.title("US30 / Dow Jones Trader Demo")
st.caption("Rule-based demo — no API keys — no LLM")

# ────────────────────────────────────────────────
# SESSION STATE
# ────────────────────────────────────────────────
if 'analysis' not in st.session_state:
    st.session_state.analysis = None

# ────────────────────────────────────────────────
# SIDEBAR
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    rr = st.slider("Risk:Reward for TP2", 1.5, 4.0, 2.5, 0.5)

# ────────────────────────────────────────────────
# TRADINGVIEW CHART – loads immediately
# ────────────────────────────────────────────────
st.subheader("📈 US30 Live Chart")

tv_symbol = st.text_input("TradingView Symbol", "CAPITALCOM:US30")

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
      "enable_publishing": false,
      "allow_symbol_change": true,
      "container_id": "tvchart"
    }});
  </script>
</div>
""", height=620)

# ────────────────────────────────────────────────
# ANALYSIS BUTTON – fully scalar-safe version
# ────────────────────────────────────────────────
if st.button("Analyze Current Structure", type="primary"):
    with st.spinner("Fetching data..."):
        try:
            df = yf.download("^DJI", period="5d", interval="15m", progress=False)

            # Early exit – safe check (df.empty is bool, len(df) is int)
            if df is None or df.empty or len(df) < 20:
                st.error("Not enough recent data from Yahoo Finance")
                st.stop()

            # Keep only needed columns + force numeric
            df = df[['Close', 'High', 'Low']].astype(float)

            # ── Extract ALL scalars first ─────────────────────────────────
            current_price = float(df['Close'].iloc[-1])
            price_r = round(current_price)

            # Rolling values → convert to float right away
            high_40 = float(df['High'].rolling(window=40).max().iloc[-1])
            low_40  = float(df['Low'].rolling(window=40).min().iloc[-1])

            atr = float((df['High'] - df['Low']).rolling(window=14).mean().iloc[-1])

            sma20 = float(df['Close'].rolling(window=20).mean().iloc[-1])

            # Levels – all scalars
            support     = [round(low_40), round(low_40 + atr * 0.6)]
            resistance  = [round(high_40 - atr * 0.6), round(high_40)]
            liquidity   = round(low_40 - atr * 0.8)

            # ── Bias logic – pure scalar comparisons ──────────────────────
            if current_price > sma20 + atr * 0.4:
                bias = "Bullish"
                entry_zone = f"Buy limit {round(current_price - atr*0.5)} – {round(current_price - atr*0.3)}"
                sl   = min(support) - int(atr * 0.4)
                risk = current_price - sl
                tp1  = round(current_price + risk)
                tp2  = round(current_price + risk * rr)

            elif current_price < sma20 - atr * 0.4:
                bias = "Bearish"
                entry_zone = f"Sell limit {round(current_price + atr*0.3)} – {round(current_price + atr*0.5)}"
                sl   = max(resistance) + int(atr * 0.4)
                risk = sl - current_price
                tp1  = round(current_price - risk)
                tp2  = round(current_price - risk * rr)

            else:
                bias = "Range / Neutral"
                entry_zone = f"Wait for break above {resistance[1]} or below {support[0]}"
                sl = tp1 = tp2 = None

            reason = f"Price ≈ {price_r} vs SMA20 ≈ {round(sma20)}. ATR ≈ {round(atr)}."

            st.session_state.analysis = {
                'price': price_r,
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
            st.error(f"Error: {str(e)}")

# ────────────────────────────────────────────────
# DISPLAY RESULTS
# ────────────────────────────────────────────────
if st.session_state.analysis:
    a = st.session_state.analysis

    st.subheader("Current Analysis")

    st.markdown(f"""
**Price** ≈ **{a['price']}**

**Bias** → **{a['bias']}**

**Suggested Entry** → {a['entry']}

**Stop Loss** → {a['sl'] if a['sl'] is not None else '—'}  
**TP1** → {a['tp1'] if a['tp1'] is not None else '—'}  
**TP2** ({rr:.1f}:1) → {a['tp2'] if a['tp2'] is not None else '—'}

**Support** → {a['support']}  
**Resistance** → {a['resistance']}  
**Liquidity** ≈ {a['liquidity']}

**Reason**  
{a['reason']}
    """)

    # Plotly backup
    st.subheader("Quick levels overlay")
    cp = a['price']
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.date_range(end=datetime.now(), periods=6, freq="30min"),
        y=[cp-300, cp-150, cp, cp+100, cp+200, cp+150],
        mode="lines+markers",
        name="Price"
    ))

    for lvl in a['support']:
        fig.add_hline(y=lvl, line_dash="dash", line_color="orange", annotation_text=str(lvl))
    for lvl in a['resistance']:
        fig.add_hline(y=lvl, line_dash="dash", line_color="red", annotation_text=str(lvl))
    if a['liquidity'] is not None:
        fig.add_hline(y=a['liquidity'], line_dash="dot", line_color="lime")
    if a['sl'] is not None:
        fig.add_hline(y=a['sl'], line_color="purple")
    if a['tp1'] is not None:
        fig.add_hline(y=a['tp1'], line_color="#00ff88")
    if a['tp2'] is not None:
        fig.add_hline(y=a['tp2'], line_color="#00cc66")

    fig.update_layout(height=450, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Press the button to analyze")

st.caption("Demo only – rule-based only – not financial advice")
