import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import yfinance as yf
from datetime import datetime

# Page config
st.set_page_config(page_title="US30 Trader Demo", layout="wide")
st.title("US30 / Dow Jones Trader Demo")
st.caption("Rule-based demo – no API keys")

st.info("""
**Why prices may differ slightly**  
Analysis uses Yahoo Finance ^DJI (official index).  
TradingView shows broker CFD price (e.g. CAPITALCOM:US30).  
Normal difference: 10–100 points.  
Paste the live price from the chart below to recalculate using that price.
""")

# Session state
if 'analysis' not in st.session_state:
    st.session_state.analysis = None

# Sidebar
with st.sidebar:
    st.header("Settings")
    rr = st.slider("Risk:Reward for TP2", 1.5, 4.0, 2.5, 0.5)

# TradingView chart
st.subheader("📈 US30 Live Chart (Broker CFD)")

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

# Manual price input to match TradingView
tv_price_input = st.number_input(
    "Paste current LIVE price from TradingView chart (optional)",
    min_value=0.0,
    step=0.1,
    format="%.1f",
    value=0.0,
    help="Copy the current price shown on the chart to recalculate entry/SL/TP using that price"
)

# Analyze button
if st.button("Analyze Current Structure", type="primary"):
    with st.spinner("Fetching data from Yahoo Finance (^DJI)..."):
        try:
            df = yf.download("^DJI", period="5d", interval="15m", progress=False)

            if df.empty or len(df) < 20:
                st.error("Not enough recent data from Yahoo Finance")
                st.stop()

            df = df[['Close', 'High', 'Low']].astype(float)

            # Base price from yfinance
            yf_price = float(df['Close'].iloc[-1])
            price_r = round(yf_price)

            # If user pasted TradingView price → use that instead
            use_price = tv_price_input if tv_price_input > 1000 else yf_price
            use_price_r = round(use_price)

            high_40 = float(df['High'].rolling(40).max().iloc[-1])
            low_40  = float(df['Low'].rolling(40).min().iloc[-1])

            atr = float((df['High'] - df['Low']).rolling(14).mean().iloc[-1])

            sma20 = float(df['Close'].rolling(20).mean().iloc[-1])

            support     = [round(low_40), round(low_40 + atr * 0.6)]
            resistance  = [round(high_40 - atr * 0.6), round(high_40)]
            liquidity   = round(low_40 - atr * 0.8)

            if use_price > sma20 + atr * 0.4:
                bias = "Bullish"
                entry_point = round(use_price - atr * 0.4)
                entry_text = f"Enter long at ≈ **{entry_point}** (±10 points)"
                sl   = min(support) - int(atr * 0.4)
                risk = entry_point - sl
                tp1  = round(entry_point + risk)
                tp2  = round(entry_point + risk * rr)

            elif use_price < sma20 - atr * 0.4:
                bias = "Bearish"
                entry_point = round(use_price + atr * 0.4)
                entry_text = f"Enter short at ≈ **{entry_point}** (±10 points)"
                sl   = max(resistance) + int(atr * 0.4)
                risk = sl - entry_point
                tp1  = round(entry_point - risk)
                tp2  = round(entry_point - risk * rr)

            else:
                bias = "Range / Neutral"
                entry_text = f"No clear entry. Watch break above {resistance[1]} or below {support[0]}"
                sl = tp1 = tp2 = None

            reason = f"Using price {use_price_r} (TradingView if pasted, else Yahoo ^DJI). SMA20 ≈ {round(sma20)}. ATR ≈ {round(atr)}."

            st.session_state.analysis = {
                'price': use_price_r,
                'bias': bias,
                'entry': entry_text,
                'sl': sl,
                'tp1': tp1,
                'tp2': tp2,
                'support': support,
                'resistance': resistance,
                'liquidity': liquidity,
                'reason': reason,
                'source_note': "TradingView price" if tv_price_input > 1000 else "Yahoo ^DJI"
            }

            st.success("Analysis complete")

        except Exception as e:
            st.error(f"Error: {str(e)}")

# Show results
if st.session_state.analysis:
    a = st.session_state.analysis

    st.subheader(f"Current Analysis ({a['source_note']})")

    st.markdown(f"""
**Price used** ≈ **{a['price']}**

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

    # Plotly
    st.subheader("Levels overlay (using analysis price)")
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
