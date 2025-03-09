import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from collections import Counter
import re
from urllib.parse import urlparse, quote_plus
import concurrent.futures
import time
import io
import random
import json
import datetime

# Set up page configuration
st.set_page_config(
    page_title="Retailer Brand Validator",
    page_icon="🔍",
    layout="wide"
)

# Add title and description
st.title("Retailer Brand Validator")
st.markdown("Validate retailers and extract keywords to confirm if they stock specific brands")

# Define a simple list of stopwords
english_stopwords = set(['and', 'the', 'for', 'with', 'that', 'this', 'you', 'your', 'our', 'from', 
             'have', 'has', 'are', 'not', 'when', 'what', 'where', 'why', 'how', 'all',
             'been', 'being', 'both', 'but', 'by', 'can', 'could', 'did', 'do', 'does',
             'doing', 'down', 'each', 'few', 'more', 'most', 'off', 'on', 'once', 'only',
             'own', 'same', 'should', 'so', 'some', 'such', 'than', 'too', 'very', 'will'])

# Initialize session state variables
if 'results_df' not in st.session_state:
    st.session_state['results_df'] = None

if 'bulk_brands_df' not in st.session_state:
    st.session_state['bulk_brands_df'] = None

# Function to normalize URLs
def normalize_url(url):
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

