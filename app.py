import os
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import re
from urllib.parse import urlparse, quote_plus, unquote
import time
import random

# Load API keys from a separate .env file
load_dotenv()

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

def search_google_shopping(brand_name, brand_url=None, industry=None, filters=None):
    """
    Enhanced function to scrape Google Shopping results to find retailers carrying a brand.
    Uses multiple approaches to account for different Google Shopping HTML structures.
    """
    # Clean up brand URL if provided
    brand_domain = extract_domain(brand_url) if brand_url else None
    
    # Build search query
    query = brand_name
    
    # Add industry if provided
    if industry:
        query += f" {industry}"
    
    # Add filters if provided
    if filters:
        query += " " + " ".join(filters)
    
    # Encode the query
    encoded_query = quote_plus(query)
    
    # Direct Google Shopping URL
    search_url = f"https://www.google.com/search?q={encoded_query}&tbm=shop&num=100"
    
    # Use a realistic user agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "TE": "Trailers"
    }
    
    retailers = []
    seen_domains = set()
    
    try:
        # Make the request to Google Shopping
        st.info(f"Searching Google Shopping for: {query}")
        response = requests.get(search_url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            st.error(f"Google Shopping search failed: {response.status_code}")
            return []
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Debug: Save HTML for inspection
        # with open("google_shopping.html", "w", encoding="utf-8") as f:
        #     f.write(response.text)
        
        # APPROACH 1: Look for merchant elements using various class patterns
        merchant_classes = ['merchant', 'sh-dlr__list-result', 'sh-dlr__content', 'a5OGkf', 'E5ocAb', 
                           'aULzUe', 'kPMwsc', 'sh-np__click-target', 'BXIkFb']
        
        for class_name in merchant_classes:
            merchant_elements = soup.find_all(class_=re.compile(class_name))
            
            for element in merchant_elements:
                links = element.find_all('a', href=True)
                
                for link in links:
                    url = link['href']
                    
                    # Extract actual URL from Google redirect
                    if 'google.com/url' in url or 'google.com/aclk' in url:
                        if 'url=' in url:
                            match = re.search(r'url=([^&]+)', url)
                            if match:
                                url = unquote(match.group(1))
                        elif 'adurl=' in url:
                            match = re.search(r'adurl=([^&]+)', url)
                            if match:
                                url = unquote(match.group(1))
                    
                    # Skip if not a proper URL
                    if not url.startswith(('http://', 'https://')):
                        continue
                    
                    domain = extract_domain(url)
                    
                    # Skip if it's the brand's own site
                    if brand_domain and (domain == brand_domain or brand_domain in domain):
                        continue
                    
                    # Skip common non-retailer sites
                    skip_domains = ['google.', 'facebook.', 'instagram.', 'pinterest.', 'twitter.', 
                                   'linkedin.', 'tiktok.', 'youtube.', 'reddit.']
                    if any(skip in domain.lower() for skip in skip_domains):
                        continue
                    
                    # Skip if already found
                    if domain in seen_domains:
                        continue
                    
                    seen_domains.add(domain)
                    
                    # Try to find merchant name
                    merchant_name = None
                    merchant_elem = element.find(text=re.compile(r'from|by|sold by|at', re.IGNORECASE))
                    
                    if merchant_elem:
                        text = merchant_elem.strip()
                        match = re.search(r'(?:from|by|sold by|at)\s+([A-Za-z0-9\s\.\-&\']+)', text, re.IGNORECASE)
                        if match:
                            merchant_name = match.group(1).strip()
                    
                    if not merchant_name:
                        # Extract from domain
                        merchant_name = domain.split('.')[0].capitalize()
                    
                    # Extract price if available
                    price = "N/A"
                    price_pattern = re.compile(r'\$[\d,]+\.\d{2}')
                    price_match = element.find(text=price_pattern)
                    if price_match:
                        match = price_pattern.search(price_match)
                        if match:
                            price = match.group(0)
                    
                    # Get product title
                    product_title = "Product page"
                    title_elem = element.find(['h3', 'h4'])
                    if title_elem:
                        product_title = title_elem.text.strip()
                    
                    retailers.append({
                        "Retailer": merchant_name,
                        "Domain": domain,
                        "Link": url,
                        "Product": product_title,
                        "Price": price,
                        "Source": "Google Shopping"
                    })
        
        # APPROACH 2: Find all external links in the page
        if len(retailers) < 2:
            for link in soup.find_all('a', href=True):
                url = link['href']
                
                # Only look at Google Shopping redirects
                if not ('url=' in url or 'google.com/aclk' in url):
                    continue
                
                # Extract actual URL
                if 'url=' in url:
                    match = re.search(r'url=([^&]+)', url)
                    if match:
                        url = unquote(match.group(1))
                elif 'adurl=' in url:
                    match = re.search(r'adurl=([^&]+)', url)
                    if match:
                        url = unquote(match.group(1))
                
                # Skip if not a proper URL
                if not url.startswith(('http://', 'https://')):
                    continue
                
                domain = extract_domain(url)
                
                # Skip if it's the brand's own site
                if brand_domain and (domain == brand_domain or brand_domain in domain):
                    continue
                
                # Skip if already found
                if domain in seen_domains:
                    continue
                
                # Skip common non-retailer sites
                skip_domains = ['google.', 'facebook.', 'instagram.', 'pinterest.', 'twitter.', 
                               'linkedin.', 'tiktok.', 'youtube.', 'reddit.', 'wikipedia.']
                if any(skip in domain.lower() for skip in skip_domains):
                    continue
                
                seen_domains.add(domain)
                
                # Find the nearest text that might be the title
                parent = link.parent
                product_title = "Product page"
                
                # Look up to 2 levels to find title-like text
                for _ in range(2):
                    if parent:
                        title_elem = parent.find(['h3', 'h4', 'div'], class_=re.compile('title|name|product', re.IGNORECASE))
                        if title_elem:
                            product_title = title_elem.text.strip()
                            break
                        parent = parent.parent
                    else:
                        break
                
                # Use link text if no title found
                if product_title == "Product page" and link.text.strip():
                    product_title = link.text.strip()
                
                retailers.append({
                    "Retailer": domain.split('.')[0].capitalize(),
                    "Domain": domain,
                    "Link": url,
                    "Product": product_title,
                    "Price": "N/A",
                    "Source": "Google Shopping"
                })
        
        # APPROACH 3: Try a different shopping URL format
        if len(retailers) < 3:
            # Use the shopping tab format
            alt_url = f"https://www.google.com/search?q={encoded_query}+buy+online&tbm=shop"
            
            response = requests.get(alt_url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Look for all links with redirects
                for link in soup.find_all('a', href=True):
                    url = link['href']
                    
                    # Only look at Google Shopping redirects
                    if not ('url=' in url or 'google.com/aclk' in url):
                        continue
                    
                    # Extract actual URL
                    if 'url=' in url:
                        match = re.search(r'url=([^&]+)', url)
                        if match:
                            url = unquote(match.group(1))
                    elif 'adurl=' in url:
                        match = re.search(r'adurl=([^&]+)', url)
                        if match:
                            url = unquote(match.group(1))
                    
                    # Skip if not a proper URL
                    if not url.startswith(('http://', 'https://')):
                        continue
                    
                    domain = extract_domain(url)
                    
                    # Skip if it's the brand's own site
                    if brand_domain and (domain == brand_domain or brand_domain in domain):
                        continue
                    
                    # Skip if already found
                    if domain in seen_domains:
                        continue
                    
                    # Skip common non-retailer sites
                    skip_domains = ['google.', 'facebook.', 'instagram.', 'pinterest.', 'twitter.', 
                                   'linkedin.', 'tiktok.', 'youtube.', 'reddit.', 'wikipedia.']
                    if any(skip in domain.lower() for skip in skip_domains):
                        continue
                    
                    seen_domains.add(domain)
                    
                    retailers.append({
                        "Retailer": domain.split('.')[0].capitalize(),
                        "Domain": domain,
                        "Link": url,
                        "Product": link.text.strip() if link.text.strip() else "Product page",
                        "Price": "N/A",
                        "Source": "Google Shopping (Alternative)"
                    })
        
        return retailers
    
    except Exception as e:
        st.error(f"Error scraping Google Shopping: {str(e)}")
        return []

def find_retailers_comprehensive(brand_name, brand_url, industry, filters):
    """Main function to find retailers through multiple Google Shopping searches"""
    all_retailers = []
    seen_domains = set()
    
    # First search with original parameters
    retailers = search_google_shopping(brand_name, brand_url, industry, filters)
    
    for retailer in retailers:
        domain = retailer["Domain"]
        if domain not in seen_domains:
            all_retailers.append(retailer)
            seen_domains.add(domain)
    
    # If we don't have enough results, try with a specific "buy" keyword
    if len(all_retailers) < 5:
        st.info("Trying alternative search to find more retailers...")
        buy_search = f"{brand_name} buy"
        retailers = search_google_shopping(buy_search, brand_url, industry, filters)
        
        for retailer in retailers:
            domain = retailer["Domain"]
            if domain not in seen_domains:
                all_retailers.append(retailer)
                seen_domains.add(domain)
    
    # Try with a "where to buy" keyword if still not enough results
    if len(all_retailers) < 5:
        st.info("Searching for 'where to buy' information...")
        where_to_buy_search = f"{brand_name} where to buy"
        retailers = search_google_shopping(where_to_buy_search, brand_url, industry, filters)
        
        for retailer in retailers:
            domain = retailer["Domain"]
            if domain not in seen_domains:
                all_retailers.append(retailer)
                seen_domains.add(domain)
    
    # Add a direct check for major retailers if specific keywords are found
    if "cosmetics" in (industry or "").lower() or "makeup" in (industry or "").lower() or "beauty" in (industry or "").lower():
        beauty_retailers = ["target.com", "qvc.com", "amazon.com", "ulta.com", "sephora.com"]
        
        for retailer in beauty_retailers:
            if retailer not in seen_domains:
                specific_search = f"{brand_name} site:{retailer}"
                search_url = f"https://www.google.com/search?q={quote_plus(specific_search)}"
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                
                try:
                    response = requests.get(search_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200 and "did not match any documents" not in response.text:
                        # Results found, this retailer likely carries the brand
                        all_retailers.append({
                            "Retailer": retailer.split('.')[0].capitalize(),
                            "Domain": retailer,
                            "Link": f"https://{retailer}/search?q={quote_plus(brand_name)}",
                            "Product": f"{brand_name} products",
                            "Price": "N/A",
                            "Source": "Direct Retailer Check"
                        })
                        seen_domains.add(retailer)
                except:
                    continue
    
    return all_retailers

# Streamlit UI
st.title("Brand Retailer Finder")
st.write("Find retailers that carry a specific brand's products on Google Shopping")

brand_name = st.text_input("Enter Brand Name:")
brand_url = st.text_input("Enter Brand Website URL (optional):")
industry = st.text_input("Enter Industry (optional):")
filters = st.text_input("Enter Additional Filters (comma-separated, optional):")
filters_list = [f.strip() for f in filters.split(',')] if filters else []

if st.button("Find Retailers"):
    if not brand_name:
        st.error("Please enter a brand name to search.")
    else:
        with st.spinner(f"Searching Google Shopping for retailers that carry {brand_name}..."):
            results = find_retailers_comprehensive(brand_name, brand_url, industry, filters_list)
        
        if results:
            st.success(f"Found {len(results)} retailers carrying {brand_name} on Google Shopping")
            
            # Create DataFrame
            df = pd.DataFrame(results)
            
            # Display results
            st.dataframe(df)
            
            # Download option
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Results as CSV", csv, f"{brand_name}_retailers.csv", "text/csv")
        else:
            st.warning("No retailers found on Google Shopping. Try a different search term or check the brand name.")
            
            # Suggest direct checks
            st.info("You can manually check these common retailers:")
            common_retailers = {
                "Amazon": f"https://www.amazon.com/s?k={quote_plus(brand_name)}",
                "Target": f"https://www.target.com/s?searchTerm={quote_plus(brand_name)}",
                "Walmart": f"https://www.walmart.com/search?q={quote_plus(brand_name)}",
                "QVC": f"https://www.qvc.com/content/search.html?qq={quote_plus(brand_name)}"
            }
            
            for retailer, url in common_retailers.items():
                st.markdown(f"- [{retailer}]({url})")

# Display information about the app
with st.expander("About this app"):
    st.write("""
    This app helps you find retailers that carry a specific brand's products by scraping Google Shopping results.
    
    **Tips for best results:**
    - Enter the exact brand name
    - If you know the brand's website, enter it to exclude the brand's own site from results
    - Specify the industry to get more relevant results (e.g., "cosmetics", "electronics")
    - Use filters to narrow down results (e.g., "usa", "official retailer")
    """)
