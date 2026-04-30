import streamlit as st
import pandas as pd
import requests

# 1. Setup the Web Page
st.set_page_config(page_title="CSE AI Trading Bot", layout="wide")
st.title("📊 CSE AI Fundamental Analysis Bot")
st.write("This bot analyzes the Colombo Stock Exchange for buying opportunities.")

# 2. The Data Scraper (Getting the live data)
@st.cache_data(ttl=3600) # Only refresh data once per hour to be safe
def get_data():
    url = "https://www.cse.lk/api/tradeSummary"
    try:
        response = requests.post(url)
        data = response.json()
        return pd.DataFrame(data["reqTradeSummery"])
    except:
        return pd.DataFrame()

# 3. The Logic (The 'Brain' of your bot)
df = get_data()

if not df.empty:
    # Basic cleaning
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Simple AI Scoring Filter (Example: High Volume + Positive Growth)
    # In a real bot, we'd add the P/E and ROE here.
    suggestions = df[df['percentageChange'] > 0].sort_values(by='tradevolume', ascending=False)
    
    st.subheader("🚀 Top Buy Suggestions (Based on Momentum)")
    st.dataframe(suggestions[['symbol', 'name', 'price', 'percentageChange', 'tradevolume']])
    
    st.info("Note: This is a simulation. Always consult a financial advisor before trading.")
else:
    st.error("Could not fetch data from CSE. Please try again later.")
