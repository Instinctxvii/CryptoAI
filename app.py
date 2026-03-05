import streamlit as st
import pandas as pd
import requests
import subprocess
import sys
from datetime import datetime, timedelta
import pytz
import json

# ================= AUTO-INSTALL BS4 =================
try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    st.warning("Installing missing package 'beautifulsoup4'...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup
    st.success("'beautifulsoup4' installed successfully! Please rerun the app.")

from openai import OpenAI

# ================= PAGE CONFIG =================
st.set_page_config(page_title="AI Trading Terminal", layout="wide")
st.title("📊 AI Trading Terminal")

# ================= TIMEZONE =================
ny_tz = pytz.timezone("America/New_York")
local_tz = pytz.timezone("Africa/Johannesburg")  # adjust as needed

ny_open = ny_tz.localize(datetime.combine(datetime.today(), datetime.strptime("09:30", "%H:%M").time()))
ny_open_local = ny_open.astimezone(local_tz)
st.info(f"🕘 New York Open: 09:30 ET → {ny_open_local.strftime('%H:%M %p')} Local Time")

# ================= SIDEBAR =================
with st.sidebar:
    st.header("🔑 API Key")
    user_key = st.text_input("Enter xAI API Key", type="password")
    try:
        secret_key = st.secrets["XAI_API_KEY"]
    except Exception:
        secret_key = None

    xai_key = user_key if user_key else secret_key
    st.caption("For security: Never share your key. Add it via Streamlit Secrets.")

    st.markdown("---")
    st.header("Market Selection")
    market_type = st.radio("Select Market Type", ["Crypto", "Forex", "US30"])

    st.markdown("---")
    st.header("Backtesting Date")
    today = datetime.today()
    one_year_ago = today - timedelta(days=365)
    selected_date = st.date_input(
        "Select Date for Analysis",
        value=today,
        min_value=one_year_ago,
        max_value=today
    )

    st.markdown("---")
    st.header("Tools")
    scan_crypto = st.button("🔎 Scan Crypto Market")
    scan_forex = st.button("🔎 Scan Forex Market")
    scan_us30 = st.button("🔎 Scan US30 News")

# ================= CRYPTO SCANNER =================
if scan_crypto:
    st.subheader("🚀 Top Crypto Market Overview")
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "zar", "order": "market_cap_desc", "per_page": 50, "page": 1}
    data = requests.get(url, params=params).json()
    df = pd.DataFrame(data)[["name","symbol","current_price","market_cap","price_change_percentage_24h"]]
    df.columns = ["Name","Symbol","Price (R)","Market Cap","24h Change %"]
    st.dataframe(df, use_container_width=True)
    st.markdown("---")

# ================= FOREX SCANNER =================
if scan_forex:
    st.subheader("💱 Top Forex Pairs Overview")
    forex_pairs = ["EUR/USD","USD/JPY","GBP/USD","AUD/USD","USD/CAD"]
    rates = [1.08, 134.5, 1.24, 0.67, 1.36]  # Placeholder
    df_forex = pd.DataFrame({"Pair": forex_pairs,"Rate": rates})
    st.dataframe(df_forex,use_container_width=True)
    st.markdown("---")

# ================= US30 NEWS =================
us30_headlines = []
if market_type == "US30" or scan_us30:
    st.subheader("📰 US30 Latest Headlines from CNBC")
    url = "https://www.cnbc.com/us-stocks/"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        headlines = [h.text.strip() for h in soup.select("a.Card-title")]
        us30_headlines = headlines[:10]
        for h in us30_headlines:
            st.markdown(f"- {h}")
    except Exception as e:
        st.error(f"Failed to fetch CNBC headlines: {e}")

# ================= SYMBOL INPUT =================
symbol_default = "bitcoin" if market_type=="Crypto" else ("EURUSD" if market_type=="Forex" else "US30")
symbol = st.text_input("Enter Symbol", symbol_default)

# ================= AI ANALYSIS FUNCTION =================
support_resistance = []  # store levels for overlay

