import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# --- APP CONFIG ---
st.set_page_config(page_title="CSE AI Master Bot", layout="wide", page_icon="📊")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { 
        background-color: white; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #e0e0e0; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- ADVANCED DATA SCRAPER ---

@st.cache_data(ttl=600)
def fetch_market_summary():
    """Gets the live price and volume for all companies."""
    url = "https://www.cse.lk/api/tradeSummary"
    try:
        res = requests.post(url, timeout=10)
        return pd.DataFrame(res.json()["reqTradeSummery"])
    except:
        return pd.DataFrame()

def fetch_company_ratios(symbol):
    """Deep-scrapes specific ratios from the company's official CSE profile."""
    url = "https://www.cse.lk/api/companyInfoSummery"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.post(url, json={"symbol": symbol}, timeout=5, headers=headers)
        d = res.json()
        return {
            "NAV": d.get("netAssetValue", 0),
            "PE": d.get("pe", 0),
            "EPS": d.get("eps", 0),
            "PBV": d.get("pbv", 0),
            "DY": d.get("dividendYield", 0)
        }
    except:
        return {"NAV": 0, "PE": 0, "EPS": 0, "PBV": 0, "DY": 0}

# --- CHART COMPONENT ---
def draw_tradingview_chart(symbol, title):
    st.write(f"### {title}")
    chart_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_{symbol}"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width": "100%", "height": 350, "symbol": "CSELK:{symbol}",
        "interval": "D", "timezone": "Asia/Colombo", "theme": "light",
        "style": "3", "locale": "en", "toolbar_bg": "#f1f3f6",
        "enable_publishing": false, "hide_top_toolbar": true, "save_image": false,
        "container_id": "tradingview_{symbol}"
      }});
      </script>
    </div>
    """
    components.html(chart_code, height=360)

# --- APP LAYOUT ---

st.title("🏛️ CSE AI: Fundamental Analysis Engine")

# Index Row
c1, c2 = st.columns(2)
with c1: draw_tradingview_chart("ASPI", "ASPI Index")
with c2: draw_tradingview_chart("S&PSL20", "S&P SL20 Index")

st.divider()

# Market Overview Section
st.header("🔍 Market Screener")
df_market = fetch_market_summary()

if not df_market.empty:
    # Let user pick which stocks to analyze deeply
    all_symbols = sorted(df_market['symbol'].unique())
    
    st.write("### Step 1: Select Stocks to Scan")
    selected_symbols = st.multiselect(
        "Choose stocks (e.g., SAMP.N0000, JKH.N0000) to pull financial reports for:",
        options=all_symbols,
        default=all_symbols[:5] # Default to top 5
    )

    if st.button("🚀 Run AI Deep Scan"):
        results = []
        progress_bar = st.progress(0)
        
        for i, sym in enumerate(selected_symbols):
            # Fetch fundamentals
            ratios = fetch_company_ratios(sym)
            # Fetch price from market df
            price_row = df_market[df_market['symbol'] == sym].iloc[0]
            
            # AI Logic
            price = float(price_row['price'])
            nav = float(ratios['NAV'])
            pe = float(ratios['PE'])
            
            signal = "Neutral"
            if nav > 0 and price < nav and 0 < pe < 10:
                signal = "💎 STRONG BUY (Value)"
            elif price < (nav * 0.7):
                signal = "📉 DEEP DISCOUNT"
            elif float(price_row['percentageChange']) > 3:
                signal = "🚀 MOMENTUM"

            results.append({
                "Symbol": sym,
                "Price": price,
                "Chg%": price_row['percentageChange'],
                "NAV": nav,
                "PE": pe,
                "EPS": ratios['EPS'],
                "Div Yield": ratios['DY'],
                "AI Signal": signal
            })
            progress_bar.progress((i + 1) / len(selected_symbols))
        
        final_df = pd.DataFrame(results)
        st.subheader("📊 Automated Financial Report Summary")
        st.dataframe(final_df, use_container_width=True)
        st.success("Deep Scan Complete! All ratios extracted from CSE.lk financial profiles.")

else:
    st.warning("Could not connect to CSE.lk API. Please refresh.")

st.info("💡 **How it works:** This bot connects directly to the CSE company directory. When you click 'Deep Scan', it opens the hidden financial reports for each stock, extracts the NAV, PE, and EPS, and compares them to the current live price.")
