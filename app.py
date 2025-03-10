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

# Set up page configuration
st.set_page_config(
    page_title="B2B Retailer Finder",
    page_icon="🔍",
    layout="wide"
)

# Add title and description
st.title("B2B Retailer Finder")
st.markdown("Discover retailers that carry specific brands through Google search")

# Initialize session state variables
if 'results_df' not in st.session_state:
    st.session_state['results_df'] = None

if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []

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

# Function to search for retailers that carry a brand
def find_retailers_for_brand(brand_name, search_type='shopping', num_pages=3, country='us'):
    retailers = []
    
    # Rotate user agents to avoid blocking
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
    ]
    
    # Define headers with random user agent
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Clean up brand name
    brand_query = quote_plus(brand_name)
    
    # Define search queries based on search type
    if search_type == 'shopping':
        # Google Shopping search
        base_url = f"https://www.google.com/search?q={brand_query}&tbm=shop"
        search_type_name = "Google Shopping"
    elif search_type == 'b2b':
        # B2B-focused search
        base_url = f"https://www.google.com/search?q={brand_query}+authorized+retailer+OR+distributor+OR+reseller+OR+stockist+OR+dealer"
        search_type_name = "B2B Search"
    elif search_type == 'wholesale':
        # Wholesale-focused search
        base_url = f"https://www.google.com/search?q={brand_query}+wholesale+OR+bulk+OR+b2b+OR+trade"
        search_type_name = "Wholesale Search"
    else:
        # Regular Google search
        base_url = f"https://www.google.com/search?q={brand_query}"
        search_type_name = "Regular Search"
    
    # Add country-specific parameters if needed
    if country and country.lower() != 'us':
        base_url += f"&gl={country.lower()}"

    found_domains = set()  # Track domains we've already found
    
    # Search multiple pages
    for page in range(num_pages):
        current_url = base_url
        if page > 0:
            current_url += f"&start={page * 10}"
        
        try:
            # Add a delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))
            
            # Send request
            response = requests.get(current_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                st.warning(f"Received HTTP {response.status_code} for page {page+1}. Stopping search.")
                break
            
            # Parse the page
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract search results
            if search_type == 'shopping':
                # Extract shopping results
                shopping_items = soup.find_all('div', class_=re.compile('sh-dgr__content'))
                
                for item in shopping_items:
                    # Extract merchant info
                    merchant_elem = item.find('div', class_=re.compile('merchant'))
                    if merchant_elem:
                        merchant_text = merchant_elem.text.strip()
                        merchant_link = None
                        
                        # Try to find merchant link
                        link = merchant_elem.find('a')
                        if link and 'href' in link.attrs:
                            merchant_link = link['href']
                        
                        # Extract domain if link exists
                        domain = extract_domain(merchant_link) if merchant_link else merchant_text
                        
                        # Skip if we've already found this domain
                        if domain.lower() in found_domains:
                            continue
                            
                        found_domains.add(domain.lower())
                        
                        # Find price if available
                        price_elem = item.find(text=re.compile(r'\$[\d,]+\.\d{2}'))
                        price = price_elem if price_elem else "N/A"
                        
                        # Find title if available
                        title_elem = item.find('h3')
                        title = title_elem.text.strip() if title_elem else "N/A"
                        
                        retailers.append({
                            'Brand': brand_name,
                            'Retailer': merchant_text,
                            'Domain': domain,
                            'Product': title,
                            'Price': price,
                            'Source': search_type_name,
                            'Link': merchant_link if merchant_link else ""
                        })
            else:
                # Extract regular search results
                search_results = soup.find_all('div', class_=re.compile('g'))
                
                for result in search_results:
                    # Extract title and link
                    title_elem = result.find('h3')
                    if not title_elem:
                        continue
                        
                    link_elem = result.find('a')
                    if not link_elem or 'href' not in link_elem.attrs:
                        continue
                        
                    result_link = link_elem['href']
                    if not result_link.startswith(('http://', 'https://')):
                        continue
                        
                    # Extract domain
                    domain = extract_domain(result_link)
                    
                    # Skip Google, Wikipedia, etc.
                    skip_domains = ['google.', 'wikipedia.', 'facebook.', 'instagram.', 'twitter.', 
                                   'linkedin.', 'youtube.', 'amazon.', 'ebay.']
                    if any(skip in domain.lower() for skip in skip_domains) or domain.lower() in found_domains:
                        continue
                        
                    found_domains.add(domain.lower())
                    
                    # Extract snippet
                    snippet_elem = result.find('div', class_=re.compile('VwiC3b'))
                    snippet = snippet_elem.text.strip() if snippet_elem else "N/A"
                    
                    # Check if snippet suggests this is a retailer
                    retailer_signals = ['buy', 'shop', 'purchase', 'order', 'price', 'retailer', 'store', 
                                        'distributor', 'dealer', 'authorized', 'official', 'stockist', 
                                        'reseller', 'wholesale', 'supplier']
                    
                    is_likely_retailer = any(signal in snippet.lower() for signal in retailer_signals)
                    retailer_confidence = "High" if is_likely_retailer else "Medium"
                    
                    retailers.append({
                        'Brand': brand_name,
                        'Retailer': title_elem.text.strip(),
                        'Domain': domain,
                        'Product': "N/A",
                        'Price': "N/A",
                        'Source': search_type_name,
                        'Link': result_link,
                        'Retailer Confidence': retailer_confidence
                    })
        
        except Exception as e:
            st.error(f"Error searching page {page+1}: {str(e)}")
            break
    
    return retailers

# Function to process a brand with multiple search types in parallel
def process_brand_searches(brand_name, search_types, num_pages=3, country='us'):
    all_retailers = []
    
    # Create a progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_searches = len(search_types)
    
    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, total_searches)) as executor:
        future_to_search = {executor.submit(find_retailers_for_brand, brand_name, search_type, num_pages, country): search_type 
                           for search_type in search_types}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_search):
            search_type = future_to_search[future]
            try:
                retailers = future.result()
                all_retailers.extend(retailers)
                
                completed += 1
                progress = completed / total_searches
                progress_bar.progress(progress)
                status_text.text(f"Completed {search_type} search ({completed}/{total_searches})")
                
            except Exception as e:
                st.error(f"Error in {search_type} search: {str(e)}")
                completed += 1
                progress = completed / total_searches
                progress_bar.progress(progress)
    
    # Remove duplicates (same domain for same brand)
    unique_retailers = []
    seen_domains = set()
    
    for retailer in all_retailers:
        if (retailer['Brand'], retailer['Domain'].lower()) not in seen_domains:
            seen_domains.add((retailer['Brand'], retailer['Domain'].lower()))
            unique_retailers.append(retailer)
    
    # Create DataFrame
    df = pd.DataFrame(unique_retailers)
    
    # Complete
    progress_bar.progress(1.0)
    status_text.text(f"Found {len(unique_retailers)} unique retailers for {brand_name}")
    
    return df

