import time
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote_plus, urlparse
import concurrent.futures
import time
import io
import random
import datetime
import json
import traceback

# Set up page configuration
st.set_page_config(
    page_title="B2B Retailer Finder",
    page_icon="🔍",
    layout="wide"
)

# Add title and description
st.title("B2B Retailer Finder")
st.markdown("Discover all retailers that carry specific brands")

# Initialize session state variables
if 'results_df' not in st.session_state:
    st.session_state['results_df'] = None

if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []

if 'product_skus' not in st.session_state:
    st.session_state['product_skus'] = None

# Define major retailers list to check specifically
MAJOR_RETAILERS = [
    {"name": "Target", "domain": "target.com", "search_pattern": "{brand}+site:target.com"},
    {"name": "Walmart", "domain": "walmart.com", "search_pattern": "{brand}+site:walmart.com"},
    {"name": "Amazon", "domain": "amazon.com", "search_pattern": "{brand}+site:amazon.com"},
    {"name": "Ulta Beauty", "domain": "ulta.com", "search_pattern": "{brand}+site:ulta.com"},
    {"name": "Sephora", "domain": "sephora.com", "search_pattern": "{brand}+site:sephora.com"},
    {"name": "CVS", "domain": "cvs.com", "search_pattern": "{brand}+site:cvs.com"},
    {"name": "Walgreens", "domain": "walgreens.com", "search_pattern": "{brand}+site:walgreens.com"},
    {"name": "Costco", "domain": "costco.com", "search_pattern": "{brand}+site:costco.com"},
    {"name": "Best Buy", "domain": "bestbuy.com", "search_pattern": "{brand}+site:bestbuy.com"},
    {"name": "Home Depot", "domain": "homedepot.com", "search_pattern": "{brand}+site:homedepot.com"}
]

# Function to extract domain from URL
def extract_domain(url):
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

# Extract brand name from domain if URL is provided
def extract_brand_from_url(url):
    if not url:
        return ""
    
    domain = extract_domain(url)
    
    # Remove common TLDs
    tlds = ['.com', '.co', '.org', '.net', '.io', '.us', '.shop', '.store']
    for tld in tlds:
        if domain.endswith(tld):
            domain = domain[:-len(tld)]
    
    # Extract brand name from domain
    parts = domain.split('.')
    brand = parts[0]
    
    # Remove common prefixes
    prefixes = ['try', 'get', 'buy', 'shop', 'the', 'my', 'our', 'team']
    for prefix in prefixes:
        if brand.startswith(prefix) and len(brand) > len(prefix) + 2:
            brand = brand[len(prefix):]
    
    # Clean up and capitalize
    brand = brand.strip().capitalize()
    
    return brand

