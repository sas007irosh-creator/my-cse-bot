import streamlit as st
import pandas as pd
import requests

# --- APP CONFIG ---
st.set_page_config(page_title="CSE Industrial Analyzer", layout="wide")

# --- DATA SCRAPING ENGINE ---

@st.cache_data(ttl=300)
def fetch_safe_market_data():
    """Fetches market data and safely maps volume columns to avoid KeyErrors."""
    url = "https://www.cse.lk/api/tradeSummary"
    try:
        res = requests.post(url, timeout=10)
        df = pd.DataFrame(res.json()["reqTradeSummery"])
        
        # Mapping: API Internal Name -> Your Requested Display Name
        # We use a case-insensitive check to find the columns
        rename_map = {
            'symbol': 'Symbol',
            'price': 'Price',
            'change': 'Price Change (Rs)',
            'percentageChange': 'Chg %',
            'sharevolume': 'Share Volume',
            'tradevolume': 'Trade Volume'
        }
        
        # Standardize API columns to lowercase for a guaranteed match
        df.columns = [c.lower() for c in df.columns]
        
        # Apply the rename
        df = df.rename(columns=rename_map)
        
        # Ensure numeric conversion so sorting works
        cols_to_fix = ['Price', 'Price Change (Rs)', 'Chg %', 'Share Volume', 'Trade Volume']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def fetch_deep_ratios(symbol, price):
    """Fetches and calculates the full list of requested financial ratios."""
    url = "https://www.cse.lk/api/companyInfoSummery"
    try:
        res = requests.post(url, json={"symbol": symbol}, timeout=5)
        d = res.json()
        
        nav = float(d.get("netAssetValue", 0) or 0)
        eps = float(d.get("eps", 0) or 0)
        pe = float(d.get("pe", 0) or 0)
        dy = float(d.get("dividendYield", 0) or 0)
        
        # Calculations
        roe = round((eps / nav) * 100, 2) if nav > 0 else 0
        roa = d.get("roa", 0) or 0
        debt_equity = d.get("debtToEquity", 0) or 0
        payout = round(((dy/100) * price) / eps, 2) if eps > 0 else 0

        return {
            "NAV per Share": nav,
            "P/E": pe if pe > 0 else (round(price/eps, 2) if eps > 0 else 0),
            "EPS": eps,
            "Div Yield (%)": dy,
            "Div Payout Ratio": payout,
            "ROE (%)": roe,
            "ROA (%)": roa,
            "Debt/Equity": debt_equity
        }
    except:
        return {k: 0 for k in ["NAV per Share", "P/E", "EPS", "Div Yield (%)", "Div Payout Ratio", "ROE (%)", "ROA (%)", "Debt/Equity"]}

# --- UI LAYOUT ---

st.title("🏛️ CSE Industrial Analysis Dashboard")

# CSS fix for safe HTML rendering
st.markdown("<style>.stDataFrame { border-radius: 10px; }</style>", unsafe_allow_html=True)

df_market = fetch_safe_market_data()

if not df_market.empty:
    # 1. LIVE MONITOR (Fixed KeyError Section)
    st.subheader("📊 Live Market Monitor")
    
    # We only try to display columns that actually exist now
    requested_cols = ['Symbol', 'Price', 'Price Change (Rs)', 'Chg %', 'Share Volume', 'Trade Volume']
    actual_cols = [c for c in requested_cols if c in df_market.columns]
    
    st.dataframe(
        df_market[actual_cols].sort_values(by='Chg %', ascending=False), 
        use_container_width=True
    )

    st.divider()

    # 2. DEEP SCANNER
    st.subheader("🎯 Deep Financial Scanner")
    selected = st.multiselect("Select stocks:", df_market['Symbol'].unique(), default=df_market['Symbol'].head(3).tolist())

    if st.button("🚀 Run Deep Analysis"):
        results = []
        bar = st.progress(0)
        
        for i, sym in enumerate(selected):
            price_now = float(df_market[df_market['Symbol'] == sym]['Price'].values[0])
            ratios = fetch_deep_ratios(sym, price_now)
            
            combined = {"Symbol": sym, "Price": price_now}
            combined.update(ratios)
            results.append(combined)
            bar.progress((i + 1) / len(selected))
        
        st.dataframe(pd.DataFrame(results), use_container_width=True)
else:
    st.warning("Data is currently unavailable from the CSE server. Please refresh.")
