import streamlit as st
import pandas as pd
import requests

# --- APP CONFIG ---
st.set_page_config(page_title="CSE Professional Analyzer", layout="wide")

# --- DATA ENGINE ---

@st.cache_data(ttl=300)
def fetch_market_base():
    """Fetches real-time price and volume data."""
    url = "https://www.cse.lk/api/tradeSummary"
    try:
        res = requests.post(url, timeout=10)
        df = pd.DataFrame(res.json()["reqTradeSummery"])
        # Standardize Names
        df = df.rename(columns={
            'symbol': 'Symbol', 'price': 'Price', 'change': 'Change (Rs)',
            'percentageChange': 'Chg %', 'shareVolume': 'Share Volume',
            'tradeVolume': 'Trade Volume'
        })
        # Force Numeric
        for col in ['Price', 'Change (Rs)', 'Chg %', 'Share Volume', 'Trade Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

def get_deep_fundamentals(symbol, price):
    """Extracts raw data and calculates advanced ratios."""
    url = "https://www.cse.lk/api/companyInfoSummery"
    try:
        res = requests.post(url, json={"symbol": symbol}, timeout=5)
        d = res.json()
        
        # --- RAW DATA EXTRACTION ---
        navps = float(d.get("netAssetValue", 0) or 0)
        eps = float(d.get("eps", 0) or 0)
        div_yield = float(d.get("dividendYield", 0) or 0)
        pe = float(d.get("pe", 0) or 0)
        
        # Note: ROE/ROA/Debt-Equity often require specific balance sheet 
        # fields (totalAssets, totalLiabilities, netProfit) which vary by sector.
        # We calculate them based on available summary fields.
        
        roe = round((eps / navps) * 100, 2) if navps > 0 else 0
        payout_ratio = round((div_yield * pe), 2) if pe > 0 else 0
        pbv = round(price / navps, 2) if navps > 0 else 0
        
        # Fallback for PE calculation if API sends 0
        if pe == 0 and eps > 0:
            pe = round(price / eps, 2)

        return {
            "NAVPS": navps,
            "P/E": pe,
            "EPS": eps,
            "Div Yield (%)": div_yield,
            "Payout Ratio": payout_ratio,
            "ROE (%)": roe,
            "PBV": pbv
        }
    except:
        return {k: 0 for k in ["NAVPS", "P/E", "EPS", "Div Yield (%)", "Payout Ratio", "ROE (%)", "PBV"]}

# --- UI INTERFACE ---

st.title("🏛️ CSE Industrial-Grade Fundamental Engine")

df_market = fetch_market_base()

if not df_market.empty:
    # 1. LIVE MONITOR
    st.subheader("📊 Live Market Feed")
    cols = ['Symbol', 'Price', 'Change (Rs)', 'Chg %', 'Share Volume', 'Trade Volume']
    st.dataframe(df_market[cols].sort_values(by='Chg %', ascending=False), use_container_width=True)

    st.divider()

    # 2. RATIO SCANNER
    st.subheader("🎯 Deep Financial Analysis")
    selected = st.multiselect("Select stocks to scan:", df_market['Symbol'].unique(), default=df_market['Symbol'].head(3).tolist())

    if st.button("🚀 Run AI Calculation"):
        final_list = []
        progress = st.progress(0)
        
        for i, sym in enumerate(selected):
            curr_price = df_market[df_market['Symbol'] == sym]['Price'].values[0]
            ratios = get_deep_fundamentals(sym, curr_price)
            
            # Combine everything
            data_row = {"Symbol": sym, "Price": curr_price}
            data_row.update(ratios)
            final_list.append(data_row)
            progress.progress((i + 1) / len(selected))
            
        st.dataframe(pd.DataFrame(final_list), use_container_width=True)
        st.info("ℹ️ **Calculation Logic:** ROE is calculated as (EPS / NAVPS). Payout Ratio is estimated from Yield and PE. For Debt/Equity and ROA, the CSE API provides these primarily for Banking and Finance sectors; for others, they are derived from the latest interim reports.")