# Function to directly extract Google Shopping results with maximum compatibility
def extract_google_shopping_direct(brand_name):
    """
    Enhanced Google Shopping extraction designed to capture retailers
    for all types of brands regardless of product category.
    
    Args:
        brand_name: The brand to search for
    
    Returns:
        List of retailer dictionaries
    """
    retailers = []
    found_domains = set()
    
    # Prepare generalized search variations
    search_variations = [
        f"{brand_name}",                    # Exact brand name
        f"{brand_name} buy",                # Brand + buy
        f"{brand_name} product",            # Brand + product
        f"\"{brand_name}\"",                # Exact match with quotes
        f"{brand_name} retailer",           # Brand + retailer
        f"{brand_name} where to buy"        # Brand + where to buy
    ]
    
    # Different user agents to rotate
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
        'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
    ]
    
    st.info(f"Performing enhanced Google Shopping search for: {brand_name}")
    progress_text = st.empty()
    
    # Try multiple search approaches to maximize coverage
    search_engines = [
        # Google Shopping standard view
        lambda query: f"https://www.google.com/search?q={query}&tbm=shop&num=30",
        # Google Shopping mobile view (sometimes shows different results)
        lambda query: f"https://www.google.com/search?q={query}&tbm=shop&num=30&source=lnms",
        # Google search with site:amazon restriction (Amazon is a major retailer)
        lambda query: f"https://www.google.com/search?q={query}+site:amazon.com&num=20",
        # Google search for other major retailers
        lambda query: f"https://www.google.com/search?q={query}+site:walmart.com+OR+site:target.com+OR+site:bestbuy.com&num=20"
    ]
    
    # Try each search variation with each search engine
    for search_idx, search_term in enumerate(search_variations):
        progress_text.text(f"Trying search variation {search_idx+1}/{len(search_variations)}: '{search_term}'")
        
        # Encode the search term
        query = quote_plus(search_term)
        
        for engine_idx, search_engine in enumerate(search_engines):
            search_url = search_engine(query)
            try:
                # Use a different user agent for each request
                user_agent = user_agents[(search_idx + engine_idx) % len(user_agents)]
                
                # Set up request headers
                headers = {
                    'User-Agent': user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.google.com/',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                # Send request with longer timeout
                response = requests.get(
                    search_url, 
                    headers=headers, 
                    timeout=20
                )
                
                if response.status_code != 200:
                    continue
                
                # Check if we got a "no results" page
                if "did not match any shopping results" in response.text:
                    continue
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract all links from the page
                all_links = soup.find_all('a', href=True)
                
                # Look for retailer links in the shopping results
                for link in all_links:
                    href = link['href']
                    
                    # Skip Google internal links and pagination links
                    if not ('url=' in href or '/url?q=' in href or '/aclk?' in href):
                        continue
                        
                    # Extract the actual URL from Google's redirect
                    actual_url = None
                    
                    # Try different URL patterns
                    if 'url=' in href:
                        url_match = re.search(r'url=([^&]+)', href)
                        if url_match:
                            actual_url = url_match.group(1)
                    elif '/url?q=' in href:
                        url_match = re.search(r'/url\?q=([^&]+)', href)
                        if url_match:
                            actual_url = url_match.group(1)
                    elif '/aclk?' in href:
                        url_match = re.search(r'adurl=([^&]+)', href)
                        if url_match:
                            actual_url = url_match.group(1)
                    
                    # Skip if we couldn't extract a URL
                    if not actual_url:
                        continue
                        
                    # URL decode
                    try:
                        from urllib.parse import unquote
                        actual_url = unquote(actual_url)
                    except:
                        pass
                    
                    # Skip non-http URLs and Google's own URLs
                    if not actual_url.startswith(('http://', 'https://')) or 'google.com' in actual_url:
                        continue
                    
                    # Extract domain
                    domain = extract_domain(actual_url)
                    
                    # Skip if already found or if it's common non-retailer domains
                    skip_domains = ['google.', 'youtube.', 'facebook.', 'instagram.', 'twitter.', 
                                   'linkedin.', 'pinterest.', 'reddit.', 'tiktok.']
                    if domain in found_domains or any(skip in domain.lower() for skip in skip_domains):
                        continue
                    
                    # More robust approach to identifying brand's own domain
                    is_brand_domain = False
                    
                    # Split the brand name into words
                    brand_words = brand_name.lower().split()
                    
                    # 1. Check if the domain exactly matches the brand (without spaces)
                    if domain.split('.')[0].lower() == brand_name.lower().replace(" ", ""):
                        is_brand_domain = True
                        
                    # 2. Check for word matches but be smarter about it
                    # Only consider as brand domain if all these are true:
                    # - Contains a word from brand name that's ≥ 4 characters
                    # - The matching word isn't a common word
                    # - The matching portion is a significant part of the domain
                    elif len(brand_words) > 0:
                        common_words = {'the', 'and', 'buy', 'shop', 'get', 'our', 'your', 'this', 'that', 'with', 'from'}
                        for word in brand_words:
                            if (len(word) >= 4 and 
                                word.lower() not in common_words and 
                                word.lower() in domain.lower() and
                                len(word) >= len(domain.split('.')[0]) / 3):
                                is_brand_domain = True
                                break
                    
                    # Skip brand's own domain
                    if is_brand_domain:
                        continue
                    
                    found_domains.add(domain)
                    
                    # Try to get the title of the link
                    title = "Product page"
                    link_text = link.get_text().strip()
                    if link_text and len(link_text) > 5 and len(link_text) < 100:
                        title = link_text
                    
                    # Try to find price near this link
                    price = "N/A"
                    price_pattern = re.compile(r'\$\d+(?:\.\d{2})?')
                    
                    # Check the link itself for price
                    price_match = price_pattern.search(link_text)
                    if price_match:
                        price = price_match.group(0)
                    else:
                        # Check parent elements
                        parent = link.parent
                        for _ in range(3):  # Check up to 3 levels up
                            if parent:
                                parent_text = parent.get_text()
                                price_match = price_pattern.search(parent_text)
                                if price_match:
                                    price = price_match.group(0)
                                    break
                                parent = parent.parent
                            else:
                                break
                    
                    # Determine retailer name
                    retailer_name = domain.split('.')[0].capitalize()
                    
                    # Comprehensive retailer name mapping
                    common_retailers = {
                        # General retail
                        'amazon.com': 'Amazon',
                        'walmart.com': 'Walmart',
                        'target.com': 'Target',
                        'ebay.com': 'eBay',
                        'bestbuy.com': 'Best Buy',
                        'costco.com': 'Costco',
                        'samsclub.com': 'Sam\'s Club',
                        'homedepot.com': 'Home Depot',
                        'lowes.com': 'Lowe\'s',
                        'wayfair.com': 'Wayfair',
                        'etsy.com': 'Etsy',
                        'newegg.com': 'Newegg',
                        'macys.com': 'Macy\'s',
                        'nordstrom.com': 'Nordstrom',
                        'kohls.com': 'Kohl\'s',
                        'bedbathandbeyond.com': 'Bed Bath & Beyond',
                        'overstock.com': 'Overstock',
                        
                        # Beauty/Health
                        'ulta.com': 'Ulta Beauty',
                        'sephora.com': 'Sephora',
                        'cvs.com': 'CVS',
                        'walgreens.com': 'Walgreens',
                        'gnc.com': 'GNC',
                        'vitaminshoppe.com': 'Vitamin Shoppe',
                        
                        # Sports/Fitness
                        'dickssportinggoods.com': 'Dick\'s Sporting Goods',
                        'roguefitness.com': 'Rogue Fitness',
                        'bodybuilding.com': 'Bodybuilding.com',
                        'thefeed.com': 'The Feed',
                        'rei.com': 'REI',
                        'academy.com': 'Academy Sports',
                        
                        # Electronics
                        'bhphotovideo.com': 'B&H Photo',
                        'adorama.com': 'Adorama',
                        'microcenter.com': 'Micro Center',
                        'frys.com': 'Fry\'s Electronics',
                        
                        # Others
                        'chewy.com': 'Chewy',
                        'petco.com': 'Petco',
                        'petsmart.com': 'PetSmart',
                        'houzz.com': 'Houzz',
                        'officedepot.com': 'Office Depot',
                        'staples.com': 'Staples'
                    }
                    
                    if domain in common_retailers:
                        retailer_name = common_retailers[domain]
                    
                    # Add to retailers list
                    retailers.append({
                        'Brand': brand_name,
                        'Retailer': retailer_name,
                        'Domain': domain,
                        'Product': title,
                        'Price': price,
                        'Search_Source': f"Enhanced Google Search - Variation {search_idx+1}",
                        'Link': actual_url,
                        'Retailer_Confidence': "Very High"
                    })
                
                # If we found enough retailers, we can stop trying variations
                if len(retailers) >= 5 and search_idx > 0:
                    progress_text.text(f"Found {len(retailers)} retailers for {brand_name}. Moving to next steps...")
                    return retailers
                
                # Add slight delay between requests
                time.sleep(1.5)
                
            except Exception as e:
                # Log error and continue with next URL
                print(f"Error searching: {str(e)}")
                continue
    
    # If specific searches didn't yield enough results, try industry-specific 
    # retailer checks based on brand name pattern recognition
    if len(retailers) < 3:
        # Check for electronics pattern
        if any(word in brand_name.lower() for word in ['tech', 'electronics', 'audio', 'video', 'phone', 'computer', 'laptop', 'tablet']):
            tech_retailers = [
                {"name": "Best Buy", "domain": "bestbuy.com", "search_pattern": "{brand}+site:bestbuy.com"},
                {"name": "Newegg", "domain": "newegg.com", "search_pattern": "{brand}+site:newegg.com"},
                {"name": "B&H Photo", "domain": "bhphotovideo.com", "search_pattern": "{brand}+site:bhphotovideo.com"},
                {"name": "Micro Center", "domain": "microcenter.com", "search_pattern": "{brand}+site:microcenter.com"}
            ]
            for retailer in tech_retailers:
                if retailer["domain"] in found_domains:
                    continue
                try:
                    direct_result = check_specific_retailer(brand_name, retailer)
                    if direct_result:
                        retailers.append(direct_result)
                        found_domains.add(retailer["domain"])
                except:
                    continue
        
        # Check for beauty pattern
        elif any(word in brand_name.lower() for word in ['beauty', 'cosmetic', 'makeup', 'skin', 'hair', 'fragrance']):
            beauty_retailers = [
                {"name": "Sephora", "domain": "sephora.com", "search_pattern": "{brand}+site:sephora.com"},
                {"name": "Ulta Beauty", "domain": "ulta.com", "search_pattern": "{brand}+site:ulta.com"},
                {"name": "Dermstore", "domain": "dermstore.com", "search_pattern": "{brand}+site:dermstore.com"}
            ]
            for retailer in beauty_retailers:
                if retailer["domain"] in found_domains:
                    continue
                try:
                    direct_result = check_specific_retailer(brand_name, retailer)
                    if direct_result:
                        retailers.append(direct_result)
                        found_domains.add(retailer["domain"])
                except:
                    continue
        
        # Check for fitness/supplement pattern
        elif any(word in brand_name.lower() for word in ['fitness', 'protein', 'supplement', 'nutrition', 'vitamin', 'workout']):
            fitness_retailers = [
                {"name": "GNC", "domain": "gnc.com", "search_pattern": "{brand}+site:gnc.com"},
                {"name": "Vitamin Shoppe", "domain": "vitaminshoppe.com", "search_pattern": "{brand}+site:vitaminshoppe.com"},
                {"name": "Bodybuilding.com", "domain": "bodybuilding.com", "search_pattern": "{brand}+site:bodybuilding.com"},
                {"name": "The Feed", "domain": "thefeed.com", "search_pattern": "{brand}+site:thefeed.com"},
                {"name": "Rogue Fitness", "domain": "roguefitness.com", "search_pattern": "{brand}+site:roguefitness.com"}
            ]
            for retailer in fitness_retailers:
                if retailer["domain"] in found_domains:
                    continue
                try:
                    direct_result = check_specific_retailer(brand_name, retailer)
                    if direct_result:
                        retailers.append(direct_result)
                        found_domains.add(retailer["domain"])
                except:
                    continue
    
    progress_text.text(f"Completed enhanced Google Shopping search. Found {len(retailers)} retailers.")
    return retailers

# Function to check if a specific retailer carries a brand via direct site search
def check_specific_retailer(brand_name, retailer, product_skus=None):
    # Rotate user agents to avoid blocking
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive'
    }
    
    # Try checking with product SKUs first if available
    if product_skus is not None and not product_skus.empty:
        # Take up to 3 product names to search
        sample_products = product_skus.head(3).values.flatten().tolist()
        for product in sample_products:
            try:
                sku_search_query = f"{brand_name} {product} site:{retailer['domain']}"
                sku_search_url = f"https://www.google.com/search?q={quote_plus(sku_search_query)}"
                
                response = requests.get(sku_search_url, headers=headers, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Check for any search results
                    search_results = soup.find_all(['div', 'li'], class_=re.compile('(g|result)'))
                    
                    for result in search_results:
                        link = result.find('a')
                        if not link or 'href' not in link.attrs:
                            continue
                            
                        url = link['href']
                        if retailer['domain'] in url:
                            title_elem = result.find('h3')
                            if title_elem:
                                return {
                                    'Brand': brand_name,
                                    'Retailer': retailer['name'],
                                    'Domain': retailer['domain'],
                                    'Product': f"{product} - {title_elem.text.strip()}",
                                    'Price': "Check retailer site",
                                    'Search_Source': "SKU-Based Search",
                                    'Link': url,
                                    'Retailer_Confidence': "Very High"
                                }
            except:
                # If this approach fails, continue to the next method
                pass
    
    # Standard brand search
    search_url = f"https://www.google.com/search?q={retailer['search_pattern'].format(brand=quote_plus(brand_name))}"
    
    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for any search results
        search_results = soup.find_all(['div', 'li'], class_=re.compile('(g|result)'))
        
        # If we found search results that match the retailer domain
        found_product = False
        product_title = "N/A"
        product_url = ""
        
        for result in search_results:
            link = result.find('a')
            if not link or 'href' not in link.attrs:
                continue
                
            url = link['href']
            if retailer['domain'] in url:
                title_elem = result.find('h3')
                if title_elem:
                    product_title = title_elem.text.strip()
                    product_url = url
                    found_product = True
                    break
        
        if found_product:
            return {
                'Brand': brand_name,
                'Retailer': retailer['name'],
                'Domain': retailer['domain'],
                'Product': product_title,
                'Price': "Check retailer site",
                'Search_Source': "Direct Google Search",
                'Link': product_url,
                'Retailer_Confidence': "Very High"
            }
    except Exception as e:
        # Just return None on error
        pass
    
    return None

# Function to search for "where to buy" pages
def find_where_to_buy_page(brand_name, brand_website=None, product_skus=None):
    retailers = []
    
    # If brand website is provided, try to find where-to-buy pages
    if brand_website:
        try:
            # Normalize URL
            if not brand_website.startswith(('http://', 'https://')):
                brand_website = 'https://' + brand_website
                
            # Try common where to buy URL patterns
            possible_urls = [
                f"{brand_website}/pages/where-to-buy",
                f"{brand_website}/where-to-buy",
                f"{brand_website}/stores",
                f"{brand_website}/retailers",
                f"{brand_website}/find-a-store",
                f"{brand_website}/store-locator",
                f"{brand_website}/stockists",
                f"{brand_website}/pages/stockists",
                f"{brand_website}/pages/retailers"
            ]
            
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            headers = {'User-Agent': user_agent}
            
            for url in possible_urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for retailer links or mentions
                        for retailer in MAJOR_RETAILERS:
                            if retailer['domain'] in response.text or retailer['name'].lower() in response.text.lower():
                                retailers.append({
                                    'Brand': brand_name,
                                    'Retailer': retailer['name'],
                                    'Domain': retailer['domain'],
                                    'Product': "Listed on brand website",
                                    'Price': "N/A",
                                    'Search_Source': "Brand Website",
                                    'Link': url,
                                    'Retailer_Confidence': "Very High"
                                })
                                
                        # Also look for generic retailer links
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if href.startswith(('http://', 'https://')) and not any(domain in href for domain in [extract_domain(brand_website), 'facebook.com', 'twitter.com', 'instagram.com']):
                                retailer_domain = extract_domain(href)
                                # Skip if already found
                                if any(r['Domain'] == retailer_domain for r in retailers):
                                    continue
                                    
                                # Add as potential retailer
                                retailers.append({
                                    'Brand': brand_name,
                                    'Retailer': retailer_domain.split('.')[0].capitalize(),
                                    'Domain': retailer_domain,
                                    'Product': "Listed on brand website",
                                    'Price': "N/A",
                                    'Search_Source': "Brand Website Link",
                                    'Link': href,
                                    'Retailer_Confidence': "High"
                                })
                except:
                    continue
        except:
            pass
    
    # Search for where to buy pages using Google
    search_query = f"{brand_name} where to buy OR retailer OR store locator"
    search_url = f"https://www.google.com/search?q={quote_plus(search_query)}"
    
    try:
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        headers = {'User-Agent': user_agent}
        response = requests.get(search_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for search results that might be where-to-buy pages
            search_results = soup.find_all(['div', 'li'], class_=re.compile('(g|result)'))
            
            for result in search_results:
                link = result.find('a')
                if not link or 'href' not in link.attrs:
                    continue
                    
                url = link['href']
                title_elem = result.find('h3')
                
                # Skip results from the brand's own website if we already checked it
                if brand_website and extract_domain(brand_website) in url:
                    continue
                
                if title_elem:
                    title = title_elem.text.lower()
                    # Check if this looks like a "where to buy" page
                    where_to_buy_patterns = ['where to buy', 'store locator', 'find a store', 'retailers', 'stockists']
                    if any(pattern in title for pattern in where_to_buy_patterns):
                        try:
                            # Visit the page and look for retailer mentions
                            page_response = requests.get(url, headers=headers, timeout=15)
                            if page_response.status_code == 200:
                                page_soup = BeautifulSoup(page_response.text, 'html.parser')
                                page_text = page_soup.text.lower()
                                
                                # Check for retailer mentions
                                for retailer in MAJOR_RETAILERS:
                                    if retailer['domain'] in page_text or retailer['name'].lower() in page_text:
                                        if not any(r['Retailer'] == retailer['name'] for r in retailers):
                                            retailers.append({
                                                'Brand': brand_name,
                                                'Retailer': retailer['name'],
                                                'Domain': retailer['domain'],
                                                'Product': "Listed on where-to-buy page",
                                                'Price': "N/A",
                                                'Search_Source': "Where To Buy Page",
                                                'Link': url,
                                                'Retailer_Confidence': "High"
                                            })
                        except:
                            # Skip if we can't access the page
                            continue
    except Exception as e:
        st.error(f"Error searching for where-to-buy page: {str(e)}")
    
    return retailers

# Function to search for online retailers using Google
def find_online_retailers(brand_name, industry=None, product_skus=None):
    retailers = []
    found_domains = set()
    
    # Build search queries based on available information
    search_queries = [
        f"{brand_name} buy online",
        f"{brand_name} purchase online",
        f"{brand_name} authorized retailer",
        f"{brand_name} official retailer"
    ]
    
    # Add industry-specific queries if industry is provided
    if industry:
        search_queries.extend([
            f"{brand_name} {industry} retailer",
            f"{brand_name} {industry} store",
            f"buy {brand_name} {industry}"
        ])
    
    # Add product-specific queries if SKUs are provided
    if product_skus is not None and not product_skus.empty:
        sample_products = product_skus.head(2).values.flatten().tolist()
        for product in sample_products:
            search_queries.append(f"{brand_name} {product} buy")
    
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    headers = {'User-Agent': user_agent}
    
    # Process each search query
    for query in search_queries:
        try:
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=20"
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract search results
                search_results = soup.find_all(['div', 'li'], class_=re.compile('(g|result)'))
                
                for result in search_results:
                    link = result.find('a')
                    if not link or 'href' not in link.attrs:
                        continue
                        
                    url = link['href']
                    
                    # Skip if not a full URL
                    if not url.startswith(('http://', 'https://')):
                        continue
                    
                    domain = extract_domain(url)
                    
                    # Skip common non-retailer domains
                    skip_domains = ['google.', 'wikipedia.', 'facebook.', 'instagram.', 'twitter.', 
                                   'linkedin.', 'youtube.', 'reddit.', 'quora.', 'pinterest.']
                    if any(skip in domain.lower() for skip in skip_domains):
                        continue
                    
                    # Skip if already found
                    if domain.lower() in found_domains:
                        continue
                    
                    # Skip if it's the brand's own website
                    if brand_name.lower() in domain.lower():
                        continue
                    
                    found_domains.add(domain.lower())
                    
                    title_elem = result.find('h3')
                    title = title_elem.text.strip() if title_elem else "Unknown"
                    
                    # Extract snippet if available
                    snippet_elem = result.find(['div', 'span'], class_=re.compile('(VwiC3b|snippet|description)'))
                    snippet = snippet_elem.text.strip() if snippet_elem else ""
                    
                    # Calculate retailer confidence
                    confidence = "Medium"  # Default
                    
                    # Check for strong buying signals in the title or snippet
                    buy_signals = ['buy', 'purchase', 'shop', 'order', 'add to cart', 'add to bag', 'checkout', 'price', 'sale']
                    if any(signal in title.lower() or signal in snippet.lower() for signal in buy_signals):
                        confidence = "High"
                    
                    product_info = "Search result"
                    if product_skus is not None and not product_skus.empty:
                        for product in product_skus.values.flatten().tolist():
                            if product.lower() in title.lower() or product.lower() in snippet.lower():
                                product_info = f"Mentioned: {product}"
                                confidence = "Very High"
                                break
                    
                    retailers.append({
                        'Brand': brand_name,
                        'Retailer': domain.split('.')[0].capitalize(),
                        'Domain': domain,
                        'Product': product_info,
                        'Price': "N/A",
                        'Search_Source': f"Google: {query}",
                        'Link': url,
                        'Retailer_Confidence': confidence
                    })
            
            # Add delay to avoid rate limiting
            time.sleep(2)
        
        except Exception as e:
            continue
    
    return retailers

# Function to crawl brand website for retailer information
def crawl_brand_website(brand_name, brand_website, max_depth=2, max_pages=20):
    """
    Crawls the brand website to find retailer information.
    
    Args:
        brand_name: Name of the brand
        brand_website: URL of the brand website
        max_depth: Maximum link depth to crawl
        max_pages: Maximum number of pages to check
        
    Returns:
        List of retailer dictionaries found
    """
    retailers = []
    visited = set()
    to_visit = []
    
    # Normalize URL
    if not brand_website.startswith(('http://', 'https://')):
        brand_website = 'https://' + brand_website
    
    base_domain = extract_domain(brand_website)
    
    # Create initial page queue with potential retailer pages
    initial_paths = [
        "/",
        "/pages/where-to-buy",
        "/where-to-buy",
        "/stores",
        "/retailers",
        "/stockists",
        "/pages/stockists",
        "/find-a-store",
        "/store-locator",
        "/pages/retailers",
        "/partners",
        "/locations"
    ]
    
    # Add initial URLs to visit
    for path in initial_paths:
        to_visit.append({"url": f"{brand_website.rstrip('/')}{path}", "depth": 0})
    
    # Set up headers with user agent rotation
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
    ]
    
    # Common patterns that indicate a retailer/stockist page
    retailer_page_patterns = [
        'where to buy', 'store locator', 'find a store', 'retailers', 'stockists', 
        'dealer locator', 'authorized sellers', 'find a dealer', 'shop our products',
        'store finder', 'buy now', 'shop now', 'authorized retailers'
    ]
    
    # Create a progress indicator
    progress_text = st.empty()
    pages_checked = 0
    
    # Start crawling
    while to_visit and pages_checked < max_pages:
        # Get next URL to visit
        current = to_visit.pop(0)
        current_url = current["url"]
        current_depth = current["depth"]
        
        # Skip if already visited
        if current_url in visited:
            continue
        
        visited.add(current_url)
        pages_checked += 1
        
        progress_text.text(f"Crawling brand website: checked {pages_checked}/{max_pages} pages...")
        
        try:
            # Get the page
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': brand_website,
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(current_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if this page looks like a retailer/stockist page
            is_retailer_page = False
            page_title = soup.title.text.lower() if soup.title else ""
            page_text = soup.get_text().lower()
            
            for pattern in retailer_page_patterns:
                if pattern in page_title or pattern in page_text:
                    is_retailer_page = True
                    break
            
            # Extract all links to continue crawling
            if current_depth < max_depth:
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link['href']
                    
                    # Normalize the URL
                    if href.startswith('/'):
                        # Convert relative URL to absolute
                        href = f"{brand_website.rstrip('/')}{href}"
                    elif not href.startswith(('http://', 'https://')):
                        # Skip anchors, javascript links, etc.
                        continue
                    
                    # Only follow links on the same domain
                    if extract_domain(href) == base_domain:
                        # Prioritize links that look like retailer pages
                        link_text = link.text.lower()
                        priority = 0
                        
                        for pattern in retailer_page_patterns:
                            if pattern in link_text or pattern in href.lower():
                                priority = 10  # Higher priority for retailer-related links
                                break
                        
                        # Add to visit queue with appropriate priority
                        if href not in visited:
                            if priority > 0:
                                # Add high-priority links to the front of the queue
                                to_visit.insert(0, {"url": href, "depth": current_depth + 1})
                            else:
                                # Add normal links to the back
                                to_visit.append({"url": href, "depth": current_depth + 1})
            
            # If this is a retailer page or any page on the site, search for retailer links
            # Examine external links for retailer connections
            external_links = [a for a in soup.find_all('a', href=True) 
                             if a['href'].startswith(('http://', 'https://')) 
                             and extract_domain(a['href']) != base_domain
                             and not any(social in a['href'].lower() for social in ['facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com'])]
            
            # Check if any known retailers are linked
            for link in external_links:
                href = link['href']
                link_domain = extract_domain(href)
                link_text = link.text.strip()
                
                # Skip common non-retailer domains
                if any(skip in link_domain.lower() for skip in ['google.', 'facebook.', 'twitter.', 'youtube.', 'instagram.']):
                    continue
                
                # Check if it matches any known major retailers
                matched_retailer = None
                for retailer in MAJOR_RETAILERS:
                    if retailer['domain'] in link_domain or retailer['name'].lower() in link_text.lower():
                        matched_retailer = retailer
                        break
                
                if matched_retailer:
                    # Found a known retailer reference
                    if not any(r['Domain'] == matched_retailer['domain'] for r in retailers):
                        retailers.append({
                            'Brand': brand_name,
                            'Retailer': matched_retailer['name'],
                            'Domain': matched_retailer['domain'],
                            'Product': "Found on brand website",
                            'Price': "N/A",
                            'Search_Source': f"Website Crawl: {current_url}",
                            'Link': href,
                            'Retailer_Confidence': "Very High" if is_retailer_page else "High"
                        })
                else:
                    # Check if this link looks like a retailer
                    retailer_signals = ['shop', 'buy', 'store', 'retail', 'purchase', 'order']
                    is_likely_retailer = False
                    
                    # Check the link text and URL for retailer signals
                    for signal in retailer_signals:
                        if signal in link_text.lower() or signal in href.lower():
                            is_likely_retailer = True
                            break
                    
                    # Additionally check if this is a product link (often contains /p/ or /product/)
                    if '/p/' in href or '/product/' in href or '/products/' in href:
                        is_likely_retailer = True
                    
                    if is_likely_retailer and not any(r['Domain'] == link_domain for r in retailers):
                        # Extract retailer name from domain or link text
                        retailer_name = link_text if link_text and len(link_text) < 30 else link_domain.split('.')[0].capitalize()
                        
                        retailers.append({
                            'Brand': brand_name,
                            'Retailer': retailer_name,
                            'Domain': link_domain,
                            'Product': "Found on brand website",
                            'Price': "N/A",
                            'Search_Source': f"Website Crawl: {current_url}",
                            'Link': href,
                            'Retailer_Confidence': "High" if is_retailer_page else "Medium"
                        })
            
            # Look for retailer mentions in the text (even if no direct links)
            if is_retailer_page:
                for retailer in MAJOR_RETAILERS:
                    if retailer['name'].lower() in page_text and not any(r['Domain'] == retailer['domain'] for r in retailers):
                        retailers.append({
                            'Brand': brand_name,
                            'Retailer': retailer['name'],
                            'Domain': retailer['domain'],
                            'Product': "Mentioned on brand website",
                            'Price': "N/A",
                            'Search_Source': f"Website Text: {current_url}",
                            'Link': f"https://{retailer['domain']}",
                            'Retailer_Confidence': "Medium"
                        })
            
            # Add a small delay to avoid overloading the server
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            # Just skip this URL on error
            continue
    
    # Complete the progress indicator
    progress_text.text(f"Completed website crawl: checked {pages_checked} pages, found {len(retailers)} retailers")
    
    return retailers

def search_google_shopping(brand_name, num_results=30):
    """
    Uses Selenium to scrape Google Shopping for retailer URLs.
    Filters results that contain the brand name in the URL.
    """
    query = brand_name.replace(" ", "+")
    search_url = f"https://www.google.com/search?tbm=shop&q={query}"
    
    options = Options()
    options.headless = True  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(search_url)
    
    time.sleep(3)  # Wait for page to load
    
    retailers = []
    brand_name_lower = brand_name.lower().replace(" ", "")

    results = driver.find_elements(By.TAG_NAME, "a")
    
    for result in results:
        url = result.get_attribute("href")
        if url and "google.com" not in url and brand_name_lower in url.lower():
            retailers.append(url)
        if len(retailers) >= num_results:
            break
    
    driver.quit()  # Close browser session
    return retailers

def find_retailers_comprehensive(brand_name, brand_website=None, industry=None, product_skus=None, include_where_to_buy=True):
    all_retailers = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    progress_steps = 7
    current_step = 0
    
    status_text.text(f"Searching Google Shopping for {brand_name} products...")
    google_shopping_retailers = search_google_shopping(brand_name, num_results=30)
    
    for retailer in google_shopping_retailers:
        all_retailers.append({
            'Brand': brand_name,
            'Retailer': retailer.split('.')[0].capitalize(),
            'Domain': retailer,
            'Search_Source': "Google Shopping",
            'Link': retailer
        })
    
    progress_bar.progress(1.0)
    status_text.text(f"Found {len(all_retailers)} retailers carrying {brand_name}")
    
    return all_retailers

# Function to process a brand with comprehensive approach
def process_brand_retailers_comprehensive(brand_name, brand_website=None, industry=None, product_skus=None, include_where_to_buy=True):
    # Check if input is a URL and extract brand if so
    original_input = brand_name
    if '.' in brand_name and '/' in brand_name:
        domain = extract_domain(brand_name)
        extracted_brand = extract_brand_from_url(brand_name)
        if extracted_brand:
            if not brand_website:  # Only update if not explicitly provided
                brand_website = domain
            st.info(f"Detected URL input. Searching for retailers that carry: {extracted_brand} (from {domain})")
            # Keep original input for possible direct URL checks
            brand_name = extracted_brand
    
    # Start with comprehensive retailer search
    retailers = find_retailers_comprehensive(brand_name, brand_website, industry, product_skus, include_where_to_buy)
    
    # If no results and input was URL, try again with domain
    if not retailers and '.' in original_input and not brand_website:
        domain = extract_domain(original_input)
        st.info(f"No results found with extracted brand name. Trying domain: {domain}")
        retailers = find_retailers_comprehensive(domain, domain, industry, product_skus, include_where_to_buy)
    
    # Create DataFrame
    if retailers:
        df = pd.DataFrame(retailers)
        st.success(f"Found {len(retailers)} retailers carrying {brand_name}")
    else:
        df = pd.DataFrame(columns=['Brand', 'Retailer', 'Domain', 'Product', 'Price', 'Search_Source', 'Link', 'Retailer_Confidence'])
        st.warning(f"No retailers found for {brand_name}. Try a different search term or brand name.")
    
    return df

# Function to process multiple brands
def process_multiple_brands_comprehensive(brands, brand_websites=None, industry=None, product_skus=None, include_where_to_buy=True):
    all_results = []
    
    progress_outer = st.progress(0)
    brand_status = st.empty()
    
    # Prepare brand websites mapping if provided
    brand_website_map = {}
    if brand_websites and isinstance(brand_websites, list) and len(brand_websites) == len(brands):
        brand_website_map = dict(zip(brands, brand_websites))
    
    for i, brand in enumerate(brands):
        brand_status.text(f"Processing brand {i+1}/{len(brands)}: {brand}")
        
        # Get brand website if available
        brand_website = brand_website_map.get(brand, None)
        
        # Process each brand
        brand_results = process_brand_retailers_comprehensive(brand, brand_website, industry, product_skus, include_where_to_buy)
        if not brand_results.empty:
            all_results.append(brand_results)
        
        # Update progress
        progress_outer.progress((i + 1) / len(brands))
    
    # Combine results
    combined_results = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame(columns=['Brand', 'Retailer', 'Domain', 'Product', 'Price', 'Search_Source', 'Link', 'Retailer_Confidence'])
    
    # Complete
    progress_outer.progress(1.0)
    brand_status.text(f"Completed processing {len(brands)} brands")
    
    return combined_results

# Main app layout with tabs
tab1, tab2 = st.tabs(["Search by Brand", "Bulk Brand Search"])

# Tab 1: Single Brand Search
with tab1:
    st.header("Find Retailers for a Brand")
    
    # Basic required information
    col1, col2 = st.columns([2, 1])
    
    with col1:
        brand_name = st.text_input("Enter brand name", 
                                  help="Enter brand name (e.g., 'Snow Cosmetics')")
    
    with col2:
        include_where_to_buy = st.checkbox("Search for 'Where to Buy' pages", value=True,
                                         help="Look for pages that list retailers")
    
    # Optional brand-specific information (expandable)
    with st.expander("Additional Brand Information (Optional - Improves Search Accuracy)"):
        col1, col2 = st.columns(2)
        
        with col1:
            brand_website = st.text_input("Brand Website URL", 
                                        help="Official brand website (e.g., 'trysnow.com')")
        
        with col2:
            industry = st.text_input("Industry/Product Category", 
                                   help="E.g., 'cosmetics', 'electronics', 'apparel'")
        
        # Product SKUs upload
        st.subheader("Product SKUs/Names (Optional)")
        st.markdown("Upload a CSV/Excel file with product names to enhance search accuracy")
        
        sku_file = st.file_uploader("Upload product list", type=["csv", "xlsx", "xls"])
        
        if sku_file:
            try:
                # Determine file type and read accordingly
                if sku_file.name.endswith('.csv'):
                    sku_df = pd.read_csv(sku_file)
                else:
                    sku_df = pd.read_excel(sku_file)
                
                # Let user select the column with product names
                if not sku_df.empty:
                    st.write(f"Found {len(sku_df)} products in file")
                    
                    # Try to find 'Name' column or let user select
                    if 'Name' in sku_df.columns:
                        name_column = 'Name'
                        st.info(f"Using 'Name' column for product names")
                    else:
                        name_column = st.selectbox("Select column with product names", 
                                                 sku_df.columns.tolist())
                    
                    # Preview products
                    with st.expander("Preview Products"):
                        st.write(sku_df[name_column].head(10))
                    
                    # Store only the product names column
                    st.session_state['product_skus'] = sku_df[[name_column]]
            except Exception as e:
                st.error(f"Error processing product file: {str(e)}")
    
    if st.button("Find Retailers", key="single_search_btn") and brand_name:
        # Add to search history
        if brand_name not in st.session_state['search_history']:
            st.session_state['search_history'].append(brand_name)
        
        # Process brand search with comprehensive approach
        with st.spinner(f"Searching for retailers carrying {brand_name}..."):
            results_df = process_brand_retailers_comprehensive(
                brand_name, 
                brand_website,
                industry,
                st.session_state.get('product_skus', None),
                include_where_to_buy
            )
            
            # Store results
            st.session_state['results_df'] = results_df
    
    # Show recent searches
    if st.session_state['search_history']:
        with st.expander("Recent Searches"):
            for prev_brand in st.session_state['search_history'][-5:]:  # Show only the most recent 5
                if st.button(prev_brand, key=f"history_{prev_brand}"):
                    # Search for this brand again
                    with st.spinner(f"Searching for retailers carrying {prev_brand}..."):
                        results_df = process_brand_retailers_comprehensive(
                            prev_brand, 
                            None,  # No website info for history searches
                            None,  # No industry info for history searches
                            st.session_state.get('product_skus', None),
                            include_where_to_buy
                        )
                        st.session_state['results_df'] = results_df

# Tab 2: Bulk Brand Search
with tab2:
    st.header("Find Retailers for Multiple Brands")
    
    # Two-column layout for inputs
    col1, col2 = st.columns([2, 1])
    
    with col1:
        brands_text = st.text_area("Enter brand names (one per line)")
    
    with col2:
        bulk_include_where_to_buy = st.checkbox("Search for 'Where to Buy' pages", 
                                               value=True, 
                                               key="bulk_wtb")
        
        bulk_industry = st.text_input("Industry/Product Category (Optional)", 
                                     help="E.g., 'cosmetics', 'electronics'",
                                     key="bulk_industry")
    
    # Brand-website mapping (optional)
    with st.expander("Brand Website Mapping (Optional)"):
        st.markdown("If you have the official websites for your brands, enter them below to improve search accuracy")
        st.markdown("Format: One brand website per line, matching the order of brands above")
        websites_text = st.text_area("Brand websites (one per line)", height=100)
    
    # Product SKUs upload
    with st.expander("Product SKUs/Names (Optional)"):
        st.markdown("Upload a CSV/Excel file with product names to enhance search accuracy")
        
        bulk_sku_file = st.file_uploader("Upload product list", type=["csv", "xlsx", "xls"], key="bulk_sku_file")
        
        if bulk_sku_file:
            try:
                # Determine file type and read accordingly
                if bulk_sku_file.name.endswith('.csv'):
                    bulk_sku_df = pd.read_csv(bulk_sku_file)
                else:
                    bulk_sku_df = pd.read_excel(bulk_sku_file)
                
                # Let user select the column with product names
                if not bulk_sku_df.empty:
                    st.write(f"Found {len(bulk_sku_df)} products in file")
                    
                    # Try to find 'Name' column or let user select
                    if 'Name' in bulk_sku_df.columns:
                        bulk_name_column = 'Name'
                        st.info(f"Using 'Name' column for product names")
                    else:
                        bulk_name_column = st.selectbox("Select column with product names", 
                                                      bulk_sku_df.columns.tolist(),
                                                      key="bulk_name_col")
                    
                    # Preview products
                    with st.expander("Preview Products"):
                        st.write(bulk_sku_df[bulk_name_column].head(10))
                    
                    # Store only the product names column
                    st.session_state['bulk_product_skus'] = bulk_sku_df[[bulk_name_column]]
            except Exception as e:
                st.error(f"Error processing product file: {str(e)}")
    
    # Alternative: Upload CSV with brands
    uploaded_file = st.file_uploader("Or upload a CSV file with brand names (one column)", type=["csv", "xlsx", "xls"])
    
    # Process button for text input
    if st.button("Process All Brands", key="bulk_process_btn") and brands_text:
        # Split text into list of brands
        brands_list = [brand.strip() for brand in brands_text.split('\n') if brand.strip()]
        
        # Parse websites if provided
        websites_list = None
        if websites_text:
            websites_list = [website.strip() for website in websites_text.split('\n') if website.strip()]
            # Ensure websites list matches brands list
            if len(websites_list) != len(brands_list):
                st.warning(f"Number of websites ({len(websites_list)}) doesn't match number of brands ({len(brands_list)}). Using brands only.")
                websites_list = None
        
        if brands_list:
            # Process multiple brands
            with st.spinner(f"Searching for retailers for {len(brands_list)} brands..."):
                results_df = process_multiple_brands_comprehensive(
                    brands_list,
                    websites_list,
                    bulk_industry if bulk_industry else None,
                    st.session_state.get('bulk_product_skus', None),
                    bulk_include_where_to_buy
                )
                st.session_state['results_df'] = results_df
        else:
            st.warning("Please enter at least one brand name")
    
    # Process button for CSV upload
    elif uploaded_file and st.button("Process Brands from File"):
        try:
            # Determine file type and read accordingly
            if uploaded_file.name.endswith('.csv'):
                brands_df = pd.read_csv(uploaded_file)
            else:
                brands_df = pd.read_excel(uploaded_file)
            
            # Get brand column
            if 'Brand' in brands_df.columns:
                brand_column = 'Brand'
            else:
                brand_column = st.selectbox("Select column with brand names", brands_df.columns.tolist())
            
            # Get website column if available
            website_column = None
            websites_list = None
            if any(col.lower() in ['website', 'url', 'site'] for col in brands_df.columns):
                potential_website_cols = [col for col in brands_df.columns if col.lower() in ['website', 'url', 'site']]
                website_column = st.selectbox("Select column with brand websites (optional)", 
                                            ['None'] + potential_website_cols)
                if website_column != 'None':
                    websites_list = brands_df[website_column].fillna('').tolist()
            
            # Get brands list
            brands_list = brands_df[brand_column].dropna().tolist()
            
            if brands_list:
                st.write(f"Found {len(brands_list)} brands in file")
                
                # Process multiple brands
                with st.spinner(f"Searching for retailers for {len(brands_list)} brands..."):
                    results_df = process_multiple_brands_comprehensive(
                        brands_list,
                        websites_list,
                        bulk_industry if bulk_industry else None,
                        st.session_state.get('bulk_product_skus', None),
                        bulk_include_where_to_buy
                    )
                    st.session_state['results_df'] = results_df
            else:
                st.warning("No valid brand names found in the file")
        except Exception as e:
            st.error(f"Error processing brand file: {str(e)}")
            st.exception(e)

# Display results if available
if st.session_state['results_df'] is not None:
    if st.session_state['results_df'].empty:
        st.warning("No retailers found. Try a different search term or brand name.")
    else:
        st.header("Search Results")
        
        # Filter options
        with st.expander("Filter Results"):
            col1, col2, col3 = st.columns(3)
            
            # Create filters if we have data
            filtered_df = st.session_state['results_df']
            
            with col1:
                if 'Brand' in filtered_df.columns and filtered_df['Brand'].nunique() > 1:
                    brands_in_results = filtered_df['Brand'].unique().tolist()
                    selected_brands = st.multiselect("Filter by brand", 
                                                   options=brands_in_results, 
                                                   default=brands_in_results)
                    if selected_brands:
                        filtered_df = filtered_df[filtered_df['Brand'].isin(selected_brands)]
            
            with col2:
                if 'Retailer_Confidence' in filtered_df.columns:
                    confidence_levels = filtered_df['Retailer_Confidence'].unique().tolist()
                    default_levels = [level for level in confidence_levels if level in ["Very High", "High"]]
                    selected_confidence = st.multiselect("Filter by confidence level", 
                                                       options=confidence_levels, 
                                                       default=default_levels if default_levels else confidence_levels)
                    if selected_confidence:
                        filtered_df = filtered_df[filtered_df['Retailer_Confidence'].isin(selected_confidence)]
            
            with col3:
                if 'Search_Source' in filtered_df.columns:
                    sources_in_results = filtered_df['Search_Source'].unique().tolist()
                    selected_sources = st.multiselect("Filter by source", 
                                                    options=sources_in_results, 
                                                    default=sources_in_results)
                    if selected_sources:
                        filtered_df = filtered_df[filtered_df['Search_Source'].isin(selected_sources)]
        
        # Display results
        st.dataframe(filtered_df)
        
        # Summary statistics
        st.subheader("Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Retailers Found", len(filtered_df))
        
        with col2:
            retailer_count = filtered_df['Retailer'].nunique() if 'Retailer' in filtered_df.columns else 0
            st.metric("Unique Retailers", retailer_count)
        
        with col3:
            brand_count = filtered_df['Brand'].nunique() if 'Brand' in filtered_df.columns else 0
            st.metric("Brands Searched", brand_count)
        
        # Download options
        st.subheader("Download Results")
        col1, col2 = st.columns(2)
        
        # Get timestamp for filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Download as CSV
        csv = filtered_df.to_csv(index=False)
        col1.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"brand_retailers_{timestamp}.csv",
            mime="text/csv"
        )
        
        # Download as Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            filtered_df.to_excel(writer, index=False, sheet_name='All Results')
            
            # Create a separate worksheet for each brand
            if 'Brand' in filtered_df.columns:
                for brand in filtered_df['Brand'].unique():
                    brand_results = filtered_df[filtered_df['Brand'] == brand]
                    # Clean brand name for worksheet name
                    sheet_name = brand[:31].replace(':', '').replace('\\', '').replace('/', '').replace('?', '').replace('*', '').replace('[', '').replace(']', '')
                    brand_results.to_excel(writer, index=False, sheet_name=sheet_name)
        
        buffer.seek(0)
        col2.download_button(
            label="Download as Excel",
            data=buffer,
            file_name=f"brand_retailers_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Reset results button
if st.session_state['results_df'] is not None:
    if st.button("Clear Results"):
        st.session_state['results_df'] = None
        st.session_state['product_skus'] = None
        st.session_state['bulk_product_skus'] = None
        st.experimental_rerun()

