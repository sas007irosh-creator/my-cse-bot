import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# --- APP CONFIG ---
st.set_page_config(page_title="CSE AI Master Bot", layout="wide", page_icon="📊")

# --- CUSTOM CSS FOR BETTER LOOK ---
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_index=True)

# --- DATA FETCHING (AUTOMATIC SCRAPING) ---

@st.cache_data(ttl=600)
def fetch_market_with_fundamentals():
    """
    Scrapes the daily trade summary and then automatically 
    fetches fundamental ratios for each company.
    """
    market_url = "https://www.cse.lk/api/tradeSummary"
    fundamentals_url = "https://www.cse.lk/api/companyInfoSummery"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        # 1. Get Market Prices
        res = requests.post(market_url, timeout=10)
        df = pd.DataFrame(res.json()["reqTradeSummery"])
        
        # We only take the top 50 by volume to keep the app fast
        df = df.sort_values(by='tradevolume', ascending=False).head(50)
        
        # 2. Automatically Scrape Fundamentals for each stock in the list
        fundamentals_list = []
        for symbol in df['symbol']:
            try:
                f_res = requests.post(fundamentals_url, json={"symbol": symbol}, timeout=5, headers=headers)
                f_data = f_res.json()
                fundamentals_list.append({
                    "symbol": symbol,
                    "NAV": f_data.get("netAssetValue", 0),
                    "PE": f_data.get("pe", 0),
                    "EPS": f_data.get("eps", 0),
                    "PBV": f_data.get("pbv", 0)
                })
            except:
                fundamentals_list.append({"symbol": symbol, "NAV": 0, "PE": 0, "EPS": 0, "PBV": 0})
        
        f_df = pd.DataFrame(fundamentals_list)
        final_df = pd.merge(df, f_df, on='symbol')
        
        # Cleaning Data Types
        final_df['price'] = pd.to_numeric(final_df['price'], errors='coerce')
        final_df['NAV'] = pd.to_numeric(final_df['NAV'], errors='coerce')
        final_df['PE'] = pd.to_numeric(final_df['PE'], errors='coerce')
        
        return final_df
    except Exception as e:
        st.error(f"Failed to scrape CSE.lk: {e}")
        return pd.DataFrame()

# --- CHART COMPONENT ---
def draw_tradingview_chart(symbol, title):
    st.write(f"### {title}")
    # Using TradingView Widget for ASPI and S&P SL20
    # Note: ASPI = CSE:ASPI, S&P SL20 = CSE:S&PSL20
    chart_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_{symbol}"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width": "100%",
        "height": 400,
        "symbol": "CSELK:{symbol}",
        "interval": "D",
        "timezone": "Asia/Colombo",
        "theme": "light",
        "style": "3",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "hide_top_toolbar": true,
        "save_image": false,
        "container_id": "tradingview_{symbol}"
      }});
      </script>
    </div>
    """
    components.html(chart_code, height=410)

# --- APP LAYOUT ---

st.title("🏛️ CSE AI: Institutional Grade Dashboard")

# Top Charts Row
col_aspi, col_sp = st.columns(2)
with col_aspi:
    draw_tradingview_chart("ASPI", "ASPI Index (All Share)")
with col_sp:
    draw_tradingview_chart("S&PSL20", "S&P SL20 Index")

st.divider()

# Market Table with Automated Fundamentals
st.header("🔥 Live Market Movers & Fundamental Ratios")
st.write("This table automatically scrapes NAV, PE, and EPS for the highest volume stocks.")

with st.spinner("Scraping live financials from CSE.lk..."):
    full_data = fetch_market_with_fundamentals()

if not full_data.empty:
    # Adding an AI Recommendation Column
    def ai_logic(row):
        if row['NAV'] > 0 and row['price'] < row['NAV'] and row['PE'] < 10 and row['PE'] > 0:
            return "💎 STRONG BUY (UNDER NAV)"
        elif row['percentageChange'] > 2:
            return "🚀 MOMENTUM"
        else:
            return "Neutral"

    full_data['AI_Signal'] = full_data.apply(ai_logic, axis=1)

    # Columns to display
    display_cols = [
        'symbol', 'name', 'price', 'percentageChange', 
        'NAV', 'PE', 'EPS', 'AI_Signal'
    ]
    
    st.dataframe(
        full_data[display_cols].sort_values(by='percentageChange', ascending=False),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("The market is currently being scanned. If it stays blank, refresh in 10 seconds.")

st.info("💡 **Tip:** The 'NAV' and 'PE' columns are now scraped directly from the official CSE company profiles in real-time.")
