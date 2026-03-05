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
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

from openai import OpenAI

# ================= PAGE CONFIG =================
st.set_page_config(page_title="AI Trading Terminal", layout="wide")
st.title("📊 AI Trading Terminal")

# ================= TIMEZONE =================
ny_tz = pytz.timezone("America/New_York")
local_tz = pytz.timezone("Africa/Johannesburg")

ny_open = ny_tz.localize(datetime.combine(datetime.today(), datetime.strptime("09:30","%H:%M").time()))
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

    st.markdown("---")
    st.header("Market Selection")
    market_type = st.radio("Select Market Type", ["Crypto", "Forex", "US30"])

    st.markdown("---")
    st.header("Backtesting Date")
    today = datetime.today()
    one_year_ago = today - timedelta(days=365)
    selected_date = st.date_input("Select Date for Analysis", value=today, min_value=one_year_ago, max_value=today)

    st.markdown("---")
    st.header("Tools")
    scan_crypto = st.button("🔎 Scan Crypto Market")
    scan_forex = st.button("🔎 Scan Forex Market")
    scan_us30 = st.button("🔎 Scan US30 News")

# ================= SYMBOL INPUT =================
symbol_default = "bitcoin" if market_type=="Crypto" else ("EURUSD" if market_type=="Forex" else "US30")
symbol = st.text_input("Enter Symbol", symbol_default)

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

# ================= AI ANALYSIS =================
support_resistance = []
def run_ai_analysis(symbol, market_type, headlines, selected_date):
    global support_resistance
    if not xai_key:
        st.error("Enter your xAI API Key in the sidebar")
        return
    client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1")
    prompt = f"""
You are a professional institutional trader.
Analyze {symbol} ({market_type}) for {selected_date.strftime('%Y-%m-%d')}.
Predict market movement by NY open ({ny_open_local.strftime('%H:%M %p')} local time).
Include numeric support/resistance and liquidity zones.
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
    st.subheader(f"🧠 AI Analysis for {selected_date.strftime('%Y-%m-%d')}")
    st.markdown(analysis_text)

    import re
    prices = [float(p) for p in re.findall(r"\b\d+\.\d+\b", analysis_text)]
    support_resistance = prices[:5]

# Run AI automatically for US30
if market_type=="US30":
    run_ai_analysis(symbol, market_type, us30_headlines, selected_date)

if st.button("🤖 Run AI Market Analysis"):
    run_ai_analysis(symbol, market_type, us30_headlines, selected_date)

# ================= TRADINGVIEW CHART =================
st.subheader("📈 TradingView Chart with AI Zones")
symbol_clean = symbol.upper().replace(" ","")
tv_symbol_map = {
    "BITCOIN":"COINBASE:BTCUSD",
    "ETHEREUM":"COINBASE:ETHUSD",
    "EURUSD":"FX_IDC:EURUSD",
    "US30":"PEPPERSTONE:US30"  # <--- default to Pepperstone US30 CFD
}
tv_symbol = tv_symbol_map.get(symbol_clean,"INDEX:US30")

overlays_json = []
for level in support_resistance:
    overlays_json.append({"price":level,"color":"red","width":1})

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
        "interval":"60",
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
