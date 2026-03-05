import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import json
from bs4 import BeautifulSoup

# ================= PAGE CONFIG =================
st.set_page_config(page_title="AI Trading Terminal", layout="wide")
st.title("📊 AI Trading Terminal (Real-Time US30 & Forex)")

# ================= TIMEZONE =================
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
    st.header("Backtesting Date (Optional)")
    today = datetime.today()
    one_year_ago = today - timedelta(days=365)
    selected_date = st.date_input("Select Date for Backtesting", value=today, min_value=one_year_ago, max_value=today)
    
    st.markdown("---")
    st.header("Tools")
    scan_forex = st.button("🔎 Scan Forex Market")
    scan_us30 = st.button("🔎 Scan US30 News")

# ================= FOREX SCANNER =================
if scan_forex:
    st.subheader("💱 Top Forex Pairs Overview")
    forex_pairs = ["EUR/USD","USD/JPY","GBP/USD","AUD/USD","USD/CAD"]
    rates = [1.08,134.5,1.24,0.67,1.36]  # placeholder rates
    df_forex = pd.DataFrame({"Pair":forex_pairs,"Rate":rates})
    st.dataframe(df_forex,use_container_width=True)
    st.markdown("---")

# ================= US30 NEWS =================
us30_headlines = []
if market_type=="US30" or scan_us30:
    st.subheader("📰 US30 Latest Headlines from CNBC")
    try:
        response = requests.get("https://www.cnbc.com/us-stocks/")
        soup = BeautifulSoup(response.text, "html.parser")
        headlines = [h.text.strip() for h in soup.select("a.Card-title")]
        us30_headlines = headlines[:10]
        for h in us30_headlines:
            st.markdown(f"- {h}")
    except:
        st.warning("Failed to fetch CNBC headlines")

# ================= SYMBOL INPUT =================
symbol_default = "EURUSD" if market_type=="Forex" else "US30"
symbol = st.text_input("Enter Symbol", symbol_default)

# ================= AI ANALYSIS (SIMULATED) =================
support_resistance = [39000,39500,40000]  # default placeholders

def run_ai_analysis():
    global support_resistance
    # Simulate AI output based on symbol
    if market_type=="US30":
        support_resistance = [39000,39500,40000]
        trend_bias = "Bullish"
    else:
        support_resistance = [1.08,1.082,1.085]
        trend_bias = "Neutral"
    st.subheader(f"🧠 AI Market Analysis for {symbol}")
    st.markdown(f"""
**Date:** {datetime.today().strftime('%Y-%m-%d')}  
**New York Open:** {ny_open_local.strftime('%H:%M %p')} Local Time  

**Support Levels:** {support_resistance[:2]}  
**Resistance Levels:** {support_resistance[2:]}  
**Trend Bias:** {trend_bias}  
**Liquidity Pools:** Around {support_resistance[1]}  
**Trade Setup Idea:** Monitor break of resistance for long entry
""")

if st.button("🤖 Run AI Market Analysis (Live)"):
    run_ai_analysis()

# ================= TRADINGVIEW CHART (REAL-TIME) =================
st.subheader("📈 Real-Time TradingView Chart")
symbol_clean = symbol.upper().replace(" ","")
tv_symbol_map = {
    "EURUSD":"FX_IDC:EURUSD",
    "US30":"PEPPERSTONE:US30"  # default Pepperstone US30 CFD
}
tv_symbol = tv_symbol_map.get(symbol_clean,"INDEX:US30")

overlays_json = [{"price":level,"color":"red","width":1} for level in support_resistance]
overlays_js = json.dumps(overlays_json)

st.components.v1.html(f"""
<div class="tradingview-widget-container">
  <div id="tradingview_{symbol_clean}"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
    const overlays = {overlays_js};
    const widget = new TradingView.widget({{
        "width":"100%",
        "height":500,
        "symbol":"{tv_symbol}",
        "interval":"1",  // 1-minute candles for real-time
        "timezone":"Etc/UTC",
        "theme":"light",
        "style":"1",
        "locale":"en",
        "toolbar_bg":"#f1f3f6",
        "enable_publishing":false,
        "allow_symbol_change":true,
        "container_id":"tradingview_{symbol_clean}"
    }});
    overlays.forEach(l=>console.log("AI Zone Price:",l.price));
  </script>
</div>
""",height=520)

# ================= HISTORICAL BACKTESTING (OPTIONAL) =================
st.subheader("📊 Historical OHLC (Backtesting)")
if market_type=="Forex":
    df_hist = pd.DataFrame({
        "timestamp": pd.date_range(start=selected_date, periods=6, freq="H"),
        "price":[1.08,1.081,1.079,1.082,1.084,1.083]
    }).set_index("timestamp")
else:
    df_hist = pd.DataFrame({
        "timestamp": pd.date_range(start=selected_date, periods=6, freq="H"),
        "price":[39000,39200,39100,39300,39500,39400]
    }).set_index("timestamp")
st.line_chart(df_hist)

# ================= SMART MONEY ZONES =================
st.subheader("📊 Smart Money Zones")
col1,col2,col3 = st.columns(3)
with col1: st.metric("Support","Scanning...")
with col2: st.metric("Resistance","Scanning...")
with col3: st.metric("Liquidity Pools","Scanning...")

# ================= SCENARIOS =================
st.subheader("📉 AI Scenario Projection")
scenario_df = pd.DataFrame({"Scenario":["Bear","Base","Bull"],"Probability %":[25,50,25]})
st.bar_chart(scenario_df.set_index("Scenario"))

st.markdown("---")
st.caption("Educational use only. Trading involves risk.")
