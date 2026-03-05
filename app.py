import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import yfinance as yf
import openai
import requests
from datetime import datetime
import pytz
from xml.etree import ElementTree as ET

# ================= PAGE CONFIG =================
st.set_page_config(page_title="AI Trader Terminal", layout="wide")
st.title("📊 AI Trader Terminal — Live OpenAI Analysis + TradingView")

# ================= SESSION STATE =================
if 'analysis' not in st.session_state:
    st.session_state.analysis = None

# ================= SIDEBAR =================
with st.sidebar:
    st.header("API Keys")
    openai_key = st.text_input("OpenAI API Key", type="password", value="")
    st.caption("Get free credits at platform.openai.com")

    st.markdown("---")
    st.header("Settings")
    market_type = st.radio("Market", ["US30"], index=0)  # locked to US30 for now
    rr_ratio = st.slider("Risk:Reward Ratio", 1.0, 3.0, 2.0, 0.5)

# ================= SYMBOLS =================
symbol = "US30"
tv_symbol = st.text_input("TradingView Symbol", value="CAPITALCOM:US30")  # ← works in widget

# ================= NEWS HELPER =================
def get_cnbc_headlines():
    try:
        r = requests.get("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", timeout=8)
        root = ET.fromstring(r.text)
        headlines = [item.find("title").text for item in root.findall(".//item")[:6]]
        return "\n".join(headlines)
    except:
        return "No CNBC headlines available at the moment."

# ================= MAIN BUTTON =================
if st.button("🚀 Run OpenAI Trader Analysis (NY Open Focus)", type="primary"):
    if not openai_key:
        st.error("Please enter your OpenAI API key")
        st.stop()

    with st.spinner("Fetching live data + CNBC news + running OpenAI analysis..."):
        # Fetch price data
        hist = yf.download("^DJI", period="7d", interval="15m", progress=False)
        if hist.empty or len(hist) < 30:
            st.error("Not enough data from Yahoo Finance")
            st.stop()

        current_price = round(hist['Close'].iloc[-1], 0)
        recent_high = round(hist['High'].rolling(40).max().iloc[-1], 0)
        recent_low = round(hist['Low'].rolling(40).min().iloc[-1], 0)
        data_summary = f"""
Current price: {current_price}
Recent high: {recent_high}
Recent low: {recent_low}
Last 8 candles (OHLC):
{hist.tail(8)[['Open','High','Low','Close']].round(0).to_string()}
"""

        news = get_cnbc_headlines()

        ny_time = datetime.now(pytz.timezone("America/New_York")).strftime("%H:%M ET")

        prompt = f"""You are a professional US30/Dow Jones trader preparing for New York open.

Current NY time: {ny_time}
Price action summary:
{data_summary}

Latest CNBC headlines:
{news}

Analyse the full market structure and give me a complete trading plan in **valid JSON only** (no extra text):

{{
  "bias": "Bullish / Bearish / Neutral",
  "order_blocks": ["demand zone 48xxx-48yyy", "supply zone 48aaa-48bbb"],
  "support_levels": [num1, num2],
  "resistance_levels": [num1, num2],
  "liquidity_pools": [num],
  "entry": "Buy limit at XXXX (or market if breaks above YYYY) — within ±10 points",
  "sl": num,
  "tp1": num,
  "tp2": num,
  "reasoning": "Detailed explanation including order blocks, liquidity, market structure, and how CNBC news affects the bias"
}}

Be precise, realistic, and professional. Use round numbers for US30.
"""

        client = openai.OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800
        )

        raw = response.choices[0].message.content.strip()
        try:
            analysis = json.loads(raw)
        except:
            st.error("OpenAI response format issue — please try again")
            st.stop()

        st.session_state.analysis = {
            "price": current_price,
            "analysis": analysis,
            "hist": hist
        }
        st.success("✅ OpenAI analysis complete!")

# ================= DISPLAY =================
if st.session_state.analysis:
    a = st.session_state.analysis["analysis"]
    price = st.session_state.analysis["price"]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("🧠 OpenAI Trader Plan")
        st.markdown(f"""
**Bias**: **{a['bias']}**  
**Entry**: {a['entry']}  
**Stop Loss**: **{a['sl']}**  
**TP1**: **{a['tp1']}**  
**TP2**: **{a['tp2']}**

**Order Blocks**: {a['order_blocks']}  
**Support**: {a['support_levels']}  
**Resistance**: {a['resistance_levels']}  
**Liquidity Pools**: {a['liquidity_pools']}
        """)

    with col2:
        st.subheader("📝 Reasoning")
        st.write(a['reasoning'])

    # ================= TRADINGVIEW CHART =================
    st.subheader("📈 TradingView Live Chart")
    symbol_clean = "US30"
    overlays = []
    for lvl in a.get('support_levels', []):
        overlays.append({"price": float(lvl), "color": "orange", "width": 2})
    for lvl in a.get('resistance_levels', []):
        overlays.append({"price": float(lvl), "color": "red", "width": 2})
    for lvl in a.get('liquidity_pools', []):
        overlays.append({"price": float(lvl), "color": "lime", "width": 3, "linestyle": "dashed"})
    if a.get('sl'):
        overlays.append({"price": float(a['sl']), "color": "purple", "width": 2, "linestyle": "dotted"})
    if a.get('tp1'):
        overlays.append({"price": float(a['tp1']), "color": "#00ff88", "width": 2})
    if a.get('tp2'):
        overlays.append({"price": float(a['tp2']), "color": "#00cc66", "width": 3})

    overlays_json = json.dumps(overlays)

    st.components.v1.html(f"""
    <div class="tradingview-widget-container">
      <div id="tv"></div>
      <script src="https://s3.tradingview.com/tv.js"></script>
      <script>
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
          "container_id": "tv"
        }});
      </script>
    </div>
    """, height=620)

    # ================= PLOTLY =================
    st.subheader("📊 AI Levels Overlay")
    cp = st.session_state.analysis["price"]
    times = pd.date_range(end=datetime.now(), periods=8, freq="15min")
    prices = [cp-300, cp-150, cp, cp+80, cp+180, cp+250, cp+120, cp]

    fig = go.Figure(go.Scatter(x=times, y=prices, mode="lines+markers", name="Price"))
    for lvl in a.get('support_levels', []):
        fig.add_hline(y=lvl, line_dash="dash", line_color="orange", annotation_text=f"Support {lvl}")
    for lvl in a.get('resistance_levels', []):
        fig.add_hline(y=lvl, line_dash="dash", line_color="red", annotation_text=f"Resistance {lvl}")
    for lvl in a.get('liquidity_pools', []):
        fig.add_hline(y=lvl, line_dash="dot", line_color="lime", annotation_text=f"Liquidity {lvl}")
    if a.get('sl'):
        fig.add_hline(y=a['sl'], line_color="purple", annotation_text=f"SL {a['sl']}")
    if a.get('tp1'):
        fig.add_hline(y=a['tp1'], line_color="#00ff88", annotation_text=f"TP1 {a['tp1']}")
    if a.get('tp2'):
        fig.add_hline(y=a['tp2'], line_color="#00cc66", annotation_text=f"TP2 {a['tp2']}")

    fig.update_layout(height=500, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Enter your OpenAI key → click the big button above")

st.caption("Not financial advice • Always verify • Built for demo only")
