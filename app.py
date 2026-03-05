import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
import json

# ================= PAGE CONFIG =================
st.set_page_config(page_title="AI Trading Terminal", layout="wide")
st.title("📊 AI Trading Terminal (Live + AI Zones)")

# ================= TIME =================
ny_tz = pytz.timezone("America/New_York")
local_tz = pytz.timezone("Africa/Johannesburg")
ny_open = ny_tz.localize(datetime.combine(datetime.today(), datetime.strptime("09:30","%H:%M").time()))
ny_open_local = ny_open.astimezone(local_tz)
st.info(f"🕘 New York Open: 09:30 ET → {ny_open_local.strftime('%H:%M %p')} Local Time")

# ================= SIDEBAR =================
with st.sidebar:
    st.header("Market Selection")
    market_type = st.radio("Select Market Type", ["Forex", "US30"])
    
    st.markdown("---")
    st.header("Backtesting Date (not yet active)")
    today = datetime.today()
    one_year_ago = today - timedelta(days=365)
    selected_date = st.date_input("Select Date for Backtesting", value=today, 
                                 min_value=one_year_ago, max_value=today)

# ================= SYMBOL INPUT =================
symbol_default = "EURUSD" if market_type == "Forex" else "US30"
symbol = st.text_input("Enter Symbol", symbol_default)

# ================= CURRENT PRICE INPUT =================
st.subheader("Current Market Price (from TradingView)")
if market_type == "US30":
    default_price = 48600.0  # update this to whatever you see today
    step = 10.0
    price_format = "%.0f"
else:
    default_price = 1.0820
    step = 0.0001
    price_format = "%.4f"

current_price = st.number_input(
    "Paste/enter the current or last visible price from the chart",
    min_value=0.0,
    value=default_price,
    step=step,
    format=price_format
)

# ================= OVERRIDE TRADINGVIEW SYMBOL (very useful for debugging) =================
st.subheader("TradingView Symbol (override if needed)")
default_tv_symbol = "FX:US30" if market_type == "US30" else "FX:EURUSD"
tv_symbol_override = st.text_input(
    "TradingView symbol (e.g. FX:US30, OANDA:US30USD, TVC:DJI, FX:EURUSD)",
    value=default_tv_symbol
)

# ================= AI ANALYSIS =================
support_levels = []
resistance_levels = []
trend_bias = "Neutral"
liquidity_pool = None

if st.button("🤖 Run AI Market Analysis"):
    if market_type == "US30":
        base = round(current_price / 100) * 100
        support_levels = [round(base - 400), round(base - 200)]
        resistance_levels = [round(base + 200), round(base + 400)]
        liquidity_pool = round(base - 180)
    else:
        base = round(current_price * 10000) / 10000
        support_levels = [round(base - 0.0040, 4), round(base - 0.0020, 4)]
        resistance_levels = [round(base + 0.0020, 4), round(base + 0.0040, 4)]
        liquidity_pool = round(base - 0.0015, 4)

    st.subheader(f"🧠 AI Market Analysis for {symbol}")
    st.markdown(f"""
**Support Levels:** {support_levels}  
**Resistance Levels:** {resistance_levels}  
**Trend Bias:** {trend_bias}  
**Liquidity Pools:** Around {liquidity_pool}  
    """)

# Combine levels for overlays
all_ai_levels = support_levels + resistance_levels
if liquidity_pool is not None:
    all_ai_levels.append(liquidity_pool)

# ================= TRADINGVIEW WIDGET =================
st.subheader("📈 Real-Time TradingView Chart")

symbol_clean = symbol.upper().replace(" ", "")

# Use the override if provided, otherwise fallback logic
if tv_symbol_override.strip():
    tv_symbol = tv_symbol_override.strip()
else:
    tv_symbol_map = {
        "EURUSD": "FX:EURUSD",
        "GBPUSD": "FX:GBPUSD",
        "USDZAR": "FX:USDZAR",
        "US30": "FX:US30",           # most reliable public one
        "DJI": "TVC:DJI",
        "DOW": "TVC:DJI"
    }
    tv_symbol = tv_symbol_map.get(symbol_clean, "FX:US30" if market_type == "US30" else "FX:EURUSD")

# Prepare overlays
overlays = []
for lvl in support_levels + resistance_levels:
    overlays.append({"price": float(lvl), "color": "red", "width": 1})
if liquidity_pool is not None:
    overlays.append({"price": float(liquidity_pool), "color": "lime", "width": 2, "linestyle": "dashed"})

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
      "toolbar_bg": "#f1f3f6",
      "enable_publishing": false,
      "allow_symbol_change": true,
      "container_id": "tradingview_{symbol_clean}"
    }});
    console.log("Using symbol: {tv_symbol}");
    overlays.forEach(l => console.log("AI Level:", l.price));
  </script>
</div>
""", height=580)

# (rest of the code - Plotly chart remains unchanged)

st.subheader("📊 Price Simulation with AI Levels")

if market_type == "US30":
    base_prices = [current_price - 300, current_price - 150, current_price, 
                   current_price + 100, current_price + 250, current_price]
else:
    base_prices = [current_price - 0.003, current_price - 0.0015, current_price, 
                   current_price + 0.001, current_price + 0.0025, current_price]

times = pd.date_range(end=datetime.now(pytz.UTC), periods=6, freq="5min")
df = pd.DataFrame({"Time": times, "Price": base_prices})

fig = go.Figure()
fig.add_trace(go.Scatter(x=df["Time"], y=df["Price"], 
                        mode="lines+markers", name="Price", line=dict(color="#00ccff")))

for lvl in support_levels:
    fig.add_hline(y=lvl, line_dash="dash", line_color="orange", 
                  annotation_text=f"Support {lvl}", annotation_position="right")
for lvl in resistance_levels:
    fig.add_hline(y=lvl, line_dash="dash", line_color="red", 
                  annotation_text=f"Resistance {lvl}", annotation_position="right")
if liquidity_pool is not None:
    fig.add_hline(y=liquidity_pool, line_dash="dot", line_color="lime", 
                  line_width=2, annotation_text=f"Liquidity \~{liquidity_pool}", 
                  annotation_position="left")

fig.update_layout(
    height=500,
    xaxis_title="Time (UTC)",
    yaxis_title="Price",
    template="plotly_dark",
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("Tip: If chart still fails → paste one of these into the override field: FX:US30, OANDA:US30USD, TVC:DJI, BLACKBULL:US30")
