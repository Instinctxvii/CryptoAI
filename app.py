import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from openai import OpenAI

st.set_page_config(page_title="AI Trading Terminal", layout="wide")

st.title("📊 AI Trading Terminal")

# ================= SIDEBAR =================

with st.sidebar:

    st.header("🔑 API Key")

    user_key = st.text_input("Enter xAI API Key", type="password")

    try:
        secret_key = st.secrets["XAI_API_KEY"]
    except:
        secret_key = None

    xai_key = user_key if user_key else secret_key

    st.divider()

    st.header("Market Type")

    market = st.selectbox(
        "Select Market",
        ["Crypto", "Forex", "Indices"]
    )

    st.divider()

    st.header("Tools")

    scan_crypto = st.button("🔎 Scan Crypto Gems")

# ================= CRYPTO SCANNER =================

if scan_crypto:

    st.subheader("🚀 Crypto Opportunity Scanner")

    url = "https://api.coingecko.com/api/v3/coins/markets"

    params = {
        "vs_currency": "zar",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1
    }

    data = requests.get(url, params=params).json()

    df = pd.DataFrame(data)[
        [
            "name",
            "symbol",
            "current_price",
            "market_cap",
            "price_change_percentage_24h"
        ]
    ]

    df.columns = [
        "Name",
        "Symbol",
        "Price (R)",
        "Market Cap",
        "24h Change %"
    ]

    st.dataframe(df, use_container_width=True)

# ================= SYMBOL INPUT =================

if market == "Crypto":

    symbol = st.text_input("Crypto Symbol", "BTC")

elif market == "Forex":

    symbol = st.text_input("Forex Pair", "EURUSD")

else:

    symbol = st.text_input("Index", "US30")

# ================= PRICE DATA =================

def get_crypto_price(symbol):

    url = "https://api.coingecko.com/api/v3/simple/price"

    params = {
        "ids": symbol.lower(),
        "vs_currencies": "zar"
    }

    r = requests.get(url, params=params).json()

    return r

# ================= CHART =================

st.subheader("📈 Market Chart")

chart_symbol = symbol

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        y=[1,2,3,2,4,5,4],
        mode="lines",
        name="Price"
    )
)

st.plotly_chart(fig, use_container_width=True)

# ================= MARKET STRUCTURE =================

st.subheader("📊 Smart Money Zones")

col1, col2, col3 = st.columns(3)

with col1:

    st.metric("Support", "Identifying")

with col2:

    st.metric("Resistance", "Identifying")

with col3:

    st.metric("Liquidity Pools", "Scanning")

# ================= AI ANALYSIS =================

if st.button("🤖 Run AI Market Analysis"):

    if not xai_key:

        st.error("Enter xAI API Key")

    else:

        with st.spinner("Analyzing market structure..."):

            client = OpenAI(
                api_key=xai_key,
                base_url="https://api.x.ai/v1"
            )

            prompt = f"""

You are a professional institutional trader.

Analyze the following market:

Asset: {symbol}
Market type: {market}

Provide:

1 Market structure
2 Support and resistance
3 Liquidity zones
4 Order blocks
5 Trend bias
6 Likely manipulation areas
7 Trade setup idea

Return a structured response.

"""

            response = client.chat.completions.create(
                model="grok-4-1-fast-reasoning",
                messages=[
                    {"role":"system","content":"You are a professional trader."},
                    {"role":"user","content":prompt}
                ]
            )

            st.subheader("🧠 AI Market Analysis")

            st.markdown(response.choices[0].message.content)

# ================= PRICE PROJECTIONS =================

st.subheader("📉 AI Price Scenarios")

scenario_df = pd.DataFrame({
    "Scenario": ["Bear", "Base", "Bull"],
    "Probability": [25,50,25]
})

st.bar_chart(scenario_df.set_index("Scenario"))

# ================= DISCLAIMER =================

st.caption("Educational use only. Not financial advice.")    
    st.caption("For security: Never share your key. On Streamlit Cloud, add it via Secrets instead of typing here.")

    st.header("ℹ️ About")
    st.info("""
    • Uses CoinGecko (free) + Grok (xAI)\n
    • Scores all 10 criteria you listed\n
    • Educational tool only — NOT financial advice
    """)

    st.header("Your 10 Criteria")
    st.markdown("""
    1. Real Problem Solved  
    2. Team Behind the Project  
    3. Tokenomics  
    4. Actual Users  
    5. Developer Activity  
    6. Partnerships & Ecosystem  
    7. Regulatory Awareness  
    8. Liquidity & Exchanges  
    9. Long-Term Narrative  
    10. Community Quality
    """)

