import streamlit as st
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

# Function to normalize URLs
def normalize_url(url):
    if not url:
        return ""
    # Add http:// prefix if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Parse the URL to handle variations
    parsed = urlparse(url)
    
    # Remove 'www.' if present
    netloc = parsed.netloc
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    
    # Return the normalized domain
    return netloc

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

# Function to search for retailers using Google Shopping
def search_google_shopping(brand_name, num_results=30):
    """
    Directly searches Google Shopping for the brand and extracts retailer information.
    
    Args:
        brand_name: Name of the brand to search for
        num_results: Maximum number of results to process
        
    Returns:
        List of retailer dictionaries found
    """
    retailers = []
    found_domains = set()
    
    # Prepare search query
    query = quote_plus(brand_name)
    
    # Different Google Shopping URL formats to try
    search_urls = [
        f"https://www.google.com/search?q={query}&tbm=shop&num={num_results}",
        f"https://www.google.com/search?q={query}+buy&tbm=shop&num={num_results}",
        f"https://www.google.com/search?q={query}+product&tbm=shop&num={num_results}"
    ]
    
    # Rotate user agents
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
        'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
    ]
    
    progress_text = st.empty()
    progress_text.text(f"Searching Google Shopping for {brand_name}...")
    
    # Try each search URL
    for url_index, search_url in enumerate(search_urls):
        try:
            # Set up request with different user agent for each attempt
            headers = {
                'User-Agent': user_agents[url_index % len(user_agents)],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Send request with longer timeout
            response = requests.get(search_url, headers=headers, timeout=20)
            
            if response.status_code != 200:
                continue
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for different Google Shopping result formats
            # Format 1: Standard shopping cards
            shopping_items = soup.find_all(['div', 'li'], class_=re.compile('(sh-dgr__content|sh-dlr__list-result)'))
            
            # Format 2: Shopping knowledge panel
            if not shopping_items:
                shopping_items = soup.find_all(['div'], class_=re.compile('(commercial-unit-desktop-top|pla-unit)'))
            
            # Format 3: Individual shopping items
            if not shopping_items:
                shopping_items = soup.find_all(['div'], attrs={'data-docid': True})
            
            progress_text.text(f"Found {len(shopping_items)} shopping results for {brand_name}. Extracting retailers...")
            
            # Process each shopping item
            for item in shopping_items:
                try:
                    # Find merchant information (try multiple selectors)
                    merchant_elem = None
                    for selector in [
                        ['div', 'span'], {'class': re.compile('(merchant|sh-dlr__merchant|retailer)')},
                        ['a'], {'href': re.compile('(url=)')},
                        ['div'], {'class': re.compile('(a5OGkf)')}  # Another common Google merchant class
                    ]:
                        merchant_elem = item.find(*selector)
                        if merchant_elem:
                            break
                    
                    # If we still don't have a merchant, look for any link
                    if not merchant_elem:
                        links = item.find_all('a', href=True)
                        for link in links:
                            if 'google' not in link['href'] and 'url=' in link['href']:
                                merchant_elem = link
                                break
                    
                    if merchant_elem:
                        # Extract merchant name and link
                        merchant_text = merchant_elem.text.strip()
                        merchant_link = None
                        
                        # Try to find merchant link
                        if 'href' in merchant_elem.attrs:
                            href = merchant_elem['href']
                            # Google prepends URLs with '/url?q=' or similar
                            if 'url=' in href:
                                url_match = re.search(r'url=([^&]+)', href)
                                if url_match:
                                    merchant_link = url_match.group(1)
                        
                        # If still no link, search parent elements
                        if not merchant_link:
                            parent_links = item.find_all('a', href=True)
                            for parent_link in parent_links:
                                if 'url=' in parent_link['href']:
                                    url_match = re.search(r'url=([^&]+)', parent_link['href'])
                                    if url_match:
                                        merchant_link = url_match.group(1)
                                        break
                        
                        # Clean merchant name if needed
                        if not merchant_text or merchant_text.lower() in ['shop', 'buy']:
                            merchant_text = 'Unknown Retailer'
                        
                        # Extract domain if link exists
                        domain = extract_domain(merchant_link) if merchant_link else None
                        
                        # Skip Google's own shopping links
                        if domain and 'google' in domain:
                            continue
                            
                        # Use domain as merchant name if we couldn't extract it
                        if merchant_text == 'Unknown Retailer' and domain:
                            merchant_text = domain.split('.')[0].capitalize()
                            
                        # Skip if no merchant info could be found
                        if not domain and merchant_text == 'Unknown Retailer':
                            continue
                            
                        # Skip if we've already found this domain
                        if domain and domain.lower() in found_domains:
                            continue
                            
                        # Skip common non-retailer domains
                        skip_domains = ['google.', 'wikipedia.', 'youtube.', 'facebook.', 'twitter.', 'instagram.']
                        if domain and any(skip in domain.lower() for skip in skip_domains):
                            continue
                            
                        # Add to found domains
                        if domain:
                            found_domains.add(domain.lower())
                        
                        # Find price if available
                        price = "N/A"
                        price_elem = item.find(text=re.compile(r'\$[\d,]+\.\d{2}'))
                        if price_elem:
                            price = price_elem
                        
                        # Find title if available
                        title = "N/A"
                        title_elem = item.find('h3') or item.find('h4') or item.find(['div', 'span'], class_=re.compile('(title|product)'))
                        if title_elem:
                            title = title_elem.text.strip()
                        
                        # Determine final URL
                        link_url = merchant_link if merchant_link else f"https://{domain}" if domain else ""
                        
                        # Add to results
                        retailers.append({
                            'Brand': brand_name,
                            'Retailer': merchant_text,
                            'Domain': domain if domain else "unknown",
                            'Product': title,
                            'Price': price,
                            'Search_Source': "Google Shopping Direct",
                            'Link': link_url,
                            'Retailer_Confidence': "Very High"
                        })
                except Exception as e:
                    # Skip this item on error
                    continue
            
            # If we found some results, we can break the loop
            if retailers:
                break
                
            # Add delay between attempts
            time.sleep(2)
            
        except Exception as e:
            # Try next URL format on error
            continue
    
    progress_text.text(f"Found {len(retailers)} retailers from Google Shopping")
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

# Function to use a comprehensive retailer search with emphasis on Google Shopping
def find_retailers_comprehensive(brand_name, brand_website=None, industry=None, product_skus=None, include_where_to_buy=True):
    all_retailers = []
    
    # Create progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    progress_steps = 7  # Total number of search methods 
    current_step = 0
    
    # 1. PRIORITIZE: Direct Google Shopping search first
    status_text.text(f"Searching Google Shopping for {brand_name} products...")
    google_shopping_retailers = search_google_shopping(brand_name, num_results=30)
    all_retailers.extend(google_shopping_retailers)
    existing_domains = set(r['Domain'] for r in all_retailers if r['Domain'] != "unknown")
    
    current_step += 1
    progress_bar.progress(current_step / progress_steps)
    
    # 2. Try major retailers directly
    status_text.text(f"Checking major retailers for {brand_name} products...")
    for retailer in MAJOR_RETAILERS:
        # Skip if we already found this retailer in Google Shopping
        if retailer['domain'] in existing_domains:
            continue
            
        result = check_specific_retailer(brand_name, retailer, product_skus)
        if result:
            all_retailers.append(result)
            existing_domains.add(retailer['domain'])
    
    current_step += 1
    progress_bar.progress(current_step / progress_steps)
    
    # 3. Deep crawl of the brand website if provided
    if brand_website:
        status_text.text(f"Crawling {brand_website} for retailer information...")
        website_retailers = crawl_brand_website(brand_name, brand_website, max_depth=2, max_pages=30)
        
        # Add new retailers (avoid duplicates)
        for retailer in website_retailers:
            if retailer['Domain'] not in existing_domains:
                all_retailers.append(retailer)
                existing_domains.add(retailer['Domain'])
    
    current_step += 1
    progress_bar.progress(current_step / progress_steps)
    
    # 4. Try where-to-buy pages if requested (using simpler method as backup)
    if include_where_to_buy and (not brand_website or len(all_retailers) < 5):
        status_text.text(f"Looking for 'where to buy' pages for {brand_name}...")
        where_to_buy_retailers = find_where_to_buy_page(brand_name, brand_website, product_skus)
        
        # Add new retailers (avoid duplicates)
        for retailer in where_to_buy_retailers:
            if retailer['Domain'] not in existing_domains:
                all_retailers.append(retailer)
                existing_domains.add(retailer['Domain'])
    
    current_step += 1
    progress_bar.progress(current_step / progress_steps)
    
    # 5. Try general retailer search if we still don't have many results
    if len(all_retailers) < 10:
        status_text.text(f"Searching for online retailers selling {brand_name}...")
        online_retailers = find_online_retailers(brand_name, industry, product_skus)
        
        # Add new retailers (avoid duplicates)
        for retailer in online_retailers:
            if retailer['Domain'] not in existing_domains:
                all_retailers.append(retailer)
                existing_domains.add(retailer['Domain'])
    
    current_step += 1
    progress_bar.progress(current_step / progress_steps)
    
    # 6. Try product-specific searches if SKUs are provided
    if product_skus is not None and not product_skus.empty and len(all_retailers) < 15:
        status_text.text(f"Performing product-specific searches for {brand_name}...")
        
        # Take top 2 product SKUs for specific searches
        sample_products = product_skus.head(2).values.flatten().tolist()
        
        for product in sample_products:
            product_search_query = f"{brand_name} {product} buy online"
            product_search_url = f"https://www.google.com/search?q={quote_plus(product_search_query)}&num=10"
            
            try:
                user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                headers = {'User-Agent': user_agent}
                response = requests.get(product_search_url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
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
                        
                        # Skip common non-retailer domains and brand's own domain
                        skip_domains = ['google.', 'wikipedia.', 'facebook.', 'instagram.', 'twitter.', 
                                       'linkedin.', 'youtube.', 'reddit.', 'quora.', 'pinterest.']
                        if any(skip in domain.lower() for skip in skip_domains) or (brand_website and domain == extract_domain(brand_website)):
                            continue
                        
                        # Skip if already found
                        if domain.lower() in existing_domains:
                            continue
                        
                        existing_domains.add(domain.lower())
                        
                        title_elem = result.find('h3')
                        title = title_elem.text.strip() if title_elem else "Unknown"
                        
                        all_retailers.append({
                            'Brand': brand_name,
                            'Retailer': domain.split('.')[0].capitalize(),
                            'Domain': domain,
                            'Product': f"Found: {product}",
                            'Price': "N/A",
                            'Search_Source': "Product-Specific Search",
                            'Link': url,
                            'Retailer_Confidence': "Very High"  # High confidence because product was specifically found
                        })
                
                # Add delay between product searches
                time.sleep(2)
            except:
                continue
    
    current_step += 1
    progress_bar.progress(current_step / progress_steps)
    
    # 7. Try industry-specific searches if industry is provided
    if industry and len(all_retailers) < 20:
        status_text.text(f"Checking {industry} retailers for {brand_name}...")
        industry_search_query = f"{brand_name} {industry} retailers"
        industry_search_url = f"https://www.google.com/search?q={quote_plus(industry_search_query)}&num=10"
        
        try:
            user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15'
            headers = {'User-Agent': user_agent}
            response = requests.get(industry_search_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
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
                    
                    # Skip common non-retailer domains and brand's own domain
                    skip_domains = ['google.', 'wikipedia.', 'facebook.', 'instagram.', 'twitter.', 
                                   'linkedin.', 'youtube.', 'reddit.', 'quora.', 'pinterest.']
                    if any(skip in domain.lower() for skip in skip_domains) or (brand_website and domain == extract_domain(brand_website)):
                        continue
                    
                    # Skip if already found
                    if domain.lower() in existing_domains:
                        continue
                    
                    existing_domains.add(domain.lower())
                    
                    title_elem = result.find('h3')
                    title = title_elem.text.strip() if title_elem else "Unknown"
                    
                    all_retailers.append({
                        'Brand': brand_name,
                        'Retailer': domain.split('.')[0].capitalize(),
                        'Domain': domain,
                        'Product': f"Industry: {industry}",
                        'Price': "N/A",
                        'Search_Source': "Industry-Specific Search",
                        'Link': url,
                        'Retailer_Confidence': "Medium"
                    })
        except:
            pass
    
    current_step += 1
    progress_bar.progress(current_step / progress_steps)
    
    # Complete progress
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
