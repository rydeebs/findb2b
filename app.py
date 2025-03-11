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
    Enhanced function to scrape Google Shopping results with rate limit handling.
    Focuses exclusively on Google Shopping to extract retailers.
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
    
    # Direct Google Shopping URL - explicitly target shopping results only
    search_url = f"https://www.google.com/search?q={encoded_query}&tbm=shop&num=30"
    
    # Use a realistic user agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.72 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36 Edg/92.0.902.84",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
    ]
    
    retailers = []
    seen_domains = set()
    
    # Add progress indicator for rate limit backoff
    progress_message = st.empty()
    
    try:
        # Implement exponential backoff for rate limiting
        max_retries = 3
        base_delay = 2  # seconds
        
        for retry_count in range(max_retries):
            # Use a different user agent for each retry
            headers = {
                "User-Agent": random.choice(user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
                # Add a referer to look more like a real browser
                "Referer": "https://www.google.com/"
            }
            
            # Add a random delay before making the request
            delay = random.uniform(1.0, 3.0)
            progress_message.info(f"Searching Google Shopping for: {query} (waiting {delay:.1f}s to avoid rate limits)")
            time.sleep(delay)
            
            # Make the request
            response = requests.get(search_url, headers=headers, timeout=20)
            
            if response.status_code == 429:
                # Rate limited - exponential backoff
                wait_time = base_delay * (2 ** retry_count) + random.uniform(0, 1)
                progress_message.warning(f"Rate limited by Google. Waiting {wait_time:.1f} seconds before retrying...")
                time.sleep(wait_time)
                continue
                
            elif response.status_code != 200:
                progress_message.error(f"Google Shopping search failed: {response.status_code}")
                if retry_count < max_retries - 1:
                    continue
                else:
                    return []
            
            # If we reach here, we got a successful response
            progress_message.info(f"Successfully retrieved Google Shopping results for {query}")
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, "html.parser")
            
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
                        
                        # Get product title
                        product_title = "Product page"
                        title_elem = element.find(['h3', 'h4'])
                        if title_elem:
                            product_title = title_elem.text.strip()
                        
                        # Validate that the product contains part of the brand name
                        # This ensures we're only showing retailers that actually carry the brand's products
                        if brand_name.lower() not in product_title.lower():
                            # If title doesn't contain brand name, check parent elements for brand mention
                            parent_text = element.get_text().lower()
                            if brand_name.lower() not in parent_text:
                                # Skip this result if no brand mention found
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
                    
                    # Validate that the product contains part of the brand name
                    if brand_name.lower() not in product_title.lower():
                        # If parent elements exist, check them for brand mention
                        parent = link.parent
                        if parent:
                            parent_text = parent.get_text().lower()
                            if brand_name.lower() not in parent_text:
                                continue
                    
                    seen_domains.add(domain)
                    
                    retailers.append({
                        "Retailer": domain.split('.')[0].capitalize(),
                        "Domain": domain,
                        "Link": url,
                        "Product": product_title,
                        "Price": "N/A",
                        "Source": "Google Shopping"
                    })
            
            # If we have some results, don't try the next approach
            if retailers:
                break
    
    except Exception as e:
        progress_message.error(f"Error scraping Google Shopping: {str(e)}")
    
    # Clear the progress message
    progress_message.empty()
    
    return retailers

