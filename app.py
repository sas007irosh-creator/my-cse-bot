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

    # 4. PROFIT CALCULATOR SECTION (PRO VERSION)
    st.subheader("💰 Professional Investment Profit Estimator")
    
    # Define CSE Fee Structure (2026 Rates)
    # Total Fee (1.12%) = Broker (0.64%) + CSE (0.084%) + CDS (0.024%) + SEC (0.072%) + STL (0.3%)
    fee_base = 0.0112 
    vat_rate = 0.18  # 18% VAT on the service fees (excluding STL)
    service_fees = 0.0082 # The portion subject to VAT (1.12% - 0.3% STL)
    
    calc_col1, calc_col2, calc_col3 = st.columns(3)
    
    with calc_col1:
        calc_symbol = st.selectbox("Select Share You Own:", df_market['Symbol'].unique())
    with calc_col2:
        buy_price = st.number_input("Your Buy Price (Rs):", min_value=0.0, step=0.1)
    with calc_col3:
        quantity = st.number_input("Number of Shares:", min_value=0, step=1)

    if calc_symbol and buy_price > 0 and quantity > 0:
        current_p = df_market[df_market['Symbol'] == calc_symbol]['Price'].values[0]
        
        # BUY SIDE CALCULATIONS
        gross_buy = buy_price * quantity
        buy_fees = gross_buy * fee_base
        buy_vat = (gross_buy * service_fees) * vat_rate
        total_cost_to_buy = gross_buy + buy_fees + buy_vat
        
        # SELL SIDE CALCULATIONS (Estimate if sold at current price)
        gross_sell = current_p * quantity
        sell_fees = gross_sell * fee_base
        sell_vat = (gross_sell * service_fees) * vat_rate
        net_proceeds_from_sell = gross_sell - sell_fees - sell_vat
        
        # PROFIT / LOSS
        net_profit = net_proceeds_from_sell - total_cost_to_buy
        roi_percentage = (net_profit / total_cost_to_buy) * 100
        
        # DISPLAY RESULTS
        st.markdown(f"**Live Price of {calc_symbol}:** Rs. {current_p}")
        
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("Total Buying Cost", f"Rs. {total_cost_to_buy:,.2f}", help="Price + Fees + VAT")
        res_col2.metric("Net Selling Value", f"Rs. {net_proceeds_from_sell:,.2f}", help="Market Value - Fees - VAT")
        res_col3.metric("Realized Net Profit", f"Rs. {net_profit:,.2f}", f"{roi_percentage:.2f}%")

        # FEE BREAKDOWN TABLE
        with st.expander("🔍 See Fee Breakdown (CSE 2026 Standards)"):
            breakdown_data = {
                "Description": ["Gross Amount", "Brokerage & CSE Fees (1.12%)", f"VAT ({int(vat_rate*100)}% on Fees)", "Total Final Amount"],
                "Buy Side (Initial)": [f"Rs. {gross_buy:,.2f}", f"Rs. {buy_fees:,.2f}", f"Rs. {buy_vat:,.2f}", f"Rs. {total_cost_to_buy:,.2f}"],
                "Sell Side (Current)": [f"Rs. {gross_sell:,.2f}", f"Rs. {sell_fees:,.2f}", f"Rs. {sell_vat:,.2f}", f"Rs. {net_proceeds_from_sell:,.2f}"]
            }
            st.table(pd.DataFrame(breakdown_data))
