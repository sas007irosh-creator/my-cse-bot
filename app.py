import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# --- APP CONFIG ---
st.set_page_config(page_title="CSE Master Analyzer", layout="wide", page_icon="📈")

# Fix the CSS Error here (unsafe_allow_html)
st.markdown("""
<style>
    .stDataFrame { border-radius: 10px; border: 1px solid #e6e9ef; }
    .main { background-color: #f8f9fa; }
</style>
""", unsafe_allow_html=True)

# --- CHART COMPONENT ---
def draw_tradingview_chart(symbol, title):
    """Embeds a live TradingView chart for the given CSE Index."""
    st.write(f"### {title}")
    chart_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_{symbol}"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width": "100%", "height": 350, "symbol": "CSELK:{symbol}",
        "interval": "D", "timezone": "Asia/Colombo", "theme": "light",
        "style": "2", "locale": "en", "toolbar_bg": "#f1f3f6",
        "enable_publishing": false, "hide_top_toolbar": true, "save_image": false,
        "container_id": "tradingview_{symbol}"
      }});
      </script>
    </div>
    """
    components.html(chart_code, height=360)

# --- DATA ENGINE ---
@st.cache_data(ttl=300)
def fetch_safe_market_data():
    """Fetches market data and safely maps columns to avoid KeyErrors."""
    url = "https://www.cse.lk/api/tradeSummary"
    try:
        res = requests.post(url, timeout=10)
        df = pd.DataFrame(res.json()["reqTradeSummery"])
        
        # Lowercase all incoming columns to prevent case-sensitivity KeyErrors
        df.columns = [c.lower() for c in df.columns]
        
        # Safe Mapping
        rename_map = {
            'symbol': 'Symbol',
            'price': 'Price',
            'change': 'Change (Rs)',
            'percentagechange': 'Change (%)',
            'sharevolume': 'Share Volume',
            'tradevolume': 'Trade Volume'
        }
        df = df.rename(columns=rename_map)
        
        # Ensure numbers are treated as numbers for correct sorting
        cols_to_fix = ['Price', 'Change (Rs)', 'Change (%)', 'Share Volume', 'Trade Volume']
        for col in cols_to_fix:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def fetch_deep_ratios(symbol, price):
    """Extracts base metrics from CSE API and calculates advanced fundamental ratios."""
    url = "https://www.cse.lk/api/companyInfoSummery"
    try:
        res = requests.post(url, json={"symbol": symbol}, timeout=5)
        d = res.json()
        
        # Extract raw data from API response
        nav = float(d.get("netAssetValue", 0) or 0)
        eps = float(d.get("eps", 0) or 0)
        pe = float(d.get("pe", 0) or 0)
        dy = float(d.get("dividendYield", 0) or 0)
        roa = float(d.get("roa", 0) or 0)
        debt_equity = float(d.get("debtToEquity", 0) or 0)
        
        # Custom Fundamental Calculations
        roe = round((eps / nav) * 100, 2) if nav > 0 else 0
        payout = round(((dy/100) * price) / eps, 2) if eps > 0 else 0
        
        # Fallback for PE if missing from API
        if pe == 0 and eps > 0:
            pe = round(price / eps, 2)

        return {
            "NAV per Share": nav,
            "P/E": pe,
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
st.title("🏛️ CSE Master Analysis Engine")

# TOP: Market Indices
st.subheader("📈 Market Indices")
c1, c2 = st.columns(2)
with c1: 
    draw_tradingview_chart("ASPI", "All Share Price Index (ASPI)")
with c2: 
    draw_tradingview_chart("S&PSL20", "S&P Sri Lanka 20 Index")

st.divider()

# Fetch Market Data
df_market = fetch_safe_market_data()

if not df_market.empty:
    # MIDDLE: Live Monitor Table
    st.subheader("📊 Live Market Monitor")
    
    # Safely select only columns that successfully loaded
    requested_cols = ['Symbol', 'Price', 'Change (Rs)', 'Change (%)', 'Share Volume', 'Trade Volume']
    actual_cols = [c for c in requested_cols if c in df_market.columns]
    
    st.dataframe(
        df_market[actual_cols].sort_values(by='Change (%)', ascending=False), 
        use_container_width=True
    )

    st.divider()

    # BOTTOM: Deep Financial Scanner
    st.subheader("🎯 Deep Financial Scanner")
    st.write("Extracts and calculates fundamental ratios directly from the CSE financial statements.")
    
    selected = st.multiselect(
        "Select stocks to analyze:", 
        options=sorted(df_market['Symbol'].unique()), 
        default=df_market['Symbol'].head(5).tolist()
    )

    if st.button("🚀 Run Full Financial Analysis"):
        results = []
        bar = st.progress(0)
        
        for i, sym in enumerate(selected):
            # Grab current live price for calculations
            price_now = float(df_market[df_market['Symbol'] == sym]['Price'].values[0])
            
            # Fetch and calculate ratios
            ratios = fetch_deep_ratios(sym, price_now)
            
            # Combine into a single row
            combined = {"Symbol": sym, "Price": price_now}
            combined.update(ratios)
            results.append(combined)
            
            # Update progress bar
            bar.progress((i + 1) / len(selected))
        
        # Display final AI-generated table
        st.dataframe(pd.DataFrame(results), use_container_width=True)
else:
    st.warning("Data is currently unavailable from the CSE server. Please check your internet connection or refresh.")
