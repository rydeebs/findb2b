import os
import streamlit as st
import pandas as pd
import requests

# Load API key from environment variables (GitHub Secrets)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
    st.error("API keys not found! Ensure they are set as environment variables.")

def search_google_shopping(brand_name, brand_url, industry, filters, num_results=10):
    """
    Uses Google Custom Search API to get Google Shopping results for a product.
    Allows additional filtering based on user inputs such as brand URL and industry.
    """
    query_parts = [brand_name, industry, brand_url]
    query_parts.extend(filters)
    query = " ".join([part for part in query_parts if part])  # Remove empty values
    
    search_url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        "q": query,
        "cx": GOOGLE_CSE_ID,
        "key": GOOGLE_API_KEY,
        "num": num_results
    }

    response = requests.get(search_url, params=params)
    
    if response.status_code != 200:
        st.error(f"Google Search API Error {response.status_code}: {response.text}")
        return []
    
    data = response.json()
    
    retailers = []
    for item in data.get("items", []):
        retailers.append({
            "Title": item.get("title"),
            "Link": item.get("link"),
            "Snippet": item.get("snippet")
        })
    
    return retailers

def find_retailers_comprehensive(brand_name, brand_url, industry, filters):
    all_retailers = search_google_shopping(brand_name, brand_url, industry, filters)
    
    return all_retailers

# Streamlit UI
st.title("Brand Retailer Finder")

brand_name = st.text_input("Enter Brand Name:")
brand_url = st.text_input("Enter Brand Website URL:")
industry = st.text_input("Enter Industry:")
filters = st.text_input("Enter Additional Filters (e.g., 'best price', 'fast shipping', 'US only'):")
filters_list = filters.split(',') if filters else []

if st.button("Find Retailers"):
    results = find_retailers_comprehensive(brand_name, brand_url, industry, filters_list)
    
    if results:
        df = pd.DataFrame(results)
        st.dataframe(df)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Results", csv, "retailers.csv", "text/csv")
    else:
        st.write("No retailers found. Try a different search term.")
