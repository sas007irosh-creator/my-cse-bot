import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# --- APP CONFIG ---
st.set_page_config(page_title="CSE AI Master Bot", layout="wide", page_icon="📊")

# --- DATA SCRAPING ENGINE ---

@st.cache_data(ttl=300)
def fetch_comprehensive_market():
    """Fetches full market summary including price change and volumes."""
    url = "https://www.cse.lk/api/tradeSummary"
    try:
        res = requests.post(url, timeout=10)
        data = res.json()["reqTradeSummery"]
        df = pd.DataFrame(data)
        
        # Mapping CSE API fields to user-friendly names
        df = df.rename(columns={
            'symbol': 'Symbol',
            'price': 'Price',
            'change': 'Change (Rs)',
            'percentageChange': 'Chg %',
            'shareVolume': 'Share Volume',
            'tradeVolume': 'Trade Volume',
            'lastTradedTime': 'Last Updated'
        })
        return df
    except Exception as e:
        st.error(f"Error fetching market data: {e}")
        return pd.DataFrame()

def fetch_and_calculate_ratios(symbol, current_price):
    """Fetches raw data and calculates ratios manually if needed."""
    url = "https://www.cse.lk/api/companyInfoSummery"
    try:
        res = requests.post(url, json={"symbol": symbol}, timeout=5)
        d = res.json()
        
        # Extract raw values from API (Handling potential '0' or None)
        nav = float(d.get("netAssetValue", 0) or 0)
        eps = float(d.get("eps", 0) or 0)
        pe = float(d.get("pe", 0) or 0)
        dy = float(d.get("dividendYield", 0) or 0)

        # MANUAL CALCULATION FALLBACK
        # If PE is 0 but we have Price and EPS, calculate it: PE = Price / EPS
        if pe == 0 and eps > 0:
            pe = round(current_price / eps, 2)
        
        # PBV Calculation: Price / NAV
        pbv = round(current_price / nav, 2) if nav > 0 else 0

        return {
            "NAV": nav,
            "EPS": eps,
            "PE": pe,
            "PBV": pbv,
            "Div Yield": dy
        }
    except:
        return {"NAV": 0, "EPS": 0, "PE": 0, "PBV": 0, "Div Yield": 0}

# --- UI LAYOUT ---

st.title("🏛️ CSE Industrial Analysis Engine")
st.markdown("### Live Market Data & Fundamental Ratios")

df_market = fetch_comprehensive_market()

if not df_market.empty:
    # 1. Market Overview Table (Price, Change, Volumes)
    st.subheader("📈 Real-Time Trade Monitor")
    display_cols = ['Symbol', 'Price', 'Change (Rs)', 'Chg %', 'Share Volume', 'Trade Volume']
    st.dataframe(df_market[display_cols].sort_values(by='Chg %', ascending=False), use_container_width=True)

    st.divider()

    # 2. Deep Analysis Section
    st.subheader("🎯 Fundamental Ratio Scanner")
    selected_symbols = st.multiselect(
        "Select symbols for Deep Financial Analysis:",
        options=sorted(df_market['Symbol'].unique()),
        default=df_market['Symbol'].head(5).tolist()
    )

    if st.button("🔍 Run Financial Extraction"):
        results = []
        prog = st.progress(0)
        
        for i, sym in enumerate(selected_symbols):
            # Get current price from the market dataframe
            price_val = float(df_market[df_market['Symbol'] == sym]['Price'].values[0])
            
            # Get/Calc Ratios
            ratios = fetch_and_calculate_ratios(sym, price_val)
            
            # Combine data
            row = {"Symbol": sym, "Current Price": price_val}
            row.update(ratios)
            
            # Simple AI Grading
            if row['PBV'] > 0 and row['PBV'] < 1:
                row['Status'] = "🔥 Undervalued"
            elif row['PE'] > 0 and row['PE'] < 12:
                row['Status'] = "✅ Value Buy"
            else:
                row['Status'] = "⚖️ Neutral"
                
            results.append(row)
            prog.progress((i + 1) / len(selected_symbols))
        
        analysis_df = pd.DataFrame(results)
        st.dataframe(analysis_df, use_container_width=True)
else:
    st.error("Unable to load data. Please check your internet connection to CSE.lk.")
