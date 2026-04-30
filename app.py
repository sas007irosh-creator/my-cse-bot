import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# --- APP CONFIG ---
st.set_page_config(page_title="CSE AI Master Bot", layout="wide", page_icon="📊")

# --- CUSTOM CSS (FIXED ERROR HERE) ---
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

# --- DATA FETCHING ---

@st.cache_data(ttl=600)
def fetch_market_with_fundamentals():
    market_url = "https://www.cse.lk/api/tradeSummary"
    fundamentals_url = "https://www.cse.lk/api/companyInfoSummery"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.post(market_url, timeout=10)
        res_data = res.json()
        
        if "reqTradeSummery" not in res_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(res_data["reqTradeSummery"])
        
        # Filter top 30 to keep the app fast and avoid server blocks
        df = df.sort_values(by='tradevolume', ascending=False).head(30)
        
        fundamentals_list = []
        for symbol in df['symbol']:
            try:
                f_res = requests.post(fundamentals_url, json={"symbol": symbol}, timeout=5, headers=headers)
                f_data = f_res.json()
                fundamentals_list.append({
                    "symbol": symbol,
                    "NAV": f_data.get("netAssetValue", 0),
                    "PE": f_data.get("pe", 0),
                    "EPS": f_data.get("eps", 0)
                })
            except:
                fundamentals_list.append({"symbol": symbol, "NAV": 0, "PE": 0, "EPS": 0})
        
        f_df = pd.DataFrame(fundamentals_list)
        final_df = pd.merge(df, f_df, on='symbol')
        
        # Ensure numbers are treated as numbers
        numeric_cols = ['price', 'percentageChange', 'NAV', 'PE', 'EPS']
        for col in numeric_cols:
            final_df[col] = pd.to_numeric(final_df[col], errors='coerce').fillna(0)
            
        return final_df
    except Exception as e:
        return pd.DataFrame()

# --- CHART COMPONENT ---
def draw_tradingview_chart(symbol, title):
    st.write(f"### {title}")
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

# Top Charts
col_aspi, col_sp = st.columns(2)
with col_aspi:
    draw_tradingview_chart("ASPI", "ASPI Index")
with col_sp:
    draw_tradingview_chart("S&PSL20", "S&P SL20 Index")

st.divider()

# Market Table
st.header("🔥 Live Market Analysis")

with st.spinner("Scraping live financials from CSE.lk..."):
    full_data = fetch_market_with_fundamentals()

if not full_data.empty:
    def ai_logic(row):
        # Value Logic: Price < NAV and PE < 12
        if row['NAV'] > 0 and row['price'] < row['NAV'] and 0 < row['PE'] < 12:
            return "💎 STRONG BUY"
        elif row['percentageChange'] > 3:
            return "🚀 MOMENTUM"
        elif row['NAV'] > 0 and row['price'] < (row['NAV'] * 0.8):
            return "📉 DEEP VALUE"
        else:
            return "Neutral"

    full_data['AI_Signal'] = full_data.apply(ai_logic, axis=1)

    display_cols = ['symbol', 'name', 'price', 'percentageChange', 'NAV', 'PE', 'EPS', 'AI_Signal']
    
    st.dataframe(
        full_data[display_cols].sort_values(by='percentageChange', ascending=False),
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("⚠️ Data could not be fetched. The CSE website might be down or busy. Please refresh in a moment.")

st.info("💡 **Note:** NAV and PE ratios are scraped in real-time. 'STRONG BUY' signals appear when a stock is trading below its Net Asset Value with a reasonable P/E ratio.")
