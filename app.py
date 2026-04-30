import streamlit as st
import pandas as pd
import requests

# --- APP CONFIG ---
st.set_page_config(page_title="CSE Master Analyzer", layout="wide", page_icon="📈")

# --- DATA FETCHING ---
@st.cache_data(ttl=300)
def fetch_live_market():
    url = "https://www.cse.lk/api/tradeSummary"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.post(url, headers=headers, timeout=10)
        df = pd.DataFrame(res.json()["reqTradeSummery"])
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={'symbol': 'Symbol', 'price': 'Price'})
        df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0)
        return df[['Symbol', 'Price']]
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_fundamentals():
    try:
        df = pd.read_csv("fundamentals.csv")
        df['Symbol'] = df['Symbol'].str.strip()
        return df
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return None

# --- UI LOGIC ---
st.title("🏛️ CSE Professional Analysis Dashboard")

# Sidebar for controls
if st.sidebar.button("🔄 Force Refresh CSV"):
    st.cache_data.clear()
    st.rerun()

df_market = fetch_live_market()
df_fundamentals = load_fundamentals()

if df_fundamentals is not None and not df_market.empty:
    st.subheader("🎯 Deep Financial Analysis")
    selected = st.multiselect("Select Symbols from CSV:", df_fundamentals['Symbol'].unique())
    
    if st.button("🚀 Calculate All Ratios"):
        if not selected:
            st.warning("Please select at least one stock.")
        else:
            # 1. Merge Live Prices with CSV Data
            live_prices = df_market[df_market['Symbol'].isin(selected)]
            data = pd.merge(live_prices, df_fundamentals, on='Symbol', how='inner')
            
            # 2. CALCULATE ALL 8 RATIOS
            # These are now correctly indented inside the 'if' block
            data['NAV per Share'] = data['NAV']
            data['EPS'] = data['EPS']
            data['P/E'] = round(data['Price'] / data['EPS'], 2)
            data['Div Yield (%)'] = round((data['Annual Dividend'] / data['Price']) * 100, 2)
            data['Div Payout Ratio'] = round(data['Annual Dividend'] / data['EPS'], 2)
            data['ROE (%)'] = data['ROE']
            data['ROA (%)'] = data['ROA']
            data['Debt/Equity'] = data['Debt to Equity']
            
            # 3. Highlight Logic
            def color_value(row):
                if 0 < row['P/E'] < 12 and (row['Price'] / row['NAV']) < 1.0:
                    return ['background-color: #d4edda'] * len(row)
                return [''] * len(row)

            # 4. Display Result
            st.dataframe(data.style.apply(color_value, axis=1), use_container_width=True)
            st.success("✅ Ratios calculated using live prices and CSV data.")
else:
    st.info("Ensure fundamentals.csv is uploaded and the CSE market feed is active.")