# ====================== HELPER FUNCTIONS (unchanged) ======================
@st.cache_data(ttl=3600)
def get_coins_list():
    url = "https://api.coingecko.com/api/v3/coins/list"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=300)
def get_coin_data(coin_id: str):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    params = {"localization": "false", "tickers": "false", "market_data": "true", "community_data": "true", "developer_data": "true"}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=300)
def get_historical(coin_id: str, days: int = 365):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# ====================== MAIN APP ======================
coins = get_coins_list()
symbol_to_ids = {}
for coin in coins:
    sym = coin["symbol"].upper()
    if sym not in symbol_to_ids:
        symbol_to_ids[sym] = []
    symbol_to_ids[sym].append(coin["id"])

coin_input = st.text_input("Enter coin symbol (e.g. BTC, ETH, SOL)", value="BTC").strip().upper()

if coin_input and coin_input in symbol_to_ids:
    possible_ids = symbol_to_ids[coin_input]
    if len(possible_ids) > 1:
        coin_id = st.selectbox("Multiple matches — pick one", possible_ids)
    else:
        coin_id = possible_ids[0]
    
    if st.button("🚀 Analyze with Grok", type="primary"):
        xai_key = st.session_state.get("xai_key")
        
        if not xai_key:
            st.error("Please paste your xAI API key in the sidebar first.")
        else:
            with st.spinner("Fetching live data from CoinGecko..."):
                try:
                    coin_data = get_coin_data(coin_id)
                    hist_df = get_historical(coin_id, 365)
                    
                    current_price = coin_data["market_data"]["current_price"]["usd"]
                    market_cap = coin_data["market_data"]["market_cap"]["usd"]
                    volume = coin_data["market_data"]["total_volume"]["usd"]
                    
                    st.success(f"✅ Loaded {coin_data['name']} ({coin_data['symbol'].upper()})")
                    
                    st.subheader("📈 Price History (365 days)")
                    st.line_chart(hist_df.set_index("date")["price"], use_container_width=True)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1: st.metric("Current Price", f"${current_price:,.4f}")
                    with col2: st.metric("Market Cap", f"${market_cap:,.0f}")
                    with col3: st.metric("24h Volume", f"${volume:,.0f}")
                    
                    # ====================== GROK ANALYSIS ======================
                    with st.spinner("Grok is evaluating all 10 criteria + generating 12-month projections..."):
                        client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1")
                        
                        price_change = ((hist_df["price"].iloc[-1] / hist_df["price"].iloc[0]) - 1) * 100
                        
                        context = f"""
                        Coin: {coin_data['name']} ({coin_data['symbol'].upper()})
                        Current price: ${current_price:,.4f}
                        Market cap: ${market_cap:,.0f}
                        24h volume: ${volume:,.0f}
                        365-day price change: {price_change:,.1f}%
                        """
                        
                        prompt = f"""
                        You are an expert crypto analyst. Evaluate exactly against these 10 criteria:

                        1️⃣ Real Problem Being Solved  
                        2️⃣ The Team Behind the Project  
                        3️⃣ Tokenomics  
                        4️⃣ Actual Users  
                        5️⃣ Developer Activity  
                        6️⃣ Partnerships and Ecosystem  
                        7️⃣ Regulatory Awareness  
                        8️⃣ Liquidity and Exchanges  
                        9️⃣ Long-Term Narrative  
                        🔟 Community Quality

                        DATA: {context}

                        For EACH criterion: Score 1-10 + 1-2 sentence explanation.
                        Then: Overall score, Investment thesis, and 12-MONTH PRICE PROJECTIONS (Base / Bull / Bear with % upside).

                        Return clean Markdown with emojis.
                        """
                        
                        response = client.chat.completions.create(
                            model="grok-4-1-fast-reasoning",  # or "grok-beta" / check latest models in xAI console
                            messages=[
                                {"role": "system", "content": "You are Grok, a maximally truthful crypto analyst."},
                                {"role": "user", "content": prompt}
                            ]
                        )
                        
                        st.markdown("### 🧠 Grok's Full Analysis")
                        st.markdown(response.choices[0].message.content)
                        st.caption("Analysis powered by Grok (xAI) • Data from CoinGecko")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    if "authentication" in str(e).lower() or "invalid" in str(e).lower():
                        st.warning("API key issue? Double-check it in the sidebar or try regenerating a new one at console.x.ai")