# Function to process multiple brands
def process_multiple_brands(brands, search_types, num_pages=3, country='us'):
    all_results = []
    
    progress_outer = st.progress(0)
    brand_status = st.empty()
    
    for i, brand in enumerate(brands):
        brand_status.text(f"Processing brand {i+1}/{len(brands)}: {brand}")
        
        # Process each brand
        brand_results = process_brand_searches(brand, search_types, num_pages, country)
        all_results.append(brand_results)
        
        # Update progress
        progress_outer.progress((i + 1) / len(brands))
    
    # Combine results
    combined_results = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
    
    # Complete
    progress_outer.progress(1.0)
    brand_status.text(f"Completed processing {len(brands)} brands")
    
    return combined_results

# Main app layout with tabs
tab1, tab2 = st.tabs(["Search by Brand", "Bulk Brand Search"])

# Tab 1: Single Brand Search
with tab1:
    st.header("Find Retailers for a Brand")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        brand_name = st.text_input("Enter brand name", help="Enter the exact brand name you want to find retailers for")
    
    with col2:
        country = st.selectbox("Country", 
                               options=["US", "UK", "CA", "AU", "DE", "FR", "IT", "ES", "JP"], 
                               help="Select country for localized results")
    
    # Search options
    st.subheader("Search Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        search_types = st.multiselect(
            "Search methods", 
            options=["shopping", "b2b", "wholesale", "regular"],
            default=["shopping", "b2b"],
            help="Select search methods to find retailers"
        )
        
    with col2:
        num_pages = st.slider(
            "Number of pages to search", 
            min_value=1, 
            max_value=10,
            value=3,
            help="More pages = more results but slower search"
        )
    
    if st.button("Find Retailers", key="single_search_btn") and brand_name:
        # Add to search history
        if brand_name not in st.session_state['search_history']:
            st.session_state['search_history'].append(brand_name)
        
        # Process brand search
        results_df = process_brand_searches(brand_name, search_types, num_pages, country.lower())
        
        # Store results
        st.session_state['results_df'] = results_df
    
    # Show recent searches
    if st.session_state['search_history']:
        with st.expander("Recent Searches"):
            for prev_brand in st.session_state['search_history']:
                if st.button(prev_brand, key=f"history_{prev_brand}"):
                    # Search for this brand again
                    results_df = process_brand_searches(prev_brand, search_types, num_pages, country.lower())
                    st.session_state['results_df'] = results_df

