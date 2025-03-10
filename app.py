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
st.markdown("Discover retailers that carry specific brands")

# Initialize session state variables
if 'results_df' not in st.session_state:
    st.session_state['results_df'] = None

if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []

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
    {"name": "Home Depot", "domain": "homedepot.com", "search_pattern": "{brand}+site:homedepot.com"},
    {"name": "Lowe's", "domain": "lowes.com", "search_pattern": "{brand}+site:lowes.com"},
    {"name": "Macy's", "domain": "macys.com", "search_pattern": "{brand}+site:macys.com"},
    {"name": "Nordstrom", "domain": "nordstrom.com", "search_pattern": "{brand}+site:nordstrom.com"},
    {"name": "Kohl's", "domain": "kohls.com", "search_pattern": "{brand}+site:kohls.com"},
    {"name": "Dick's Sporting Goods", "domain": "dickssportinggoods.com", "search_pattern": "{brand}+site:dickssportinggoods.com"},
    {"name": "REI", "domain": "rei.com", "search_pattern": "{brand}+site:rei.com"},
    {"name": "Kroger", "domain": "kroger.com", "search_pattern": "{brand}+site:kroger.com"},
    {"name": "Safeway", "domain": "safeway.com", "search_pattern": "{brand}+site:safeway.com"},
    {"name": "Albertsons", "domain": "albertsons.com", "search_pattern": "{brand}+site:albertsons.com"},
    {"name": "Whole Foods", "domain": "wholefoodsmarket.com", "search_pattern": "{brand}+site:wholefoodsmarket.com"}
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
def check_specific_retailer(brand_name, retailer):
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
            if retailer['domain'] in url and '/p/' in url:  # Product link detected
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

# Specialized search for retailers carrying a brand
def direct_site_retailer_search(brand_name, num_retailers=10):
    retailers = []
    
    # Create progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    processed = 0
    for retailer in MAJOR_RETAILERS[:num_retailers]:  # Limit to specified number of retailers
        status_text.text(f"Checking {retailer['name']} for {brand_name} products...")
        
        result = check_specific_retailer(brand_name, retailer)
        if result:
            retailers.append(result)
        
        processed += 1
        progress_bar.progress(processed / len(MAJOR_RETAILERS[:num_retailers]))
    
    progress_bar.progress(1.0)
    status_text.text(f"Found {len(retailers)} retailers carrying {brand_name}")
    
    return retailers

