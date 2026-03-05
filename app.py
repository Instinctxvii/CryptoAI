import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from openai import OpenAI

st.set_page_config(page_title="AI Crypto Evaluator", page_icon="🚀", layout="wide")
st.title("🚀 AI Crypto Evaluator")
st.markdown("**Grok-powered analysis** against your exact 10 criteria + 12-month price projections")

# ====================== SIDEBAR with xAI API Key Input ======================
with st.sidebar:
    st.header("🔑 xAI API Key (for Grok)")
    
    # Try to get from secrets first (secure for deployed app)
    if "xai_key" not in st.session_state:
        st.session_state.xai_key = st.secrets.get("XAI_API_KEY", None)
    
    # If still not set → show input field
    if st.session_state.xai_key is None or st.session_state.xai_key == "":
        api_input = st.text_input(
            "Paste your xAI API key here",
            type="password",
            placeholder="xai-...",
            help="Get your key at https://console.x.ai → API Keys. This is only stored in your browser session."
        )
        
        if api_input:
            st.session_state.xai_key = api_input
            st.success("Key saved for this session! ✓")
            st.rerun()  # Refresh to hide input and show confirmation
    else:
        st.success("xAI API key is set ✓")
        if st.button("Clear / Change key"):
            st.session_state.xai_key = None
            st.rerun()
    
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