# Tab 2: Bulk Brand Search
with tab2:
    st.header("Find Retailers for Multiple Brands")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        brands_text = st.text_area("Enter brand names (one per line)")
    
    with col2:
        bulk_country = st.selectbox("Country", 
                                   options=["US", "UK", "CA", "AU", "DE", "FR", "IT", "ES", "JP"],
                                   key="bulk_country")
        
        bulk_search_types = st.multiselect(
            "Search methods", 
            options=["shopping", "b2b", "wholesale", "regular"],
            default=["shopping", "b2b"],
            key="bulk_search_types"
        )
        
        bulk_num_pages = st.slider(
            "Pages per search", 
            min_value=1, 
            max_value=5,
            value=2,
            key="bulk_pages"
        )
    
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
                results_df = process_multiple_brands(brands_list, bulk_search_types, bulk_num_pages, bulk_country.lower())
                st.session_state['results_df'] = results_df
                
        except Exception as e:
            st.error(f"Error processing CSV: {str(e)}")
    
    elif st.button("Process All Brands", key="bulk_process_btn") and brands_text:
        # Split text into list of brands
        brands_list = [brand.strip() for brand in brands_text.split('\n') if brand.strip()]
        
        if brands_list:
            # Process multiple brands
            results_df = process_multiple_brands(brands_list, bulk_search_types, bulk_num_pages, bulk_country.lower())
            st.session_state['results_df'] = results_df
        else:
            st.warning("Please enter at least one brand name")

# Display results if available (shared between tabs)
if st.session_state['results_df'] is not None and not st.session_state['results_df'].empty:
    st.header("Search Results")
    
    # Filter options
    with st.expander("Filter Results"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Get list of brands in results
            brands_in_results = st.session_state['results_df']['Brand'].unique().tolist()
            selected_brands = st.multiselect("Filter by brand", options=brands_in_results, default=brands_in_results)
        
        with col2:
            # Get list of search sources in results
            sources_in_results = st.session_state['results_df']['Source'].unique().tolist()
            selected_sources = st.multiselect("Filter by source", options=sources_in_results, default=sources_in_results)
    
        # Apply filters
        filtered_df = st.session_state['results_df']
        
        if selected_brands:
            filtered_df = filtered_df[filtered_df['Brand'].isin(selected_brands)]
            
        if selected_sources:
            filtered_df = filtered_df[filtered_df['Source'].isin(selected_sources)]
    
    # Display results
    st.dataframe(filtered_df)
    
    # Summary statistics
    st.subheader("Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Retailers Found", len(filtered_df))
    
    with col2:
        st.metric("Unique Domains", filtered_df['Domain'].nunique())
    
    with col3:
        st.metric("Brands Searched", filtered_df['Brand'].nunique())
    
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
        
        # Create a pivot table summary
        summary_df = pd.pivot_table(
            filtered_df,
            index='Brand',
            columns='Source',
            values='Domain',
            aggfunc='count',
            fill_value=0
        )
        
        summary_df.to_excel(writer, sheet_name='Summary')
        
        # Create a separate worksheet for each brand
        for brand in filtered_df['Brand'].unique():
            brand_results = filtered_df[filtered_df['Brand'] == brand]
            # Clean brand name for worksheet name (Excel has a 31 char limit and restricts certain chars)
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

# Help section
with st.expander("Help & Information"):
    st.write("""
    ### About This App
    
    This app helps you discover retailers that carry specific brands by searching Google:
    
    - **Google Shopping Search**: Finds retailers that sell products from the brand in Google Shopping results
    - **B2B Search**: Specifically targets authorized retailers, distributors, and resellers
    - **Wholesale Search**: Looks for wholesale and B2B relationships with the brand
    - **Regular Search**: Basic Google search results that might reveal retailer relationships
    
    ### How It Works
    
    1. Enter a brand name (or multiple brands)
    2. Select which types of searches to perform
    3. Choose how many pages of results to analyze
    4. The app searches Google using specialized queries to find retailers
    5. Results are compiled, deduplicated, and presented for download
    
    ### Tips for Best Results
    
    - Use the brand's official name rather than variations
    - Include multiple search types for more comprehensive results
    - More pages will yield more results but may take longer
    - The Excel export includes a summary tab and separate sheets for each brand
    - Retailer confidence is a rough estimate of how likely the result is a legitimate retailer
    
    ### Limitations
    
    - Some results may include false positives
    - This tool cannot access retailers behind login screens
    - Google may block searches if too many are performed rapidly
    - Not all B2B relationships will be discoverable via public web searches
    """)