def find_retailers_comprehensive(brand_name, brand_url, industry, filters):
    """Main function to find retailers with improved rate limit handling"""
    all_retailers = []
    seen_domains = set()
    progress_message = st.empty()
    
    # First search with original parameters
    progress_message.info(f"Searching for retailers that carry {brand_name}...")
    retailers = search_google_shopping(brand_name, brand_url, industry, filters)
    
    for retailer in retailers:
        domain = retailer["Domain"]
        if domain not in seen_domains:
            all_retailers.append(retailer)
            seen_domains.add(domain)
    
    # If we don't have enough results, try with a specific "buy" keyword
    # But add a longer delay to avoid rate limiting
    if len(all_retailers) < 5:
        progress_message.info(f"Trying alternative search to find more retailers...")
        time.sleep(random.uniform(3.0, 5.0))  # Longer delay between searches
        
        buy_search = f"{brand_name} buy"
        retailers = search_google_shopping(buy_search, brand_url, industry, filters)
        
        for retailer in retailers:
            domain = retailer["Domain"]
            if domain not in seen_domains:
                all_retailers.append(retailer)
                seen_domains.add(domain)
    
    # Clear progress message
    progress_message.empty()
    
    return all_retailers

def find_3pl_relationships(brand_name, brand_url=None):
    """
    Search for articles or mentions that indicate the brand works with specific 3PL providers
    """
    # List of common 3PL providers to check for
    common_3pls = [
        "ShipBob", "Deliverr", "ShipMonk", "Rakuten Super Logistics", "Fulfillment by Amazon", 
        "Red Stag Fulfillment", "ShipHero", "Flexport", "Whiplash", "Radial", "Flowspace",
        "DCL Logistics", "Ryder E-commerce", "FedEx Fulfillment", "Saddle Creek Logistics",
        "OceanX", "Whitebox", "IDS Fulfillment", "Kenco Logistics", "SEKO Logistics"
    ]
    
    relationships = []
    progress_message = st.empty()
    
    # Build search queries to find articles about the brand's fulfillment
    search_queries = [
        f"{brand_name} fulfillment partner",
        f"{brand_name} logistics provider",
        f"{brand_name} 3PL provider",
        f"{brand_name} ecommerce fulfillment",
        f"{brand_name} shipping partner"
    ]
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    }
    
    # Separately search for direct connections to each 3PL
    found_3pls = set()
    
    # Try each search query
    for query in search_queries:
        try:
            progress_message.info(f"Searching for: {query}")
            
            # Add random delay to avoid rate limiting
            time.sleep(random.uniform(2.0, 4.0))
            
            # Encode query
            encoded_query = quote_plus(query)
            search_url = f"https://www.google.com/search?q={encoded_query}&num=10"
            
            # Make request
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                progress_message.warning(f"Search failed: {response.status_code}")
                continue
            
            # Parse response
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract search results
            results = soup.find_all('div', {'class': re.compile('g|result')})
            
            for result in results:
                result_text = result.get_text().lower()
                
                # Check for mentions of 3PLs in this result
                for provider in common_3pls:
                    if provider.lower() in result_text:
                        # Found a potential relationship
                        if provider not in found_3pls:
                            # Get the URL
                            link_elem = result.find('a')
                            link = link_elem.get('href') if link_elem else "#"
                            
                            # Get context (snippet)
                            snippet = ""
                            snippet_elem = result.find('div', {'class': re.compile('VwiC3b|st|snippet')})
                            if snippet_elem:
                                snippet = snippet_elem.get_text()
                            
                            # Extract title
                            title = ""
                            title_elem = result.find('h3')
                            if title_elem:
                                title = title_elem.get_text()
                            
                            relationships.append({
                                "3PL Provider": provider,
                                "Article Title": title,
                                "Context": snippet,
                                "Source": link,
                                "Type": "Mention in article"
                            })
                            
                            found_3pls.add(provider)
            
        except Exception as e:
            progress_message.error(f"Error during search: {str(e)}")
            continue
    
    # Now search specifically for case studies
    for provider in common_3pls:
        # Skip if already found
        if provider in found_3pls:
            continue
            
        try:
            # Format provider name for domain
            provider_domain = provider.lower().replace(' ', '').replace('-', '').replace('&', 'and')
            if provider_domain == "fulfillmentbyamazon":
                provider_domain = "amazon"
                
            # Create case study search
            case_study_query = f"{brand_name} case study site:{provider_domain}.com"
            encoded_query = quote_plus(case_study_query)
            
            # Delay to avoid rate limiting
            time.sleep(random.uniform(2.0, 4.0))
            
            # Make request
            search_url = f"https://www.google.com/search?q={encoded_query}&num=5"
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                continue
                
            # Parse response
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Check if we actually got results
            if "did not match any documents" in soup.get_text():
                continue
                
            # Extract search results
            results = soup.find_all('div', {'class': re.compile('g|result')})
            
            if results:
                # Likely found a case study
                result = results[0]  # Take the first result
                
                # Get the URL
                link_elem = result.find('a')
                link = link_elem.get('href') if link_elem else "#"
                
                # Get title
                title = ""
                title_elem = result.find('h3')
                if title_elem:
                    title = title_elem.get_text()
                
                # Get snippet
                snippet = ""
                snippet_elem = result.find('div', {'class': re.compile('VwiC3b|st|snippet')})
                if snippet_elem:
                    snippet = snippet_elem.get_text()
                
                relationships.append({
                    "3PL Provider": provider,
                    "Article Title": title,
                    "Context": snippet,
                    "Source": link,
                    "Type": "Case Study"
                })
                
                found_3pls.add(provider)
                
        except Exception as e:
            continue
    
    # Clear progress message
    progress_message.empty()
    
    return relationships

