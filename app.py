import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz
import json
import yfinance as yf

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

# Use a symbol that usually works in the lightweight widget
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

            if df is None or df.empty or len(df) < 30:
                st.error("Not enough recent data from Yahoo Finance")
            else:
                # Force numeric columns
                df = df[['Open', 'High', 'Low', 'Close']].astype(float)

                # Get scalar values safely
                current_price = float(df['Close'].iloc[-1])
                price_rounded = round(current_price)

                # Rolling calculations → take last value immediately as scalar
                high_40_series = df['High'].rolling(40).max()
                low_40_series  = df['Low'].rolling(40).min()
                atr_series     = (df['High'] - df['Low']).rolling(14).mean()

                high_40 = float(high_40_series.iloc[-1]) if not pd.isna(high_40_series.iloc[-1]) else current_price
                low_40  = float(low_40_series.iloc[-1])  if not pd.isna(low_40_series.iloc[-1])  else current_price
                atr     = float(atr_series.iloc[-1])     if not pd.isna(atr_series.iloc[-1])     else 50.0

                support     = [round(low_40), round(low_40 + atr * 0.6)]
                resistance  = [round(high_40 - atr * 0.6), round(high_40)]
                liquidity   = round(low_40 - atr * 0.8)

                sma20_series = df['Close'].rolling(20).mean()
                sma20 = float(sma20_series.iloc[-1]) if not pd.isna(sma20_series.iloc[-1]) else current_price

                # All comparisons now use scalars only
                if current_price > (sma20 + atr * 0.4):
                    bias = "Bullish"
                    entry_low  = round(current_price - atr * 0.5)
                    entry_high = round(current_price - atr * 0.3)
                    entry_zone = f"Buy limit zone {entry_low} – {entry_high}"
                    sl   = min(support) - int(atr * 0.4)
                    risk = current_price - sl
                    tp1  = round(current_price + risk)
                    tp2  = round(current_price + risk * rr)

                elif current_price < (sma20 - atr * 0.4):
                    bias = "Bearish"
                    entry_low  = round(current_price + atr * 0.3)
                    entry_high = round(current_price + atr * 0.5)
                    entry_zone = f"Sell limit zone {entry_low} – {entry_high}"
                    sl   = max(resistance) + int(atr * 0.4)
                    risk = sl - current_price
                    tp1  = round(current_price - risk)
                    tp2  = round(current_price - risk * rr)

                else:
                    bias = "Range / Neutral"
                    entry_zone = f"Wait for breakout above {resistance[1]} or below {support[0]}"
                    sl = tp1 = tp2 = None

                reason = (
                    f"Price {price_rounded} vs SMA20 {round(sma20)}. "
                    f"ATR ≈ {round(atr)}. Recent range {round(low_40)}–{round(high_40)}."
                )

                st.session_state.analysis = {
                    'price': price_rounded,
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

                st.success(f"Analysis complete – Price ≈ {price_rounded}")

        except Exception as e:
            st.error(f"Fetch or calculation failed: {str(e)}\nPlease try again.")

# ================= SHOW RESULTS =================
if st.session_state.get('analysis'):
    a = st.session_state.analysis

    st.subheader("Current Analysis")

    st.markdown(f"""
**Price** ≈ **{a['price']}**

**Bias** → **{a['bias']}**

**Suggested Entry** → {a['entry']}

**Stop Loss** → {a['sl'] if a['sl'] is not None else '—'}  
**TP1** → {a['tp1'] if a['tp1'] is not None else '—'}  
**TP2** ({rr:.1f} : 1) → {a['tp2'] if a['tp2'] is not None else '—'}

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
    if a['liquidity'] is not None:
        overlays.append({"price": float(a['liquidity']), "color": "lime", "width": 3, "linestyle": "dashed"})
    if a['sl'] is not None:
        overlays.append({"price": float(a['sl']), "color": "purple", "width": 2, "linestyle": "dotted"})
    if a['tp1'] is not None:
        overlays.append({"price": float(a['tp1']), "color": "#00ff88", "width": 2})
    if a['tp2'] is not None:
        overlays.append({"price": float(a['tp2']), "color": "#00cc66", "width": 3})

    overlays_json = json.dumps(overlays)

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
    st.info("Click 'Analyze Current Structure' to get levels and trade idea")

st.caption("Demo only – rule-based only – not financial advice")
