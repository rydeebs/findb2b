import os
import streamlit as st
import pandas as pd
import requests

# Replace with your actual Google API Key and Custom Search Engine ID
GOOGLE_API_KEY = "AIzaSyAQUyfWVnYELkXvkPo0-owYGyO2K-jlqq0"
GOOGLE_CSE_ID = "22906673011-tj162qmapsaj1u9iiqivllrugnm26q3d.apps.googleusercontent.com"

def search_google_shopping(brand_name, num_results=10):
    """
    Uses Google Custom Search API to get Google Shopping results for a product.
    """
    search_url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        "q": brand_name + " buy online",
        "cx": GOOGLE_CSE_ID,
        "key": GOOGLE_API_KEY,
        "num": num_results
    }

    response = requests.get(search_url, params=params)
    
    if response.status_code != 200:
        st.error(f"Google Search API Error: {response.status_code}")
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

def find_retailers_comprehensive(brand_name):
    all_retailers = search_google_shopping(brand_name)
    
    return all_retailers

# Streamlit UI
st.title("Brand Retailer Finder")

brand_name = st.text_input("Enter Brand Name:")

if st.button("Find Retailers"):
    results = find_retailers_comprehensive(brand_name)
    
    if results:
        df = pd.DataFrame(results)
        st.dataframe(df)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Results", csv, "retailers.csv", "text/csv")
    else:
        st.write("No retailers found. Try a different search term.")
