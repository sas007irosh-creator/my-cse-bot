import streamlit as st
import pandas as pd
import requests

# --- APP CONFIG ---
st.set_page_config(page_title="CSE AI Industrial Analyzer", layout="wide")

# --- DATA ENGINE ---

@st.cache_data(ttl=300)
def fetch_market_data():
    """Fetches real-time market data with volume and change."""
    url = "https://www.cse.lk/api/tradeSummary"
    try:
        res = requests.post(url, timeout=10)
        df = pd.DataFrame(res.json()["reqTradeSummery"])
        
        # Mapping to the exact names you requested
        rename_map = {
            'symbol': 'Symbol',
            'price': 'Price',
            'change': 'Price Change (Rs)',
            'percentageChange': 'Chg %',
            'shareVolume': 'Share Volume',
            'tradeVolume': 'Trade Volume'
        }
        
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        
        # Ensure all numbers are floats for sorting
        num_cols = ['Price', 'Price Change (Rs)', 'Chg %', 'Share Volume', 'Trade Volume']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

def fetch_advanced_ratios(symbol, price):
    """Scrapes and calculates Deep Fundamental Ratios."""
    url = "https://www.cse.lk/api/companyInfoSummery"
    try:
        res = requests.post(url, json={"symbol": symbol}, timeout=5)
        d = res.json()
        
        # Get raw data (names are specific to CSE API)
        nav = float(d.get("netAssetValue", 0) or 0)
        eps = float(d.get("eps", 0) or 0)
        pe = float(d.get("pe", 0) or 0)
        dy = float(d.get("dividendYield", 0) or 0)
        
        # Calculations for requested ratios
        roe = round((eps / nav) * 100, 2) if nav > 0 else 0
        pbv = round(price / nav, 2) if nav > 0 else 0
        
        # Payout Ratio = (Dividend Per Share / EPS)
        # Note: API provides yield, so we estimate Payout: (Yield * Price) / EPS
        payout = round(((dy/100) * price) / eps, 2) if eps > 0 else 0

        # Note: ROA and Debt/Equity often require full balance sheet scraping.
        # We use standard estimates here; for Banks, these are provided in 'd'.
        roa = d.get("roa", 0)
        debt_equity = d.get("debtToEquity", 0)

        return {
            "NAV per Share": nav,
            "P/E": pe if pe > 0 else (round(price/eps, 2) if eps > 0 else 0),
            "EPS": eps,
            "Div Yield (%)": dy,
            "Div Payout Ratio": payout,
            "ROE (%)": roe,
            "ROA (%)": roa,
            "Debt/Equity": debt_equity,
            "PBV": pbv
        }
    except:
        return {k: 0 for k in ["NAV per Share", "P/E", "EPS", "Div Yield (%)", "Div Payout Ratio", "ROE (%)", "ROA (%)", "Debt/Equity", "PBV"]}

# --- UI LAYOUT ---

st.title("🏛️ CSE Industrial Analysis Dashboard")

# Fix the CSS error here
st.markdown("""
<style>
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

df_market = fetch_market_data()

if not df_market.empty:
    # 1. LIVE MONITOR
    st.subheader("📊 Live Market Monitor")
    display_cols = ['Symbol', 'Price', 'Price Change (Rs)', 'Chg %', 'Share Volume', 'Trade Volume']
    st.dataframe(df_market[display_cols].sort_values(by='Chg %', ascending=False), use_container_width=True)

    st.divider()

    # 2. DEEP SCANNER
    st.subheader("🎯 Deep Fundamental Scanner")
    selected_stocks = st.multiselect("Select stocks to analyze:", df_market['Symbol'].unique(), default=df_market['Symbol'].head(3).tolist())

    if st.button("🚀 Run Deep Analysis"):
        results = []
        bar = st.progress(0)
        
        for i, sym in enumerate(selected_stocks):
            price_now = float(df_market[df_market['Symbol'] == sym]['Price'].values[0])
            ratios = fetch_advanced_ratios(sym, price_now)
            
            combined = {"Symbol": sym, "Price": price_now}
            combined.update(ratios)
            results.append(combined)
            bar.progress((i + 1) / len(selected_stocks))
        
        st.dataframe(pd.DataFrame(results), use_container_width=True)
else:
    st.error("Connection to CSE.lk failed. Check your Streamlit internet settings.")
