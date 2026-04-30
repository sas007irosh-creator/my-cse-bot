import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# --- APP CONFIG ---
st.set_page_config(page_title="CSE Industrial Master Dashboard", layout="wide", page_icon="📊")

# --- CUSTOM STYLING ---
st.markdown("""
<style>
    .stDataFrame { border-radius: 10px; border: 1px solid #e6e9ef; }
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# --- CHART COMPONENT ---
def draw_index_chart(symbol, title):
    """Embeds a live TradingView chart for the given CSE Index."""
    st.write(f"#### {title}")
    chart_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_{symbol}"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width": "100%", "height": 300, "symbol": "CSELK:{symbol}",
        "interval": "D", "timezone": "Asia/Colombo", "theme": "light",
        "style": "2", "locale": "en", "toolbar_bg": "#f1f3f6",
        "enable_publishing": false, "hide_top_toolbar": true, "save_image": false,
        "container_id": "tradingview_{symbol}"
      }});
      </script>
    </div>
    """
    components.html(chart_code, height=310)

# --- DATA ENGINES ---
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
    except:
        return None

# --- UI LAYOUT ---
st.title("🏛️ CSE Professional Analysis Dashboard")

# 1. TOP SECTION: INDEX CHARTS
st.subheader("📈 Market Index Watch")
col_idx1, col_idx2 = st.columns(2)
with col_idx1:
    draw_index_chart("ASPI", "All Share Price Index (ASPI)")
with col_idx2:
    draw_index_chart("S&PSL20", "S&P Sri Lanka 20")

st.divider()

# 2. DATA LOADING
df_market = fetch_live_market()
df_fundamentals = load_fundamentals()

if df_fundamentals is not None and not df_market.empty:
    
    # 3. ANALYSIS SECTION
    st.subheader("🎯 Deep Financial Analysis")
    selected_stocks = st.multiselect("Select Stocks to Analyze:", df_fundamentals['Symbol'].unique(), default=df_fundamentals['Symbol'].iloc[0])
    
    if st.button("🚀 Calculate All Ratios"):
        live_prices = df_market[df_market['Symbol'].isin(selected_stocks)]
        data = pd.merge(live_prices, df_fundamentals, on='Symbol', how='inner')
        
        # Calculate Ratios
        data['P/E'] = round(data['Price'] / data['EPS'], 2)
        data['Div Yield (%)'] = round((data['Annual Dividend'] / data['Price']) * 100, 2)
        data['Div Payout Ratio'] = round(data['Annual Dividend'] / data['EPS'], 2)
        data['P/B'] = round(data['Price'] / data['NAV'], 2)
        data['Chart Link'] = data['Symbol'].apply(lambda x: f"https://www.tradingview.com/symbols/CSELK:{x}/")
        
        # Select and Reorder for display
        display_cols = ['Symbol', 'Price', 'NAV', 'P/B', 'EPS', 'P/E', 'Div Yield (%)', 'Div Payout Ratio', 'ROE', 'ROA', 'Debt to Equity', 'Chart Link']
        
        # Styling
        def highlight_val(row):
            if 0 < row['P/E'] < 12 and row['P/B'] < 1.0:
                return ['background-color: #dcfce7'] * len(row)
            return [''] * len(row)

        st.dataframe(
            data[display_cols].style.apply(highlight_val, axis=1),
            column_config={
                "Chart Link": st.column_config.LinkColumn("Share Chart", display_text="View Chart 📈")
            },
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    # 4. PROFIT CALCULATOR SECTION
    st.subheader("💰 Investment Profit Estimator")
    calc_col1, calc_col2, calc_col3 = st.columns(3)
    
    with calc_col1:
        calc_symbol = st.selectbox("Select Share You Own:", df_market['Symbol'].unique())
    with calc_col2:
        buy_price = st.number_input("Your Buy Price (Rs):", min_value=0.0, step=0.1)
    with calc_col3:
        quantity = st.number_input("Number of Shares:", min_value=0, step=1)

    if calc_symbol:
        current_p = df_market[df_market['Symbol'] == calc_symbol]['Price'].values[0]
        st.info(f"**Current Market Price of {calc_symbol}:** Rs. {current_p}")
        
        if buy_price > 0 and quantity > 0:
            investment = buy_price * quantity
            current_value = current_p * quantity
            profit_loss = current_value - investment
            percentage = (profit_loss / investment) * 100
            
            p_col1, p_col2, p_col3 = st.columns(3)
            p_col1.metric("Total Investment", f"Rs. {investment:,.2f}")
            p_col2.metric("Current Value", f"Rs. {current_value:,.2f}")
            p_col3.metric("Profit / Loss", f"Rs. {profit_loss:,.2f}", f"{percentage:.2f}%")

else:
    st.error("Missing Data: Please ensure 'fundamentals.csv' is uploaded and the CSE API is reachable.")
