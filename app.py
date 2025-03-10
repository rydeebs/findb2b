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

# Function to use a comprehensive retailer search
def find_retailers_comprehensive(brand_name, brand_website=None, industry=None, product_skus=None, include_where_to_buy=True):
    all_retailers = []
    
    # Create progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    progress_steps = 5  # Total number of search methods
    current_step = 0
    
    # 1. Try major retailers first
    status_text.text(f"Checking major retailers for {brand_name} products...")
    for retailer in MAJOR_RETAILERS:
        result = check_specific_retailer(brand_name, retailer, product_skus)
        if result:
            all_retailers.append(result)
    
    current_step += 1
    progress_bar.progress(current_step / progress_steps)
    
    # 2. Try where-to-buy pages if requested
    if include_where_to_buy:
        status_text.text(f"Looking for 'where to buy' pages for {brand_name}...")
        where_to_buy_retailers = find_where_to_buy_page(brand_name, brand_website, product_skus)
        
        # Add new retailers (avoid duplicates)
        existing_domains = set(r['Domain'] for r in all_retailers)
        for retailer in where_to_buy_retailers:
            if retailer['Domain'] not in existing_domains:
                all_retailers.append(retailer)
                existing_domains.add(retailer['Domain'])
    
    current_step += 1
    progress_bar.progress(current_step / progress_steps)
    
    # 3. Try general retailer search
    status_text.text(f"Searching for online retailers selling {brand_name}...")
    online_retailers = find_online_retailers(brand_name, industry, product_skus)
    
    # Add new retailers (avoid duplicates)
    existing_domains = set(r['Domain'] for r in all_retailers)
    for retailer in online_retailers:
        if retailer['Domain'] not in existing_domains:
            all_retailers.append(retailer)
            existing_domains.add(retailer['Domain'])
    
    current_step += 1
    progress_bar.progress(current_step / progress_steps)
    
    # 4. Try product-specific searches if SKUs are provided
    if product_skus is not None and not product_skus.empty:
        status_text.text(f"Performing product-specific searches for {brand_name}...")
        # Already done in previous steps
    
    current_step += 1
    progress_bar.progress(current_step / progress_steps)
    
    # 5. Try industry-specific searches if industry is provided
    if industry:
        status_text.text(f"Checking {industry} retailers for {brand_name}...")
        # Already included in previous steps
    
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