else:
    st.info("Enter a symbol above (BTC, ETH, SOL, etc.) and click Analyze → make sure your xAI key is set in the sidebar.")

st.caption("Educational use only • Crypto is volatile • Key stored only in your browser session")def get_historical(coin_id: str, days: int = 365):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# ====================== MAIN APP ======================
coins = get_coins_list()
symbol_to_ids = {}
for coin in coins:
    sym = coin["symbol"].upper()
    if sym not in symbol_to_ids:
        symbol_to_ids[sym] = []
    symbol_to_ids[sym].append(coin["id"])

coin_input = st.text_input("Enter coin symbol (e.g. BTC, ETH, SOL)", value="BTC").strip().upper()

if coin_input and coin_input in symbol_to_ids:
    possible_ids = symbol_to_ids[coin_input]
    if len(possible_ids) > 1:
        coin_id = st.selectbox("Multiple matches — pick one", possible_ids)
    else:
        coin_id = possible_ids[0]
    
    if st.button("🚀 Analyze with Grok", type="primary"):
        with st.spinner("Fetching live data from CoinGecko..."):
            try:
                coin_data = get_coin_data(coin_id)
                hist_df = get_historical(coin_id, 365)
                
                current_price = coin_data["market_data"]["current_price"]["usd"]
                market_cap = coin_data["market_data"]["market_cap"]["usd"]
                volume = coin_data["market_data"]["total_volume"]["usd"]
                
                st.success(f"✅ Loaded {coin_data['name']} ({coin_data['symbol'].upper()})")
                
                st.subheader("📈 Price History (365 days)")
                st.line_chart(hist_df.set_index("date")["price"], use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("Current Price", f"${current_price:,.4f}")
                with col2: st.metric("Market Cap", f"${market_cap:,.0f}")
                with col3: st.metric("24h Volume", f"${volume:,.0f}")
                
                # ====================== GROK ANALYSIS (FIXED FOR 2026) ======================
                if not xai_key:
                    st.error("Please add your xAI API key in the sidebar")
                else:
                    with st.spinner("Grok is evaluating all 10 criteria + generating 12-month projections..."):
                        client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1")
                        
                        price_change = ((hist_df["price"].iloc[-1] / hist_df["price"].iloc[0]) - 1) * 100
                        
                        context = f"""
                        Coin: {coin_data['name']} ({coin_data['symbol'].upper()})
                        Current price: ${current_price:,.4f}
                        Market cap: ${market_cap:,.0f}
                        24h volume: ${volume:,.0f}
                        365-day price change: {price_change:,.1f}%
                        """
                        
                        prompt = f"""
                        You are an expert crypto analyst. Evaluate exactly against these 10 criteria:

                        1️⃣ Real Problem Being Solved  
                        2️⃣ The Team Behind the Project  
                        3️⃣ Tokenomics  
                        4️⃣ Actual Users  
                        5️⃣ Developer Activity  
                        6️⃣ Partnerships and Ecosystem  
                        7️⃣ Regulatory Awareness  
                        8️⃣ Liquidity and Exchanges  
                        9️⃣ Long-Term Narrative  
                        🔟 Community Quality

                        DATA: {context}

                        For EACH criterion: Score 1-10 + 1-2 sentence explanation.
                        Then: Overall score, Investment thesis, and 12-MONTH PRICE PROJECTIONS (Base / Bull / Bear with % upside).

                        Return clean Markdown with emojis.
                        """
                        
                        response = client.chat.completions.create(
                            model="grok-4-1-fast-reasoning",
                            messages=[
                                {"role": "system", "content": "You are Grok, a maximally truthful crypto analyst."},
                                {"role": "user", "content": prompt}
                            ]
                        )
                        
                        st.markdown("### 🧠 Grok's Full Analysis")
                        st.markdown(response.choices[0].message.content)
                        st.caption("Analysis powered by Grok-4 (xAI) • Data from CoinGecko")
                        
            except Exception as e:
                st.error(f"Error: {str(e)}")
else:
    st.info("Enter a symbol above (BTC, ETH, SOL, etc.) and click Analyze")

st.caption("Educational use only • Crypto is volatile")
