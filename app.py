import streamlit as st
import pandas as pd
import requests

# --- APP CONFIG ---
st.set_page_config(page_title="CSE Master Analyzer", layout="wide", page_icon="📈")

# Custom CSS for styling
st.markdown("""
<style>
    .stDataFrame { border-radius: 10px; border: 1px solid #e6e9ef; }
    .main { background-color: #f8f9fa; }
</style>
""", unsafe_allow_html=True)

# --- DATA ENGINE ---

@st.cache_data(ttl=300)
def fetch_live_market():
    """Fetches real-time market data from CSE."""
    url = "https://www.cse.lk/api/tradeSummary"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.post(url, headers=headers, timeout=10)
        df = pd.DataFrame(res.json()["reqTradeSummery"])
        
        # Standardize columns to lowercase for safe mapping
        df.columns = [c.lower() for c in df.columns]
        rename_map = {
            'symbol': 'Symbol',
            'price': 'Price',
            'change': 'Change (Rs)',
            'percentagechange': 'Change (%)',
            'sharevolume': 'Share Volume',
            'tradevolume': 'Trade Volume'
        }
        df = df.rename(columns=rename_map)
        
        # Force numeric types
        cols = ['Price', 'Change (Rs)', 'Change (%)', 'Share Volume', 'Trade Volume']
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

@st.cache_data
def load_fundamental_db():
    """Loads static quarterly data from your GitHub-uploaded CSV."""
    try:
        # Tries to read the file from the same folder as app.py
        df = pd.read_csv("fundamentals.csv")
        # Ensure Symbol is cleaned of any spaces
        df['Symbol'] = df['Symbol'].str.strip()
        return df
    except FileNotFoundError:
        return None

# --- UI LAYOUT ---

st.title("🏛️ CSE Industrial Analysis Dashboard")

df_market = fetch_live_market()
df_fundamentals = load_fundamental_db()

# Check if CSV exists
if df_fundamentals is None:
    st.error("❌ **fundamentals.csv NOT FOUND**")
    st.info("""
    **How to fix:**
    1. Create a file named `fundamentals.csv` on your PC.
    2. Add these columns: `Symbol,NAV,EPS,Annual Dividend,ROA,ROE,Debt to Equity`
    3. Upload it to the **root** of your GitHub repository.
    """)
    st.stop()

if not df_market.empty:
    
    st.subheader("🎯 Selection & Deep Analysis")
    # Only allow selection of symbols that exist in BOTH the market and your CSV
    common_symbols = sorted(list(set(df_market['Symbol']) & set(df_fundamentals['Symbol'])))
    
    if not common_symbols:
        st.warning("⚠️ No matching symbols found between the Live Market and your fundamentals.csv. Check your CSV spelling (e.g., ABAN.N0000).")
        st.stop()

    selected = st.multiselect(
        "Select stocks to analyze:", 
        options=common_symbols, 
        default=common_symbols[:3] if len(common_symbols) > 0 else None
    )

    if st.button("🚀 Run Full AI Analysis"):
        # 1. Filter and Merge
        live_data = df_market[df_market['Symbol'].isin(selected)]
        merged_df = pd.merge(live_data, df_fundamentals, on='Symbol', how='inner')
        
        # 2. Live Ratio Calculations
        merged_df['Live P/E'] = round(merged_df['Price'] / merged_df['EPS'], 2)
        merged_df['Live P/B'] = round(merged_df['Price'] / merged_df['NAV'], 2)
        merged_df['Div Yield (%)'] = round((merged_df['Annual Dividend'] / merged_df['Price']) * 100, 2)
        
        # 3. Create TradingView URL
        merged_df['Chart Link'] = merged_df['Symbol'].apply(
            lambda x: f"https://www.tradingview.com/symbols/CSELK:{x}/"
        )

        # 4. Define Highlighting Logic
        def highlight_value(row):
            # Green if P/E < 12 AND P/B < 1.0 (Value Buy)
            if 0 < row['Live P/E'] < 12 and 0 < row['Live P/B'] < 1.0:
                return ['background-color: #d4edda'] * len(row)
            # Red if P/E > 30 (Overvalued)
            elif row['Live P/E'] > 30:
                return ['background-color: #f8d7da'] * len(row)
            return [''] * len(row)

        styled_df = merged_df.style.apply(highlight_value, axis=1)

        # 5. Display with Link Configuration
        st.dataframe(
            styled_df,
            column_config={
                "Price": st.column_config.NumberColumn(format="Rs. %.2f"),
                "Chart Link": st.column_config.LinkColumn(
                    "TradingView Chart",
                    display_text="View Chart 📈"
                ),
                "Share Volume": st.column_config.NumberColumn(format="%d"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.success("✅ Analysis Complete. Green rows = Undervalued | Red rows = Overvalued")

else:
    st.info("Connecting to Colombo Stock Exchange live feed...")
