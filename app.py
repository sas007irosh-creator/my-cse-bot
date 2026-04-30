import streamlit as st
import pandas as pd
import requests

# --- APP CONFIG ---
st.set_page_config(page_title="CSE AI Master Bot", layout="wide")

@st.cache_data(ttl=300)
def fetch_safe_market_data():
    url = "https://www.cse.lk/api/tradeSummary"
    try:
        res = requests.post(url, timeout=10)
        raw_data = res.json()["reqTradeSummery"]
        df = pd.DataFrame(raw_data)
        
        # --- DYNAMIC MAPPING ---
        # This prevents KeyError by checking what the API actually sent
        rename_map = {
            'symbol': 'Symbol',
            'price': 'Price',
            'change': 'Change (Rs)',
            'percentageChange': 'Chg %',
            'shareVolume': 'Share Volume',
            'tradeVolume': 'Trade Volume'
        }
        
        # Only rename columns that actually exist in the response
        existing_rename = {k: v for k, v in rename_map.items() if k in df.columns}
        df = df.rename(columns=existing_rename)
        
        # Convert numeric columns to float to ensure sorting works
        numeric_cols = ['Price', 'Change (Rs)', 'Chg %', 'Share Volume', 'Trade Volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        return df
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

# --- UI EXECUTION ---
st.title("📊 CSE Live Industrial Monitor")

df_market = fetch_safe_market_data()

if not df_market.empty:
    # We define the columns we WANT to show
    target_cols = ['Symbol', 'Price', 'Change (Rs)', 'Chg %', 'Share Volume', 'Trade Volume']
    
    # We only show the ones that were successfully found/renamed
    available_cols = [c for c in target_cols if c in df_market.columns]
    
    st.subheader("📈 Real-Time Market Summary")
    
    # Use 'Chg %' if it exists, otherwise sort by Price
    sort_key = 'Chg %' if 'Chg %' in df_market.columns else 'Price'
    
    st.dataframe(
        df_market[available_cols].sort_values(by=sort_key, ascending=False),
        use_container_width=True
    )
else:
    st.info("Waiting for data from CSE.lk...")