def run_ai_analysis(symbol, market_type, headlines, selected_date):
    global support_resistance
    if not xai_key:
        st.error("Please enter your xAI API Key in the sidebar.")
        return

    with st.spinner("Running AI market analysis..."):
        client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1")
        prompt = f"""
You are a professional institutional trader.

Analyze {symbol} ({market_type}) for date {selected_date.strftime('%Y-%m-%d')}.

Predict likely market movement by New York open ({ny_open_local.strftime('%H:%M %p')} local time).

Include clear support/resistance levels and liquidity zones (provide numeric price levels).
"""
        if market_type=="US30" and headlines:
            prompt += f"Recent CNBC headlines:\n{headlines}\n"

        response = client.chat.completions.create(
            model="grok-4-1-fast-reasoning",
            messages=[
                {"role":"system","content":"You are a professional institutional trader."},
                {"role":"user","content":prompt}
            ]
        )

        analysis_text = response.choices[0].message.content
        st.subheader(f"🧠 AI Market Analysis for {selected_date.strftime('%Y-%m-%d')}")
        st.markdown(analysis_text)

        # Extract numeric support/resistance levels from AI response (very basic)
        import re
        prices = [float(p) for p in re.findall(r"\b\d+\.\d+\b", analysis_text)]
        support_resistance = prices[:5]  # take first 5 numeric levels for overlay

# Run automatically for US30
if market_type=="US30":
    run_ai_analysis(symbol, market_type, us30_headlines, selected_date)

# Manual AI button
if st.button("🤖 Run AI Market Analysis"):
    run_ai_analysis(symbol, market_type, us30_headlines, selected_date)

# ================= TRADINGVIEW CHART WITH OVERLAYS =================
st.subheader("📈 Market Chart with AI Zones (TradingView)")
symbol_clean = symbol.upper().replace(" ","")
tv_symbol_map = {
    "BITCOIN":"COINBASE:BTCUSD",
    "ETHEREUM":"COINBASE:ETHUSD",
    "EURUSD":"FX_IDC:EURUSD",
    "US30":"INDEX:US30"
}
tv_symbol = tv_symbol_map.get(symbol_clean,"INDEX:US30")

# Build overlay lines for TradingView widget
overlays_json = []
for level in support_resistance:
    overlays_json.append({
        "id": f"level_{level}",
        "type": "horizontal_line",
        "price": level,
        "color": "red",
        "width": 1
    })

overlays_js = json.dumps(overlays_json)

st.components.v1.html(f"""
<div class="tradingview-widget-container">
  <div id="tradingview_{symbol_clean}"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  const overlays = {overlays_js};
  const widget = new TradingView.widget({{
    "width": "100%",
    "height": 500,
    "symbol": "{tv_symbol}",
    "interval": "60",
    "timezone": "Etc/UTC",
    "theme": "light",
    "style": "1",
    "locale": "en",
    "toolbar_bg": "#f1f3f6",
    "enable_publishing": false,
    "allow_symbol_change": true,
    "container_id": "tradingview_{symbol_clean}"
  }});
  // Overlay lines simulation
  overlays.forEach(l=>console.log("AI zone price:", l.price)); // TradingView widget doesn't allow direct overlay in embed, show in console for reference
  </script>
</div>
""", height=520)

# ================= HISTORICAL OHLC DATA =================
st.subheader("📊 Historical OHLC for Backtesting")
if market_type=="Crypto":
    url_hist = f"https://api.coingecko.com/api/v3/coins/{symbol.lower()}/market_chart"
    params_hist = {"vs_currency":"usd","days":"365"}
    try:
        hist_data = requests.get(url_hist, params=params_hist).json()
        df_hist = pd.DataFrame(hist_data["prices"], columns=["timestamp","price"])
        df_hist["date"] = pd.to_datetime(df_hist["timestamp"], unit="ms").dt.date
        df_day = df_hist[df_hist["date"]==selected_date]
        if not df_day.empty:
            st.line_chart(df_day.set_index("timestamp")["price"])
        else:
            st.warning("No historical data for selected date")
    except:
        st.warning("Failed to fetch historical data")

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