# Function to check if retailer is valid through Google Shopping
def validate_retailer_with_brand(retailer_url, brand_name, max_retries=2):
    try:
        # Normalize the URL to get domain
        domain = normalize_url(retailer_url)
        base_domain = domain.split('.')[0]  # Get the main part of the domain
        
        # Construct Google Shopping search query
        search_query = f"{brand_name} site:{domain}"
        encoded_query = quote_plus(search_query)
        google_shopping_url = f"https://www.google.com/search?q={encoded_query}&tbm=shop"
        
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
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Try Google Shopping search first
        google_results_found = False
        for attempt in range(max_retries):
            try:
                response = requests.get(google_shopping_url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check if there are any shopping results
                shopping_results = soup.find_all('div', class_=re.compile('sh-dgr__content'))
                if shopping_results:
                    google_results_found = True
                    break
                    
                # Check for "no results" message
                no_results = soup.find_all(text=re.compile('No results found', re.I))
                if no_results:
                    return False, f"No Google Shopping results found for {brand_name} on {domain}"
                
                time.sleep(1)
            except requests.exceptions.RequestException:
                time.sleep(1)
                continue
        
        # If Google Shopping showed results, verify by checking the retailer's website directly
        if google_results_found:
            # Now verify by checking the retailer's website directly
            retailer_url = f"https://{domain}/search?q={quote_plus(brand_name)}"
            
            for attempt in range(max_retries):
                try:
                    response = requests.get(retailer_url, headers=headers, timeout=15)
                    
                    # If we get a successful response
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Check if brand name appears in the page
                        brand_pattern = re.compile(re.escape(brand_name), re.I)
                        brand_mentions = soup.find_all(text=brand_pattern)
                        
                        if brand_mentions:
                            return True, f"Confirmed: {domain} has {brand_name} products (found on website)"
                        else:
                            # Check title and meta description as fallback
                            if soup.title and brand_pattern.search(soup.title.text):
                                return True, f"Likely: {domain} may carry {brand_name} (found in page title)"
                    
                    # Try fallback URL - just the domain homepage
                    fallback_url = f"https://{domain}"
                    response = requests.get(fallback_url, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for brand mentions in homepage
                        brand_pattern = re.compile(re.escape(brand_name), re.I)
                        brand_mentions = soup.find_all(text=brand_pattern)
                        
                        if brand_mentions:
                            return True, f"Possible: {domain} mentions {brand_name} on their homepage"
                    
                    return False, f"Uncertain: {domain} may not stock {brand_name} (not found on website)"
                        
                except requests.exceptions.RequestException:
                    if attempt == max_retries - 1:
                        return False, f"Could not verify {domain} - connection failed"
                    time.sleep(1)
        
        # Fallback: check regular Google search as a last resort
        google_search_url = f"https://www.google.com/search?q={encoded_query}"
        
        try:
            response = requests.get(google_search_url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if there are any search results containing both the brand and domain
            search_results = soup.find_all('div', class_='g')
            
            for result in search_results:
                result_text = result.text.lower()
                if brand_name.lower() in result_text and domain.lower() in result_text:
                    return True, f"Possibly valid: {domain} appears in Google results for {brand_name}"
        except:
            pass
            
        return False, f"Unverified: Could not confirm if {domain} stocks {brand_name}"
            
    except Exception as e:
        return False, f"Error validating retailer: {str(e)}"

# Function to extract keywords from a website with enhanced search capabilities
def extract_keywords_from_website(url, brand_name=None, retries=3):
    try:
        # Normalize URL
        domain = normalize_url(url)
        
        # Add http:// prefix if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

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
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Enhanced retry mechanism
        success = False
        error_msg = ""
        
        for attempt in range(retries):
            try:
                # Fetch the website with a timeout
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                success = True
                break
            except requests.exceptions.RequestException as e:
                error_msg = str(e)
                # Wait before retrying
                time.sleep(1 * (attempt + 1))
        
        if not success:
            return f"Error: {error_msg}"
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract keywords from different sources
        keywords = []
        
        # 1. Enhanced meta tag extraction (including OpenGraph and Twitter tags)
        for meta in soup.find_all('meta'):
            # Meta keywords
            if meta.get('name') == 'keywords' and meta.get('content'):
                keywords.extend([k.strip().lower() for k in meta.get('content').split(',')])
            
            # Meta description
            if meta.get('name') == 'description' and meta.get('content'):
                desc_words = re.findall(r'\b\w+\b', meta.get('content').lower())
                keywords.extend([word for word in desc_words if len(word) > 3])
                
            # OpenGraph tags
            if meta.get('property') and 'og:' in meta.get('property') and meta.get('content'):
                if 'title' in meta.get('property') or 'description' in meta.get('property'):
                    og_words = re.findall(r'\b\w+\b', meta.get('content').lower())
                    keywords.extend([word for word in og_words if len(word) > 3])
        
        # 2. Title tags
        if soup.title:
            title_words = re.findall(r'\b\w+\b', soup.title.text.lower())
            keywords.extend([word for word in title_words if len(word) > 3])
        
        # 3. Heading tags with priority (h1, h2, h3)
        for i, heading_tag in enumerate(['h1', 'h2', 'h3']):
            # Give more weight to h1 than h2, and h2 more than h3
            weight = 3 - i
            for heading in soup.find_all(heading_tag):
                heading_words = re.findall(r'\b\w+\b', heading.text.lower())
                filtered_words = [word for word in heading_words if len(word) > 3]
                # Add words multiple times based on weight
                keywords.extend(filtered_words * weight)
        
        # 4. Enhanced content extraction
        content_tags = ['article', 'main', 'section', 'div']
        content_classes = ['content', 'post', 'entry', 'article', 'main', 'blog', 'product']
        
        # Look for content in semantic tags first
        for tag in content_tags[:3]:  # article, main, section
            for content in soup.find_all(tag):
                content_words = re.findall(r'\b\w+\b', content.text.lower())
                keywords.extend([word for word in content_words if len(word) > 3])
        
        # Look for content in divs with specific classes
        for cls in content_classes:
            for content in soup.find_all('div', class_=re.compile(cls, re.I)):
                content_words = re.findall(r'\b\w+\b', content.text.lower())
                keywords.extend([word for word in content_words if len(word) > 3])
                
        # 5. Enhanced tag extraction
        # Look for tags in multiple places with various patterns
        tag_patterns = ['tag', 'category', 'topic', 'keyword', 'subject', 'label', 'brand']
        
        # Check for elements with tag-related classes
        for pattern in tag_patterns:
            # Class contains pattern
            for tag in soup.find_all(class_=re.compile(pattern, re.I)):
                tag_text = tag.text.strip().lower()
                if tag_text and len(tag_text) > 2:
                    # Add tag multiple times to increase weight
                    keywords.extend([tag_text] * 3)  
            
            # ID contains pattern
            for tag in soup.find_all(id=re.compile(pattern, re.I)):
                tag_text = tag.text.strip().lower()
                if tag_text and len(tag_text) > 2:
                    keywords.extend([tag_text] * 3)
        
        # 6. Check for tags in URLs
        tag_url_patterns = [
            r'(?:tag|tags)[=/]([^/&?#]+)',
            r'(?:category|categories)[=/]([^/&?#]+)',
            r'(?:topic|topics)[=/]([^/&?#]+)',
            r'(?:keyword|keywords)[=/]([^/&?#]+)',
            r'(?:brand|brands)[=/]([^/&?#]+)'
        ]
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            for pattern in tag_url_patterns:
                match = re.search(pattern, href)
                if match:
                    tag = match.group(1).replace('-', ' ').replace('_', ' ').replace('+', ' ').lower()
                    # Add URL tags with higher weight
                    keywords.extend([tag] * 2)
        
        # Count occurrences of each keyword
        keyword_counter = Counter(keywords)
        
        # Remove common English stop words and short words
        for word in list(keyword_counter.keys()):
            if word in english_stopwords or len(word) <= 2:
                del keyword_counter[word]
        
        # Get the 10 most common keywords
        most_common = keyword_counter.most_common(10)
        
        # Format as a string: "keyword1, keyword2, keyword3, ..."
        if most_common:
            return ', '.join([f"{k}" for k, _ in most_common])
        else:
            return "No keywords found"
            
    except Exception as e:
        return f"Error: {str(e)}"

# Function to process websites with brand validation
def process_websites_with_brand_validation(websites, brand_name):
    # Create a progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(websites)
    results = []
    
    # Determine the number of workers
    max_workers = min(8, total)  # Limit to max 8 workers to avoid being blocked
    
    # Show status
    status_text.text(f"Processing {total} websites...")
    
    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # First validate the retailers through Google
        future_to_url = {executor.submit(validate_retailer_with_brand, url, brand_name): url for url in websites}
        
        validation_results = {}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
            url = future_to_url[future]
            try:
                is_valid, validation_message = future.result()
                validation_results[url] = {
                    'is_valid': is_valid,
                    'validation_message': validation_message
                }
            except Exception as e:
                validation_results[url] = {
                    'is_valid': False,
                    'validation_message': f"Error during validation: {str(e)}"
                }
            
            # Update progress
            progress = (i + 1) / (total * 2)  # First half for validation
            progress_bar.progress(progress)
            status_text.text(f"Validating retailers: {i+1}/{total} ({int(progress*100)}%)")
    
        # Now extract keywords from validated retailers
        i = 0
        future_to_url = {}
        
        # Only process sites that were validated or we couldn't determine
        for url, validation in validation_results.items():
            if validation['is_valid'] or "unverified" in validation['validation_message'].lower():
                future = executor.submit(extract_keywords_from_website, url, brand_name)
                future_to_url[future] = url
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
            url = future_to_url[future]
            try:
                keywords = future.result()
                
                # Determine if brand appears in keywords
                brand_in_keywords = brand_name.lower() in keywords.lower()
                
                # Add to results
                results.append({
                    'Website': url,
                    'Brand': brand_name,
                    'Status': "Valid" if validation_results[url]['is_valid'] else "Unverified",
                    'Validation Message': validation_results[url]['validation_message'],
                    'Top Keywords': keywords,
                    'Brand Found in Keywords': "Yes" if brand_in_keywords else "No"
                })
            except Exception as e:
                results.append({
                    'Website': url,
                    'Brand': brand_name,
                    'Status': "Error",
                    'Validation Message': validation_results[url]['validation_message'],
                    'Top Keywords': f"Error: {str(e)}",
                    'Brand Found in Keywords': "No"
                })
            
            # Update progress for second half
            progress = 0.5 + ((i + 1) / (len(future_to_url) * 2))
            progress_bar.progress(progress)
            status_text.text(f"Extracting keywords: {i+1}/{len(future_to_url)} ({int(progress*100)}%)")
    
    # Add all invalid retailers to the results
    for url, validation in validation_results.items():
        if not validation['is_valid'] and "unverified" not in validation['validation_message'].lower():
            # Skip if already added
            if not any(r['Website'] == url for r in results):
                results.append({
                    'Website': url,
                    'Brand': brand_name,
                    'Status': "Invalid",
                    'Validation Message': validation['validation_message'],
                    'Top Keywords': "Not processed - invalid retailer",
                    'Brand Found in Keywords': "No"
                })
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Sort by validation status
    df['Sort Order'] = df['Status'].map({'Valid': 0, 'Unverified': 1, 'Invalid': 2, 'Error': 3})
    df = df.sort_values('Sort Order').drop('Sort Order', axis=1)
    
    # Complete
    progress_bar.progress(1.0)
    status_text.text(f"Completed processing {total} websites!")
    
    return df

# Function to process bulk brands and retailers
def process_bulk_validation(brands_df):
    # Create a progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_results = []
    total_combinations = len(brands_df)
    processed = 0
    
    # Process each brand-retailer combination
    for index, row in brands_df.iterrows():
        try:
            brand_name = row['Brand']
            retailer_url = row['Retailer']
            
            status_text.text(f"Processing {brand_name} at {retailer_url}... ({processed}/{total_combinations})")
            
            # Validate retailer with brand
            is_valid, validation_message = validate_retailer_with_brand(retailer_url, brand_name)
            
            # Extract keywords if valid or unverified
            if is_valid or "unverified" in validation_message.lower():
                keywords = extract_keywords_from_website(retailer_url, brand_name)
                brand_in_keywords = brand_name.lower() in keywords.lower()
            else:
                keywords = "Not processed - invalid retailer"
                brand_in_keywords = False
            
            # Add to results
            all_results.append({
                'Website': retailer_url,
                'Brand': brand_name,
                'Status': "Valid" if is_valid else ("Unverified" if "unverified" in validation_message.lower() else "Invalid"),
                'Validation Message': validation_message,
                'Top Keywords': keywords,
                'Brand Found in Keywords': "Yes" if brand_in_keywords else "No"
            })
            
            # Update progress
            processed += 1
            progress_bar.progress(processed / total_combinations)
        
        except Exception as e:
            all_results.append({
                'Website': row['Retailer'],
                'Brand': row['Brand'],
                'Status': "Error",
                'Validation Message': f"Error during processing: {str(e)}",
                'Top Keywords': "Error occurred",
                'Brand Found in Keywords': "No"
            })
            
            processed += 1
            progress_bar.progress(processed / total_combinations)
    
    # Create DataFrame
    df = pd.DataFrame(all_results)
    
    # Sort by validation status
    df['Sort Order'] = df['Status'].map({'Valid': 0, 'Unverified': 1, 'Invalid': 2, 'Error': 3})
    df = df.sort_values(['Brand', 'Sort Order']).drop('Sort Order', axis=1)
    
    # Complete
    progress_bar.progress(1.0)
    status_text.text(f"Completed processing {total_combinations} brand-retailer combinations!")
    
    return df

# Function to validate a single brand-retailer combination
def validate_single_combination(retailer_url, brand_name):
    st.info(f"Validating {brand_name} at {retailer_url}...")
    
    # Validate retailer with brand
    is_valid, validation_message = validate_retailer_with_brand(retailer_url, brand_name)
    
    # Extract keywords if valid or unverified
    if is_valid or "unverified" in validation_message.lower():
        keywords = extract_keywords_from_website(retailer_url, brand_name)
        brand_in_keywords = brand_name.lower() in keywords.lower()
    else:
        keywords = "Not processed - invalid retailer"
        brand_in_keywords = False
    
    # Create result
    result = {
        'Website': retailer_url,
        'Brand': brand_name,
        'Status': "Valid" if is_valid else ("Unverified" if "unverified" in validation_message.lower() else "Invalid"),
        'Validation Message': validation_message,
        'Top Keywords': keywords,
        'Brand Found in Keywords': "Yes" if brand_in_keywords else "No"
    }
    
    # Display result
    status_color = "green" if is_valid else ("blue" if "unverified" in validation_message.lower() else "red")
    
    st.markdown(f"### Status: <span style='color:{status_color}'>{result['Status']}</span>", unsafe_allow_html=True)
    st.write(f"**Validation Result:** {result['Validation Message']}")
    
    if keywords != "Not processed - invalid retailer":
        st.write(f"**Top Keywords:** {keywords}")
        st.write(f"**Brand Found in Keywords:** {result['Brand Found in Keywords']}")
    
    # Return as DataFrame (single row)
    return pd.DataFrame([result])

# Main app layout with tabs
tab1, tab2, tab3 = st.tabs(["Bulk Validation", "Single Validation", "Bulk Brand-Retailer Pairs"])

# Tab 1: Bulk Validation (Multiple retailers, one brand)
with tab1:
    st.header("Validate Multiple Retailers for a Brand")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader("Upload a CSV or text file with retailer URLs (one per line)", 
                                         type=["csv", "txt"], key="bulk_upload")
    
    with col2:
        brand_name = st.text_input("Enter brand name to validate")
    
    if uploaded_file is not None and brand_name:
        try:
            # Process the uploaded file
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            if file_extension == 'csv':
                # Read the CSV file
                df = pd.read_csv(uploaded_file)
                
                # Look for URL columns
                url_columns = [col for col in df.columns if any(kw in col.lower() for kw in ['url', 'website', 'site', 'link', 'domain'])]
                
                if url_columns:
                    url_column = st.selectbox("Select the column containing retailer URLs:", url_columns, key="bulk_url_col")
                else:
                    url_column = st.selectbox("Select the column containing retailer URLs:", df.columns, key="bulk_any_col")
                
                # Get the website URLs
                websites = df[url_column].dropna().tolist()
            else:
                # Read as text file
                content = uploaded_file.getvalue().decode("utf-8")
                websites = [line.strip() for line in content.split('\n') if line.strip()]
            
            st.write(f"Found {len(websites)} websites to validate for brand: {brand_name}")
            
            # Show a sample
            if len(websites) > 5:
                with st.expander("View sample websites"):
                    st.write(websites[:10])
            else:
                st.write("Websites:", websites)
            
            # Process button
            if st.button(f"Validate Retailers for {brand_name}", key="bulk_validate_btn"):
                # Process websites and get results
                st.session_state['results_df'] = process_websites_with_brand_validation(websites, brand_name)
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)
    elif uploaded_file and not brand_name:
        st.warning("Please enter a brand name to validate retailers.")
    elif brand_name and not uploaded_file:
        st.info("Please upload a file with retailer URLs.")

# Tab 2: Single Validation (One retailer, one brand)
with tab2:
    st.header("Validate a Single Retailer for a Brand")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        single_retailer = st.text_input("Enter retailer website URL")
    
    with col2:
        single_brand = st.text_input("Enter brand name")
    
    if st.button("Validate Single Combination", key="single_validate_btn") and single_retailer and single_brand:
        try:
            # Validate the single combination
            single_result_df = validate_single_combination(single_retailer, single_brand)
            
            # Store result for download
            if 'results_df' not in st.session_state or st.session_state['results_df'] is None:
                st.session_state['results_df'] = single_result_df
            else:
                st.session_state['results_df'] = pd.concat([st.session_state['results_df'], single_result_df], ignore_index=True)
            
            # Download single result
            st.subheader("Download Result")
            
            # Download as CSV
            csv = single_result_df.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name=f"{single_brand}_{normalize_url(single_retailer)}_validation.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"Error processing: {str(e)}")
    elif (single_retailer or single_brand) and not (single_retailer and single_brand):
        st.warning("Please enter both a retailer URL and a brand name.")

# Tab 3: Bulk Brand-Retailer Pairs (Multiple retailers, multiple brands in CSV)
with tab3:
    st.header("Validate Multiple Brand-Retailer Pairs")
    
    # Upload CSV with brand-retailer pairs
    bulk_pairs_file = st.file_uploader("Upload CSV with Brand and Retailer columns", 
                                       type=["csv"], key="bulk_pairs_upload")
    
    if bulk_pairs_file is not None:
        try:
            # Read the CSV file
            pairs_df = pd.read_csv(bulk_pairs_file)
            
            # Check if required columns exist
            required_cols = ['Brand', 'Retailer']
            
            # If columns with exact names don't exist, try to map
            if not all(col in pairs_df.columns for col in required_cols):
                # Look for Brand-like columns
                brand_cols = [col for col in pairs_df.columns if 'brand' in col.lower()]
                retailer_cols = [col for col in pairs_df.columns if any(kw in col.lower() for kw in ['retailer', 'url', 'website', 'site', 'domain'])]
                
                col_mapping = {}
                
                if brand_cols:
                    brand_col = st.selectbox("Select the column containing brand names:", brand_cols, key="bulk_pairs_brand_col")
                    col_mapping['Brand'] = brand_col
                else:
                    brand_col = st.selectbox("Select the column containing brand names:", pairs_df.columns, key="bulk_pairs_any_brand")
                    col_mapping['Brand'] = brand_col
                
                if retailer_cols:
                    retailer_col = st.selectbox("Select the column containing retailer URLs:", retailer_cols, key="bulk_pairs_ret_col")
                    col_mapping['Retailer'] = retailer_col
                else:
                    retailer_col = st.selectbox("Select the column containing retailer URLs:", pairs_df.columns, key="bulk_pairs_any_ret")
                    col_mapping['Retailer'] = retailer_col
                
                # Rename columns
                pairs_df = pairs_df.rename(columns=col_mapping)
            
            # Now check if we have the required columns
            if all(col in pairs_df.columns for col in required_cols):
                # Clean data
                pairs_df = pairs_df[required_cols].dropna()
                
                # Display found combinations
                st.write(f"Found {len(pairs_df)} brand-retailer combinations to validate")
                
                # Show a sample
                if len(pairs_df) > 5:
                    with st.expander("View sample combinations"):
                        st.dataframe(pairs_df.head(10))
                else:
                    st.dataframe(pairs_df)
                
                # Store for later processing
                st.session_state['bulk_brands_df'] = pairs_df
                
                # Process button
                if st.button("Validate All Brand-Retailer Pairs", key="bulk_pairs_btn"):
                    # Process brands and retailers
                    st.session_state['results_df'] = process_bulk_validation(st.session_state['bulk_brands_df'])
            else:
                st.error("Could not identify required columns. Please ensure your CSV has 'Brand' and 'Retailer' columns.")
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)

# Display results if available (shared between tabs)
if st.session_state['results_df'] is not None:
    st.header("Validation Results")
    
    # Get unique brands in results
    brands = st.session_state['results_df']['Brand'].unique()
    
    # For each brand, show results
    for brand in brands:
        brand_results = st.session_state['results_df'][st.session_state['results_df']['Brand'] == brand]
        
        # Create expander for each brand
        with st.expander(f"Results for {brand} ({len(brand_results)} retailers)", expanded=len(brands) == 1):
            # Display valid retailers first
            valid_retailers = brand_results[brand_results['Status'] == 'Valid']
            if not valid_retailers.empty:
                st.success(f"Found {len(valid_retailers)} valid retailers for {brand}")
                st.dataframe(valid_retailers)
            else:
                st.warning(f"No confirmed valid retailers found for {brand}")
            
            # Display unverified retailers
            unverified_retailers = brand_results[brand_results['Status'] == 'Unverified']
            if not unverified_retailers.empty:
                st.info(f"{len(unverified_retailers)} retailers could not be definitively verified")
                with st.expander("View unverified retailers"):
                    st.dataframe(unverified_retailers)
            
            # Display invalid retailers
            invalid_retailers = brand_results[brand_results['Status'] == 'Invalid']
            if not invalid_retailers.empty:
                with st.expander(f"View {len(invalid_retailers)} invalid retailers"):
                    st.dataframe(invalid_retailers)
    
    # Download options
    st.subheader("Download All Results")
    col1, col2 = st.columns(2)
    
    # Get timestamp for filenames
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Download as CSV
    csv = st.session_state['results_df'].to_csv(index=False)
    col1.download_button(
        label="Download as CSV",
        data=csv,
        file_name=f"brand_retailer_validation_{timestamp}.csv",
        mime="text/csv"
    )
    
    # Download as Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        st.session_state['results_df'].to_excel(writer, index=False, sheet_name='Validation Results')
        
        # Create a separate worksheet for each brand
        for brand in brands:
            brand_results = st.session_state['results_df'][st.session_state['results_df']['Brand'] == brand]
            # Clean brand name for worksheet name (Excel has a 31 char limit and restricts certain chars)
            sheet_name = brand[:31].replace(':', '').replace('\\', '').replace('/', '').replace('?', '').replace('*', '').replace('[', '').replace(']', '')
            brand_results.to_excel(writer, index=False, sheet_name=sheet_name)
    
    buffer.seek(0)
    col2.download_button(
        label="Download as Excel",
        data=buffer,
        file_name=f"brand_retailer_validation_{timestamp}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Reset results button
if st.session_state['results_df'] is not None:
    if st.button("Clear All Results"):
        st.session_state['results_df'] = None
        st.session_state['bulk_brands_df'] = None
        st.experimental_rerun()

# Help section
with st.expander("Help & Information"):
    st.write("""
    ### About This App
    
    This app validates retailers for specific brands through three main methods:
    
    **Tab 1: Bulk Validation** 
    - Upload a list of retailers to validate for a single brand
    - Ideal for checking multiple stockists for one product line
    
    **Tab 2: Single Validation**
    - Quickly check a single retailer-brand combination
    - Get detailed results for a specific validation
    
    **Tab 3: Bulk Brand-Retailer Pairs**
    - Upload a CSV with 'Brand' and 'Retailer' columns
    - Process many different brand-retailer combinations at once
    - Ideal for validating entire distribution networks
    
    ### Validation Process
    
    1. **Google Shopping Check**: Searches for "[brand] site:[retailer]" in Google Shopping
    2. **Direct Website Verification**: Visits the retailer's website to confirm brand presence
    3. **Keyword Extraction**: Analyzes the website content for relevant keywords
    
    ### Validation Levels
    
    - **Valid**: Confirmed to stock the brand through Google Shopping or direct website check
    - **Unverified**: Could not definitively confirm or deny if the retailer stocks the brand
    - **Invalid**: Evidence suggests the retailer does not stock the brand
    
    ### Tips for Best Results
    
    - Use complete brand names (e.g., "Nike" instead of "N")
    - For more accurate results, process in smaller batches
    - Some websites may block automated checks - these will appear as "Unverified"
    - The Excel export includes a separate tab for each brand's results
    """)
                
