import os
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import re
from urllib.parse import urlparse, quote_plus

# Load API keys from a separate .env file
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

def extract_domain(url):
    """Extract and normalize domain from URL"""
    if not url:
        return ""
    try:
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        return domain
    except:
        return url

def search_google_shopping_api(brand_name, brand_url=None, industry=None, filters=None, num_results=20):
    """
    Uses Google Custom Search API to get Google Shopping results for a brand.
    Specifically targets shopping results and extracts retailer information.
    """
    # Clean up brand URL if provided
    brand_domain = extract_domain(brand_url) if brand_url else None
    
    # Build base query focusing on shopping/retailer keywords
    query = f"{brand_name}"
    
    # Add shopping-specific parameters
    query += " buy OR purchase OR shop OR store OR retailer OR "where to buy""
    
    # Add industry if provided
    if industry:
        query += f" {industry}"
    
    # Add filters if provided
    if filters:
        query += " " + " ".join(filters)
    
    # Set up API request
    search_url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        "q": query,
        "cx": GOOGLE_CSE_ID,
        "key": GOOGLE_API_KEY,
        "num": min(num_results, 10),  # First batch of results
        "searchType": "shopping"  # Specifically target shopping results
    }

    retailers = []
    seen_domains = set()
    
    try:
        # Make first API request
        response = requests.get(search_url, params=params)
        
        if response.status_code != 200:
            st.error(f"Google Search API Error: {response.status_code}")
            if 'error' in response.json():
                st.error(f"Error details: {response.json()['error']['message']}")
            return []
        
        data = response.json()
        retailers.extend(process_search_results(data, brand_domain, seen_domains))
        
        # If we have more results available and need them, make a second request
        if 'nextPage' in data.get('queries', {}) and len(retailers) < num_results:
            params['start'] = data['queries']['nextPage'][0]['startIndex']
            response = requests.get(search_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                retailers.extend(process_search_results(data, brand_domain, seen_domains))
        
        # If we still don't have enough retailers, try a more specific shopping search
        if len(retailers) < 5:
            # Modify the query to specifically target product listings
            product_query = f"{brand_name} product"
            params['q'] = product_query
            params.pop('start', None)  # Remove start parameter for a fresh search
            
            response = requests.get(search_url, params=params)
            if response.status_code == 200:
                data = response.json()
                retailers.extend(process_search_results(data, brand_domain, seen_domains))
    
    except Exception as e:
        st.error(f"Error searching for retailers: {str(e)}")
    
    # If API approach didn't yield enough results, fall back to manual extraction
    if len(retailers) < 3:
        fallback_retailers = search_google_shopping_fallback(brand_name, brand_domain)
        for retailer in fallback_retailers:
            domain = extract_domain(retailer["Link"])
            if domain and domain not in seen_domains:
                retailers.append(retailer)
                seen_domains.add(domain)
    
    return retailers

def process_search_results(data, brand_domain, seen_domains):
    """Process search results and extract retailer information"""
    retailers = []
    
    # Skip if no items in results
    if 'items' not in data:
        return retailers
    
    for item in data.get("items", []):
        link = item.get("link", "")
        if not link:
            continue
            
        # Extract domain
        domain = extract_domain(link)
        
        # Skip if it's the brand's own website
        if brand_domain and (domain == brand_domain or brand_domain in domain):
            continue
            
        # Skip social media and common non-retailer sites
        skip_domains = ['facebook.com', 'instagram.com', 'pinterest.com', 'twitter.com', 
                       'linkedin.com', 'tiktok.com', 'youtube.com', 'reddit.com',
                       'amazon.com/brands/', 'wikipedia.org', 'google.com']
        if any(domain.endswith(skip) or skip in domain for skip in skip_domains):
            continue
        
        # Skip if we've already seen this domain
        if domain in seen_domains:
            continue
        
        seen_domains.add(domain)
        
        # Extract retailer name from domain
        retailer_name = domain.split('.')[0].capitalize()
        
        # Determine if this is a product page
        is_product_page = False
        product_indicators = ['/p/', '/product/', '/item/', '/shop/', '/buy/', '/pd/']
        if any(indicator in link for indicator in product_indicators):
            is_product_page = True
            
        # Extract price if available
        price = "N/A"
        snippet = item.get("snippet", "")
        price_match = re.search(r'\$\d+(?:\.\d{2})?', snippet)
        if price_match:
            price = price_match.group(0)
            
        confidence = "High" if is_product_page else "Medium"
        
        retailers.append({
            "Retailer": retailer_name,
            "Domain": domain,
            "Link": link,
            "Product": item.get("title", "Product page"),
            "Price": price,
            "Confidence": confidence,
            "Source": "Google API"
        })
    
    return retailers

def search_google_shopping_fallback(brand_name, brand_domain=None):
    """
    Fallback method to directly search Google Shopping when the API doesn't return sufficient results.
    """
    search_url = f"https://www.google.com/search?q={quote_plus(brand_name)}&tbm=shop"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    try:
        response = requests.get(search_url, headers=headers)
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        retailers = []
        
        # Look for merchant information in shopping results
        merchant_elements = soup.find_all(['div', 'span'], class_=re.compile('(merchant|seller|shop)'))
        
        for element in merchant_elements:
            # Try to find a link near the merchant element
            parent = element.parent
            link_element = None
            
            # Look up to 3 levels up
            for _ in range(3):
                if parent:
                    link_element = parent.find('a', href=True)
                    if link_element:
                        break
                    parent = parent.parent
                else:
                    break
            
            if not link_element:
                continue
                
            link = link_element.get('href', '')
            
            # Extract domain
            domain = extract_domain(link)
            
            # Skip if it's the brand's own site
            if brand_domain and (domain == brand_domain or brand_domain in domain):
                continue
            
            # Skip common non-retailer sites
            skip_domains = ['google.', 'facebook.', 'instagram.', 'pinterest.', 'twitter.']
            if any(skip in domain.lower() for skip in skip_domains):
                continue
            
            # Get merchant name
            merchant_name = element.text.strip()
            if not merchant_name or len(merchant_name) < 2:
                merchant_name = domain.split('.')[0].capitalize()
            
            retailers.append({
                "Retailer": merchant_name,
                "Domain": domain,
                "Link": link,
                "Product": "Found via Google Shopping",
                "Price": "N/A",
                "Confidence": "Medium",
                "Source": "Direct Scraping"
            })
        
        # If we didn't find merchants through the specific elements, try extracting from all links
        if not retailers:
            seen_domains = set()
            for link in soup.find_all("a", href=True):
                url = link["href"]
                
                # Extract retailer URL from Google redirect
                if 'url=' in url:
                    match = re.search(r'url=([^&]+)', url)
                    if match:
                        url = match.group(1)
                
                # Skip non-http URLs
                if not url.startswith(('http://', 'https://')):
                    continue
                    
                domain = extract_domain(url)
                
                # Skip if already found or if it's the brand domain
                if domain in seen_domains or (brand_domain and domain == brand_domain):
                    continue
                    
                # Skip common non-retailer domains
                skip_domains = ['google.', 'facebook.', 'instagram.', 'pinterest.', 'twitter.']
                if any(skip in domain.lower() for skip in skip_domains):
                    continue
                
                seen_domains.add(domain)
                
                retailers.append({
                    "Retailer": domain.split('.')[0].capitalize(),
                    "Domain": domain,
                    "Link": url,
                    "Product": link.text.strip() if link.text.strip() else "Product page",
                    "Price": "N/A",
                    "Confidence": "Low",
                    "Source": "Direct Scraping"
                })
        
        return retailers
        
    except Exception as e:
        st.error(f"Error in fallback search: {str(e)}")
        return []

def find_retailers_comprehensive(brand_name, brand_url, industry, filters):
    """Main function to find retailers through multiple methods"""
    st.info(f"Searching for retailers that carry {brand_name}...")
    
    # Start with Google Shopping API search
    retailers = search_google_shopping_api(brand_name, brand_url, industry, filters)
    
    # Sort by confidence level
    retailers = sorted(retailers, key=lambda x: 
                      {"High": 3, "Medium": 2, "Low": 1}.get(x.get("Confidence", "Low"), 0), 
                      reverse=True)
    
    return retailers

# Streamlit UI
st.title("Brand Retailer Finder")
st.write("Find retailers that carry a specific brand's products")

brand_name = st.text_input("Enter Brand Name:")
brand_url = st.text_input("Enter Brand Website URL (optional):")
industry = st.text_input("Enter Industry (optional):")
filters = st.text_input("Enter Additional Filters (comma-separated, optional):")
filters_list = [f.strip() for f in filters.split(',')] if filters else []

if st.button("Find Retailers"):
    if not brand_name:
        st.error("Please enter a brand name to search.")
    else:
        with st.spinner("Searching for retailers..."):
            results = find_retailers_comprehensive(brand_name, brand_url, industry, filters_list)
        
        if results:
            st.success(f"Found {len(results)} retailers that carry {brand_name}")
            
            # Create DataFrame
            df = pd.DataFrame(results)
            
            # Display results
            st.dataframe(df)
            
            # Download option
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Results as CSV", csv, f"{brand_name}_retailers.csv", "text/csv")
        else:
            st.warning("No retailers found. Try a different search term or check the brand name.")

# Display information about the app
with st.expander("About this app"):
    st.write("""
    This app helps you find retailers that carry a specific brand's products. 
    It uses Google's search APIs to identify online retailers that sell the brand.
    
    **Tips for best results:**
    - Enter the exact brand name
    - If you know the brand's website, enter it to exclude the brand's own site from results
    - Specify the industry to get more relevant results (e.g., "cosmetics", "electronics")
    - Use filters to narrow down results (e.g., "usa", "official retailer")
    """)
