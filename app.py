import os
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load API keys from a separate .env file
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

def search_google_shopping_api(brand_name, brand_url, industry, filters, num_results=20):
    """
    Uses Google Shopping directly to find retailers carrying the brand's products.
    """
    search_url = f"https://www.google.com/shopping?udm=28&q={brand_name}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    response = requests.get(search_url, headers=headers)
    
    if response.status_code != 200:
        st.error(f"Google Shopping search failed: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    retailers = []
    seen_domains = set()
    
    for link in soup.find_all("a", href=True):
        url = link["href"]
        if not url.startswith("http"):
            continue
        domain = url.split("/")[2]
        
        if brand_url and brand_url in url:
            continue
        
        if domain in seen_domains:
            continue
        seen_domains.add(domain)
        
        retailers.append({
            "Title": link.text.strip() or "Retailer",
            "Link": url,
            "Snippet": "Found via Google Shopping"
        })
    
    return retailers
    """
    Uses Google Custom Search API to get Google Shopping results for a product.
    Allows additional filtering based on user inputs such as brand URL and industry.
    """
    query = f"{brand_name} {industry} {brand_url} buy online OR purchase OR retailer OR store OR shop OR available at OR official distributor OR sold at OR where to buy OR online store OR wholesale"
    if filters:
        query += " " + " ".join(filters)
    
    search_url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        "q": query,
        "cx": GOOGLE_CSE_ID,
        "key": GOOGLE_API_KEY,
        "num": min(num_results, 20)
    }

    response = requests.get(search_url, params=params)
    
    if response.status_code != 200:
        st.error(f"Google Search API Error: {response.status_code}")
        return []
    
    data = response.json()
    
    retailers = []
    seen_domains = set()
    for item in data.get("items", []):
        # Skip results that match the brand's own website
        if brand_url and brand_url in item.get("link", ""):
            continue
        # Skip social media sites
        social_sites = ['facebook.com', 'instagram.com', 'pinterest.com', 'twitter.com', 'linkedin.com', 'tiktok.com']
        if any(site in item.get("link", "") for site in social_sites):
            continue
        # Skip results that match the brand's own website
        if brand_url and brand_url in item.get("link", ""):
            continue
        domain = item.get("link", "").split("/")[2]  # Extract domain name
        if domain in seen_domains:
            continue  # Skip duplicate retailers
        seen_domains.add(domain)
        retailers.append({
            "Title": item.get("title"),
            "Link": item.get("link"),
            "Snippet": item.get("snippet")
        })
    
    return retailers

def find_retailers_comprehensive(brand_name, brand_url, industry, filters):
    all_retailers = search_google_shopping_api(brand_name, brand_url, industry, filters)
    
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
