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
        
        # Standardize columns
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
    """Loads static quarterly data from your uploaded CSV."""
    try:
        return pd.read_csv("fundamentals.csv")
    except FileNotFoundError:
        st.error("⚠️ fundamentals.csv not found! Please upload it to GitHub.")
        return pd.DataFrame()

# --- UI LAYOUT ---

st.title("🏛️ CSE Industrial Analysis Dashboard")

df_market = fetch_live_market()
df_fundamentals = load_fundamental_db()

if not df_market.empty and not df_fundamentals.empty:
    
    st.subheader("🎯 Selection & Deep Analysis")
    selected = st.multiselect(
        "Select stocks to analyze:", 
        options=sorted(df_market['Symbol'].unique()), 
        default=['ABAN.N0000', 'ACL.N0000', 'AEL.N0000']
    )

    if st.button("🚀 Run Full AI Analysis"):
        # 1. Filter and Merge
        live_data = df_market[df_market['Symbol'].isin(selected)]
        merged_df = pd.merge(live_data, df_fundamentals, on='Symbol', how='left')
        
        # 2. Live Ratio Calculations
        merged_df['Live P/E'] = round(merged_df['Price'] / merged_df['EPS'], 2)
        merged_df['Live P/B'] = round(merged_df['Price'] / merged_df['NAV'], 2)
        merged_df['Div Yield (%)'] = round((merged_df['Annual Dividend'] / merged_df['Price']) * 100, 2)
        
        # 3. Create TradingView URL
        merged_df['Chart Link'] = merged_df['Symbol'].apply(
            lambda x: f"https://www.tradingview.com/symbols/CSELK:{x}/"
        )

        # 4. Apply Conditional Formatting (Highlighting)
        def highlight_value(row):
            """Returns a color list for the row based on value criteria."""
            # Default color (None)
            colors = [''] * len(row)
            
            # Green if P/E is low and P/B is under 1 (Under NAV)
            if 0 < row['Live P/E'] < 12 and row['Live P/B'] < 1.0:
                return ['background-color: #d4edda'] * len(row)
            # Red if P/E is very high
            elif row['Live P/E'] > 30:
                return ['background-color: #f8d7da'] * len(row)
            return colors

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
        
        st.success("✅ Analysis Complete. Green rows indicate stocks trading below NAV with a healthy P/E.")

else:
    st.info("Awaiting live market data and fundamentals.csv upload...")
