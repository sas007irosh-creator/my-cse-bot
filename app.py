import streamlit as st
import pandas as pd
import requests

# --- APP CONFIG ---
st.set_page_config(page_title="CSE AI Auto-Trader", layout="wide", page_icon="🤖")

st.title("🤖 CSE AI: Fully Automated Fundamental Bot")
st.caption("Fetching live data and fundamental ratios directly from CSE.lk")

# --- DATA FUNCTIONS ---

@st.cache_data(ttl=3600) # Only refresh market list once per hour
def get_market_summary():
    url = "https://www.cse.lk/api/tradeSummary"
    try:
        response = requests.post(url, timeout=10)
        return pd.DataFrame(response.json()["reqTradeSummery"])
    except:
        return pd.DataFrame()

@st.cache_data(ttl=86400) # Fundamentals change slowly, so we cache for 24 hours
def get_company_fundamentals(symbol):
    """Fetches NAV, PE, and EPS directly from CSE for a specific stock."""
    url = "https://www.cse.lk/api/companyInfoSummery"
    try:
        # We send a request for the specific company
        response = requests.post(url, json={"symbol": symbol}, timeout=5)
        data = response.json()
        return {
            "NAV": data.get("netAssetValue", 0),
            "PE": data.get("pe", 0),
            "EPS": data.get("eps", 0),
            "PBV": data.get("pbv", 0)
        }
    except:
        return {"NAV": 0, "PE": 0, "EPS": 0, "PBV": 0}

# --- MAIN LOGIC ---

df_market = get_market_summary()

if not df_market.empty:
    # 1. Cleaning the price data
    df_market['price'] = pd.to_numeric(df_market['price'], errors='coerce')
    
    # 2. Sidebar Search
    st.sidebar.header("Search & Analyze")
    all_symbols = sorted(df_market['symbol'].unique())
    selected_stock = st.sidebar.selectbox("Select a Stock to Analyze", all_symbols)

    # 3. Automatic Deep-Dive for Selected Stock
    if selected_stock:
        with st.spinner(f'Fetching latest fundamentals for {selected_stock}...'):
            f_data = get_company_fundamentals(selected_stock)
            m_data = df_market[df_market['symbol'] == selected_stock].iloc[0]
            
            # AI Logic Calculations
            price = m_data['price']
            nav = float(f_data['NAV'])
            pe = float(f_data['PE'])
            
            # THE AI SCOREBOARD
            st.subheader(f"Analysis for {selected_stock} ({m_data['name']})")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Market Price", f"Rs. {price}")
            col2.metric("NAV Per Share", f"Rs. {nav}")
            col3.metric("P/E Ratio", pe)
            col4.metric("Earnings Per Share", f"Rs. {f_data['EPS']}")

            # AI RECOMMENDATION ENGINE
            st.divider()
            st.write("### 🤖 AI Recommendation")
            
            if nav > 0:
                p_to_nav = price / nav
                if p_to_nav < 0.8 and pe < 12 and pe > 0:
                    st.success(f"🔥 **STRONG BUY:** This stock is trading at {int((1-p_to_nav)*100)}% discount to its assets (NAV) with a healthy P/E.")
                elif p_to_nav < 1.0:
                    st.info("✅ **BUY/WATCH:** Trading slightly below its asset value.")
                else:
                    st.warning("❄️ **HOLD/OVERVALUED:** Trading above its net asset value.")
            else:
                st.write("Awaiting more financial data for full recommendation.")

    # 4. General Market Table
    st.divider()
    st.subheader("Live Market Movers")
    st.dataframe(df_market[['symbol', 'name', 'price', 'percentageChange', 'tradevolume']].sort_values(by='tradevolume', ascending=False).head(20))

else:
    st.error("Could not connect to CSE servers. Please check your internet or try again later.")
