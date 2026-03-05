import streamlit as st
import pandas as pd
import requests
import subprocess
import sys

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

# ================= SIDEBAR =================
with st.sidebar:
    st.header("🔑 API Key")
    user_key = st.text_input("Enter xAI API Key", type="password")
    
    try:
        secret_key = st.secrets["XAI_API_KEY"]
    except Exception:
        secret_key = None

    xai_key = user_key if user_key else secret_key

    st.caption(
        "For security: Never share your key. "
        "On Streamlit Cloud, add it via Secrets instead of typing here."
    )

    st.markdown("---")

    st.header("Market Selection")
    market_type = st.radio("Select Market Type", ["Crypto", "Forex", "US30"])

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

    df = pd.DataFrame(data)[
        ["name", "symbol", "current_price", "market_cap", "price_change_percentage_24h"]
    ]
    df.columns = ["Name", "Symbol", "Price (R)", "Market Cap", "24h Change %"]
    st.dataframe(df, use_container_width=True)
    st.markdown("---")

# ================= FOREX SCANNER =================
if scan_forex:
    st.subheader("💱 Top Forex Pairs Overview")
    forex_pairs = ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CAD"]
    rates = [1.08, 134.5, 1.24, 0.67, 1.36]  # Placeholder
    df_forex = pd.DataFrame({"Pair": forex_pairs, "Rate": rates})
    st.dataframe(df_forex, use_container_width=True)
    st.markdown("---")

# ================= US30 NEWS =================
us30_headlines = []
if scan_us30:
    st.subheader("📰 US30 Latest Headlines from CNBC")
    url = "https://www.cnbc.com/us-stocks/"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        headlines = [h.text.strip() for h in soup.select("a.Card-title")]
        us30_headlines = headlines[:10]  # Top 10
        for h in us30_headlines:
            st.markdown(f"- {h}")
    except Exception as e:
        st.error(f"Failed to fetch CNBC headlines: {e}")

# ================= SYMBOL INPUT =================
symbol_default = "bitcoin" if market_type == "Crypto" else ("EURUSD" if market_type == "Forex" else "US30")
symbol = st.text_input("Enter Symbol", symbol_default)

# ================= TRADINGVIEW CHART =================
st.subheader("📈 Market Chart (TradingView)")
symbol_map = {
    "bitcoin": "COINBASE:BTCUSD",
    "ethereum": "COINBASE:ETHUSD",
    "EURUSD": "FX_IDC:EURUSD",
    "US30": "INDEX:US30"
}
tv_symbol = symbol_map.get(symbol.upper(), "COINBASE:BTCUSD")

st.components.v1.html(f"""
<div class="tradingview-widget-container">
  <div id="tradingview_{symbol}"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({{
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
    "container_id": "tradingview_{symbol}"
  }});
  </script>
</div>
""", height=520)

# ================= MARKET STRUCTURE DISPLAY =================
st.subheader("📊 Smart Money Zones")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Support", "Scanning...")
with col2:
    st.metric("Resistance", "Scanning...")
with col3:
    st.metric("Liquidity Pools", "Scanning...")

# ================= AI ANALYSIS =================
if st.button("🤖 Run AI Market Analysis"):
    if not xai_key:
        st.error("Please enter your xAI API Key in the sidebar.")
    else:
        with st.spinner("Running AI market analysis..."):
            client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1")
            prompt = f"""
You are a professional institutional trader.

Analyze the market: {symbol} ({market_type}).

"""
            if market_type == "US30" and us30_headlines:
                prompt += f"Recent CNBC headlines:\n{us30_headlines}\n"

            prompt += """
Provide:
1. Market structure
2. Support and resistance zones
3. Liquidity pools
4. Order blocks
5. Trend bias
6. Possible manipulation zones
7. Trade setup idea

Return clear structured analysis.
"""
            response = client.chat.completions.create(
                model="grok-4-1-fast-reasoning",
                messages=[
                    {"role": "system", "content": "You are a professional institutional trader."},
                    {"role": "user", "content": prompt},
                ],
            )
            st.subheader("🧠 AI Market Analysis")
            st.markdown(response.choices[0].message.content)

# ================= PRICE SCENARIOS =================
st.subheader("📉 AI Scenario Projection")
scenario_df = pd.DataFrame({
    "Scenario": ["Bear", "Base", "Bull"],
    "Probability %": [25, 50, 25]
})
st.bar_chart(scenario_df.set_index("Scenario"))

# ================= DISCLAIMER =================
st.markdown("---")
st.caption("Educational use only. Trading involves risk.")
