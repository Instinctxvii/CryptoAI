import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="US30 Trader Demo", layout="wide")
st.title("US30 / Dow Jones Trader Demo")
st.caption("Rule-based – no API keys – paste TradingView price to match exactly")

st.info("""
**To match the chart price 1:1**  
1. Look at the current price on the TradingView chart above  
2. Copy & paste it exactly into the field below  
3. Click Analyze → entry/SL/TP will use **exactly** that price
""")

# Session state
if 'analysis' not in st.session_state:
    st.session_state.analysis = None

# Sidebar
with st.sidebar:
    st.header("Settings")
    rr = st.slider("Risk:Reward for TP2", 1.5, 4.0, 2.5, 0.5)

# TradingView chart
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

# Price input – no max_value to avoid crash, we'll validate ourselves
tv_price = st.number_input(
    "Paste CURRENT price from TradingView chart here",
    min_value=0.0,           # allow 0 on load, we check later
    step=0.1,
    format="%.1f",
    value=48300.0,           # realistic default so app doesn't crash
    help="Copy the live price exactly from the chart above (e.g. 48322.4). This will be used for all calculations."
)

# Analyze button
if st.button("Analyze Current Structure", type="primary"):
    # Quick validation
    if tv_price < 40000 or tv_price > 60000:
        st.warning("Price looks unrealistic for US30 (should be 40,000–60,000 range). Double-check copy-paste.")
        # Continue anyway – user can correct

    with st.spinner("Calculating using your pasted price..."):
        try:
            # Fetch structure from ^DJI (SMA, ATR, support/resistance)
            df = yf.download("^DJI", period="5d", interval="15m", progress=False)

            if df.empty or len(df) < 20:
                st.error("Could not fetch structure data from Yahoo Finance")
                st.stop()

            df = df[['Close', 'High', 'Low']].astype(float)

            high_40 = float(df['High'].rolling(40).max().iloc[-1])
            low_40  = float(df['Low'].rolling(40).min().iloc[-1])
            atr     = float((df['High'] - df['Low']).rolling(14).mean().iloc[-1])
            sma20   = float(df['Close'].rolling(20).mean().iloc[-1])

            support     = [round(low_40), round(low_40 + atr * 0.6)]
            resistance  = [round(high_40 - atr * 0.6), round(high_40)]
            liquidity   = round(low_40 - atr * 0.8)

            # Use EXACTLY the pasted price for bias & levels
            price = tv_price
            price_r = round(price)

            if price > sma20 + atr * 0.4:
                bias = "Bullish"
                entry_point = round(price - atr * 0.4)
                entry_text = f"Enter long at ≈ **{entry_point}** (±10 points)"
                sl   = min(support) - int(atr * 0.4)
                risk = entry_point - sl
                tp1  = round(entry_point + risk)
                tp2  = round(entry_point + risk * rr)

            elif price < sma20 - atr * 0.4:
                bias = "Bearish"
                entry_point = round(price + atr * 0.4)
                entry_text = f"Enter short at ≈ **{entry_point}** (±10 points)"
                sl   = max(resistance) + int(atr * 0.4)
                risk = sl - entry_point
                tp1  = round(entry_point - risk)
                tp2  = round(entry_point - risk * rr)

            else:
                bias = "Range / Neutral"
                entry_text = f"No clear entry. Watch break above {resistance[1]} or below {support[0]}"
                sl = tp1 = tp2 = None

            reason = f"Using pasted TradingView price {price_r}. SMA20 ≈ {round(sma20)}. ATR ≈ {round(atr)}."

            st.session_state.analysis = {
                'price': price_r,
                'bias': bias,
                'entry': entry_text,
                'sl': sl,
                'tp1': tp1,
                'tp2': tp2,
                'support': support,
                'resistance': resistance,
                'liquidity': liquidity,
                'reason': reason
            }

            st.success("Analysis complete – using your pasted price")

        except Exception as e:
            st.error(f"Calculation failed: {str(e)}")

# Display results
if st.session_state.analysis:
    a = st.session_state.analysis

    st.subheader("Current Analysis (using pasted TradingView price)")

    st.markdown(f"""
**Price (pasted)** ≈ **{a['price']}**

**Bias** → **{a['bias']}**

**Point of Entry** → {a['entry']}

**Stop Loss** → {a['sl'] if a['sl'] is not None else '—'}  
**TP1** → {a['tp1'] if a['tp1'] is not None else '—'}  
**TP2** ({rr:.1f}:1) → {a['tp2'] if a['tp2'] is not None else '—'}

**Support** → {a['support']}  
**Resistance** → {a['resistance']}  
**Liquidity pool** ≈ {a['liquidity']}

**Reason**  
{a['reason']}
    """)

    # Plotly using pasted price
    st.subheader("Levels overlay (using pasted price)")
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
    st.info("Paste price from chart above → press Analyze")

st.caption("Demo only – rule-based only – not financial advice")