# Function to search for "where to buy" pages
def find_where_to_buy_page(brand_name):
    retailers = []
    
    # Try to identify if this is a URL or brand name
    if '.' in brand_name:
        domain = extract_domain(brand_name)
        # If URL, try to extract brand name
        extracted_brand = extract_brand_from_url(brand_name)
        # Use both for searching
        original_brand = brand_name
        brand_name = extracted_brand
        
        # Try direct where to buy page
        try:
            # Normalize URL
            if not original_brand.startswith(('http://', 'https://')):
                original_brand = 'https://' + original_brand
                
            # Try common where to buy URL patterns
            possible_urls = [
                f"{original_brand}/pages/where-to-buy",
                f"{original_brand}/where-to-buy",
                f"{original_brand}/stores",
                f"{original_brand}/retailers",
                f"{original_brand}/find-a-store",
                f"{original_brand}/store-locator"
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
                except:
                    continue
        except:
            pass
    
    # Search for where to buy pages
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

# Function to use precise retailer search
def find_retailers_for_brand_precise(brand_name, num_retailers=10, include_where_to_buy=True):
    all_retailers = []
    
    # Try direct retailer searches
    direct_retailers = direct_site_retailer_search(brand_name, num_retailers)
    all_retailers.extend(direct_retailers)
    
    # Try to find where-to-buy pages if requested
    if include_where_to_buy:
        where_to_buy_retailers = find_where_to_buy_page(brand_name)
        
        # Add new retailers (avoid duplicates)
        existing_domains = set(r['Domain'] for r in all_retailers)
        for retailer in where_to_buy_retailers:
            if retailer['Domain'] not in existing_domains:
                all_retailers.append(retailer)
                existing_domains.add(retailer['Domain'])
    
    return all_retailers

# Function to process brands with multiple approaches
def process_brand_retailers(brand_name, include_where_to_buy=True, num_retailers=10):
    # Check if input is a URL and extract brand if so
    original_input = brand_name
    if '.' in brand_name and '/' in brand_name:
        domain = extract_domain(brand_name)
        extracted_brand = extract_brand_from_url(brand_name)
        if extracted_brand:
            st.info(f"Detected URL input. Searching for retailers that carry: {extracted_brand} (from {domain})")
            # Keep original input for possible direct URL checks
            brand_name = extracted_brand
    
    # Start with precise retailer search
    retailers = find_retailers_for_brand_precise(brand_name, num_retailers, include_where_to_buy)
    
    # If no results and input was URL, try again with domain
    if not retailers and '.' in original_input:
        domain = extract_domain(original_input)
        st.info(f"No results found with extracted brand name. Trying domain: {domain}")
        retailers = find_retailers_for_brand_precise(domain, num_retailers, include_where_to_buy)
    
    # Create DataFrame
    if retailers:
        df = pd.DataFrame(retailers)
        st.success(f"Found {len(retailers)} retailers carrying {brand_name}")
    else:
        df = pd.DataFrame(columns=['Brand', 'Retailer', 'Domain', 'Product', 'Price', 'Search_Source', 'Link', 'Retailer_Confidence'])
        st.warning(f"No retailers found for {brand_name}. Try a different search term or brand name.")
    
    return df

# Function to process multiple brands
def process_multiple_brands(brands, include_where_to_buy=True, num_retailers=10):
    all_results = []
    
    progress_outer = st.progress(0)
    brand_status = st.empty()
    
    for i, brand in enumerate(brands):
        brand_status.text(f"Processing brand {i+1}/{len(brands)}: {brand}")
        
        # Process each brand
        brand_results = process_brand_retailers(brand, include_where_to_buy, num_retailers)
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
    
    brand_name = st.text_input("Enter brand name or website", 
                              help="Enter brand name (e.g., 'Snow Cosmetics') or website URL (e.g., 'trysnow.com')")
    
    col1, col2 = st.columns(2)
    
    with col1:
        include_where_to_buy = st.checkbox("Search for 'Where to Buy' pages", value=True,
                                         help="Look for pages on the brand's website that list retailers")
    
    with col2:
        num_retailers = st.slider("Number of major retailers to check", 
                                 min_value=5, 
                                 max_value=20, 
                                 value=15,
                                 help="More retailers = more thorough but slower search")
    
    if st.button("Find Retailers", key="single_search_btn") and brand_name:
        # Add to search history
        if brand_name not in st.session_state['search_history']:
            st.session_state['search_history'].append(brand_name)
        
        # Process brand search with specialized approach
        with st.spinner(f"Searching for retailers carrying {brand_name}..."):
            results_df = process_brand_retailers(brand_name, include_where_to_buy, num_retailers)
            
            # Store results
            st.session_state['results_df'] = results_df
    
    # Show recent searches
    if st.session_state['search_history']:
        with st.expander("Recent Searches"):
            for prev_brand in st.session_state['search_history'][-5:]:  # Show only the most recent 5
                if st.button(prev_brand, key=f"history_{prev_brand}"):
                    # Search for this brand again
                    with st.spinner(f"Searching for retailers carrying {prev_brand}..."):
                        results_df = process_brand_retailers(prev_brand, include_where_to_buy, num_retailers)
                        st.session_state['results_df'] = results_df

# Tab 2: Bulk Brand Search
with tab2:
    st.header("Find Retailers for Multiple Brands")
    
    brands_text = st.text_area("Enter brand names (one per line)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        bulk_include_where_to_buy = st.checkbox("Search for 'Where to Buy' pages", 
                                               value=True, 
                                               key="bulk_wtb")
    
    with col2:
        bulk_num_retailers = st.slider("Number of major retailers to check", 
                                      min_value=5, 
                                      max_value=20, 
                                      value=10,
                                      key="bulk_retailers")
    
    # Upload CSV option
    uploaded_file = st.file_uploader("Or upload a CSV file with brand names (one column)", type="csv")
    
    if uploaded_file:
        try:
            brands_df = pd.read_csv(uploaded_file)
            # Get the first column as brand names
            brand_column = brands_df.columns[0]
            brands_list = brands_df[brand_column].dropna().tolist()
            st.write(f"Found {len(brands_list)} brands in CSV")
            
            if st.button("Process All Brands from CSV"):
                # Process multiple brands
                with st.spinner(f"Searching for retailers for {len(brands_list)} brands..."):
                    results_df = process_multiple_brands(brands_list, 
                                                        bulk_include_where_to_buy, 
                                                        bulk_num_retailers)
                    st.session_state['results_df'] = results_df
                
        except Exception as e:
            st.error(f"Error processing CSV: {str(e)}")
    
    elif st.button("Process All Brands", key="bulk_process_btn") and brands_text:
        # Split text into list of brands
        brands_list = [brand.strip() for brand in brands_text.split('\n') if brand.strip()]
        
        if brands_list:
            # Process multiple brands
            with st.spinner(f"Searching for retailers for {len(brands_list)} brands..."):
                results_df = process_multiple_brands(brands_list, 
                                                   bulk_include_where_to_buy, 
                                                   bulk_num_retailers)
                st.session_state['results_df'] = results_df
        else:
            st.warning("Please enter at least one brand name")

# Display results if available
if st.session_state['results_df'] is not None:
    if st.session_state['results_df'].empty:
        st.warning("No retailers found. Try a different search term or brand name.")
    else:
        st.header("Search Results")
        
        # Display results
        st.dataframe(st.session_state['results_df'])
        
        # Summary statistics
        st.subheader("Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Retailers Found", len(st.session_state['results_df']))
        
        with col2:
            st.metric("Unique Retailers", st.session_state['results_df']['Retailer'].nunique())
        
        with col3:
            st.metric("Brands Searched", st.session_state['results_df']['Brand'].nunique())
        
        # Download options
        st.subheader("Download Results")
        col1, col2 = st.columns(2)
        
        # Get timestamp for filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Download as CSV
        csv = st.session_state['results_df'].to_csv(index=False)
        col1.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"brand_retailers_{timestamp}.csv",
            mime="text/csv"
        )
        
        # Download as Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            st.session_state['results_df'].to_excel(writer, index=False, sheet_name='All Results')
            
            # Create a separate worksheet for each brand
            for brand in st.session_state['results_df']['Brand'].unique():
                brand_results = st.session_state['results_df'][st.session_state['results_df']['Brand'] == brand]
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
        st.experimental_rerun()