# Streamlit UI
st.title("Brand Retailer & 3PL Finder")
st.write("Find retailers that carry a specific brand's products and their 3PL providers")

brand_name = st.text_input("Enter Brand Name:")
brand_url = st.text_input("Enter Brand Website URL (optional):")
industry = st.text_input("Enter Industry (optional):")
filters = st.text_input("Enter Additional Filters (comma-separated, optional):")
filters_list = [f.strip() for f in filters.split(',')] if filters else []

# Create tabs for different functions
tab1, tab2 = st.tabs(["Retailers", "3PL Providers"])

with tab1:
    if st.button("Find Retailers", key="retailer_button"):
        if not brand_name:
            st.error("Please enter a brand name to search.")
        else:
            with st.spinner(f"Searching for retailers that carry {brand_name}..."):
                results = find_retailers_comprehensive(brand_name, brand_url, industry, filters_list)
            
            if results:
                st.success(f"Found {len(results)} retailers carrying {brand_name}")
                
                # Create DataFrame and ensure all results are from Google Shopping
                df = pd.DataFrame(results)
                
                # Display results
                st.dataframe(df)
                
                # Download option
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download Results as CSV", csv, f"{brand_name}_retailers.csv", "text/csv")
            else:
                st.warning("No retailers found. This might be due to Google's rate limiting. Try again in a few minutes.")
                
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

with tab2:
    st.markdown("""
    ### 3PL Provider Finder
    This feature searches for articles and case studies that mention the brand's relationship with 3PL (third-party logistics) providers.
    
    Results are based on online mentions and should be verified through other means.
    """)
    
    if st.button("Find 3PL Relationships", key="3pl_button"):
        if not brand_name:
            st.error("Please enter a brand name to search.")
        else:
            with st.spinner(f"Searching for 3PL relationships for {brand_name}..."):
                results = find_3pl_relationships(brand_name, brand_url)
            
            if results:
                st.success(f"Found {len(results)} potential 3PL relationships for {brand_name}")
                
                # Create DataFrame
                df = pd.DataFrame(results)
                
                # Display results
                st.dataframe(df)
                
                # Download option
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download 3PL Results as CSV", csv, f"{brand_name}_3pl_relationships.csv", "text/csv")
            else:
                st.warning("No 3PL relationships found in online articles.")
                
                st.info("""
                **Common 3PL providers to check manually:**
                - ShipBob
                - Deliverr (Shopify Fulfillment Network)
                - ShipMonk
                - Fulfillment by Amazon (FBA)
                - Flexport
                - Red Stag Fulfillment
                """)

# Add footer with timestamp
st.markdown("---")
st.markdown(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
