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
    Directly scrapes Google Shopping results to find retailers carrying the brand's products.
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
    search_url = f"https://www.google.com/search?q={encoded_query}&tbm=shop"
    
    # Set user agent to avoid being blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }
    
    try:
        # Make the request to Google Shopping
        response = requests.get(search_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            st.error(f"Google Shopping search failed: {response.status_code}")
            return []
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all shopping items
        retailers = []
        seen_domains = set()
        
        # Look for shopping items with merchant information
        # Google Shopping typically has elements with merchants mentioned
        shopping_items = soup.find_all(['div', 'span'], class_=re.compile('(sh-|merchant|seller)'))
        
        for item in shopping_items:
            # Try to find merchant name
            merchant_text = item.text.strip()
            
            # Check if this element contains merchant information
            if not merchant_text or len(merchant_text) < 3:
                continue
                
            # Look for links near this element
            link_element = None
            parent = item.parent
            
            # Look up to 3 levels up for links
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
                    
            url = link_element['href']
            
            # Handle Google redirect URLs
            if 'google.com/url' in url or 'google.com/aclk' in url:
                # Extract the actual destination URL
                if 'url=' in url:
                    match = re.search(r'url=([^&]+)', url)
                    if match:
                        url = match.group(1)
                elif 'adurl=' in url:
                    match = re.search(r'adurl=([^&]+)', url)
                    if match:
                        url = match.group(1)
                        
            # Skip if not a proper URL
            if not url or not url.startswith(('http://', 'https://')):
                continue
                
            # Extract domain
            domain = extract_domain(url)
            
            # Skip if it's the brand's own site
            if brand_domain and (domain == brand_domain or brand_domain in domain):
                continue
                
            # Skip social media and common non-retailer sites
            skip_domains = ['google.', 'facebook.', 'instagram.', 'pinterest.', 'twitter.', 
                           'linkedin.', 'tiktok.', 'youtube.', 'reddit.']
            if any(skip in domain.lower() for skip in skip_domains):
                continue
                
            # Skip if we've already seen this domain
            if domain in seen_domains:
                continue
                
            # Add to seen domains
            seen_domains.add(domain)
            
            # Get retailer name - either from the merchant text or domain
            retailer_name = merchant_text if merchant_text else domain.split('.')[0].capitalize()
            
            # Extract price if available
            price = "N/A"
            price_elem = item.find(text=re.compile(r'\$[\d,]+\.\d{2}'))
            if price_elem:
                price = price_elem
                
            # Check if this appears to be a product page
            product_title = "Product page"
            title_elem = link_element.get_text() if link_element else None
            if title_elem:
                product_title = title_elem
                
            retailers.append({
                "Retailer": retailer_name,
                "Domain": domain,
                "Link": url,
                "Product": product_title,
                "Price": price,
                "Source": "Google Shopping"
            })
            
        # If we didn't find retailers through the specific elements, try a more general approach
        if not retailers:
            # Look for all links in the shopping results
            for link in soup.find_all("a", href=True):
                url = link["href"]
                
                # Skip internal Google links
                if not ('url=' in url or 'google.com/aclk' in url):
                    continue
                    
                # Extract the actual URL
                if 'url=' in url:
                    match = re.search(r'url=([^&]+)', url)
                    if match:
                        url = match.group(1)
                elif 'adurl=' in url:
                    match = re.search(r'adurl=([^&]+)', url)
                    if match:
                        url = match.group(1)
                
                # Skip if not a proper URL
                if not url.startswith(('http://', 'https://')):
                    continue
                    
                domain = extract_domain(url)
                
                # Skip if it's the brand's own site
                if brand_domain and (domain == brand_domain or brand_domain in domain):
                    continue
                    
                # Skip if already found or if it's the brand domain
                if domain in seen_domains:
                    continue
                    
                # Skip social media and common non-retailer sites
                skip_domains = ['google.', 'facebook.', 'instagram.', 'pinterest.', 'twitter.', 
                               'linkedin.', 'tiktok.', 'youtube.', 'reddit.']
                if any(skip in domain.lower() for skip in skip_domains):
                    continue
                
                seen_domains.add(domain)
                
                retailers.append({
                    "Retailer": domain.split('.')[0].capitalize(),
                    "Domain": domain,
                    "Link": url,
                    "Product": link.text.strip() if link.text.strip() else "Product page",
                    "Price": "N/A",
                    "Source": "Google Shopping"
                })
                
        return retailers
        
    except Exception as e:
        st.error(f"Error scraping Google Shopping: {str(e)}")
        return []

def find_retailers_comprehensive(brand_name, brand_url, industry, filters):
    """Main function to find retailers through multiple Google Shopping searches"""
    st.info(f"Searching for retailers that carry {brand_name} on Google Shopping...")
    
    # Try multiple search variations to maximize results
    all_retailers = []
    seen_domains = set()
    
    # First search with original parameters
    retailers = search_google_shopping(brand_name, brand_url, industry, filters)
    
    for retailer in retailers:
        domain = retailer["Domain"]
        if domain not in seen_domains:
            all_retailers.append(retailer)
            seen_domains.add(domain)
    
    # If we don't have enough results, try variations
    if len(all_retailers) < 5:
        # Try with just brand name
        retailers = search_google_shopping(brand_name, brand_url, None, None)
        for retailer in retailers:
            domain = retailer["Domain"]
            if domain not in seen_domains:
                all_retailers.append(retailer)
                seen_domains.add(domain)
    
    # Try with a "buy" keyword if still not enough results
    if len(all_retailers) < 5:
        buy_filters = ["buy online"] if not filters else filters + ["buy online"]
        retailers = search_google_shopping(brand_name, brand_url, industry, buy_filters)
        for retailer in retailers:
            domain = retailer["Domain"]
            if domain not in seen_domains:
                all_retailers.append(retailer)
                seen_domains.add(domain)
    
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
