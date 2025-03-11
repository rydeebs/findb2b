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

def find_3pl_providers(brand_name, brand_url=None):
    """
    Search for 3PL fulfillment providers used by a brand
    """
    providers = []
    
    # List of common 3PL providers to check
    common_3pls = [
        "ShipBob", "Deliverr", "ShipMonk", "Rakuten Super Logistics", "Fulfillment by Amazon", 
        "Red Stag Fulfillment", "ShipHero", "Flexport", "Whiplash", "Radial", "Flowspace",
        "DCL Logistics", "Ryder E-commerce", "FedEx Fulfillment", "Saddle Creek Logistics",
        "OceanX", "Whitebox", "IDS Fulfillment", "Kenco Logistics", "SEKO Logistics",
        "XB Fulfillment", "Shipwire", "Quiet Logistics", "Ruby Has", "symbia",
        "Fulfillrite", "Falcon Fulfillment", "eFulfillment Service", "Fulfyld", "Arvato",
        "Ingram Micro", "DHL eCommerce", "NewEgg Logistics", "UPS Supply Chain Solutions",
        "Amware Fulfillment", "PFS", "Mainfreight", "ShipNetwork", "C.H. Robinson", "DSV",
        "Geodis", "Kuehne + Nagel", "DB Schenker", "DHL Supply Chain", "XPO Logistics"
    ]
    
    # Build comprehensive searches to check for 3PL relationships
    search_queries = [
        f"{brand_name} fulfillment partner",
        f"{brand_name} logistics provider",
        f"{brand_name} 3PL provider",
        f"{brand_name} ships with",
        f"{brand_name} warehousing partner",
        f"{brand_name} order fulfillment",
        f"{brand_name} fulfillment center",
        f"{brand_name} distribution center",
        f"{brand_name} shipping partner",
        f"{brand_name} ecommerce fulfillment",
        f"{brand_name} uses for fulfillment",
        f"{brand_name} shipping label shows",
        f"{brand_name} packages shipped from",
        f"{brand_name} logistics case study",
        f"{brand_name} order processing",
        f"{brand_name} partners with fulfillment",
        f"{brand_name} third party logistics",
        f"{brand_name} supply chain partner",
        f"{brand_name} inventory management",
        f"{brand_name} warehouse locations",
        f"{brand_name} packaging slip",
        f"{brand_name} returns processing",
        f"{brand_name} third-party logistics",
        f"{brand_name} shipping from",
        f"{brand_name} fulfillment services"
    ]
    
    # Add specific provider checks
    for provider in common_3pls:
        search_queries.append(f"{brand_name} {provider}")
    
    seen_providers = set()
    
    for query in search_queries:
        try:
            # Standard Google search
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=30"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Get search result text
                search_results = soup.find_all("div", class_=re.compile("g|result"))
                
                for result in search_results:
                    result_text = result.text.lower()
                    
                    # Check for mentions of common 3PLs
                    for provider in common_3pls:
                        if provider.lower() in result_text:
                            # Found a potential 3PL reference
                            if provider not in seen_providers:
                                seen_providers.add(provider)
                                
                                # Try to get the context
                                context = ""
                                matches = re.findall(r'[^.?!]*\b' + re.escape(provider.lower()) + r'\b[^.?!]*[.?!]', result_text)
                                if matches:
                                    context = matches[0].strip()
                                
                                # Get the link
                                link_elem = result.find("a")
                                link = link_elem.get("href") if link_elem else "#"
                                
                                providers.append({
                                    "3PL Provider": provider,
                                    "Context": context,
                                    "Source": link,
                                    "Confidence": "Medium"
                                })
                                
                # Direct statement patterns (e.g., "works with ShipBob")
                patterns = [
                    r'(?:' + brand_name.lower() + r')\s+(?:use[sd]?|work[sd]? with|partner[sd]? with|ship[sd]? (?:with|via|through|using))\s+([A-Za-z\s]+(?:fulfillment|logistics|shipping|3PL|warehouse))',
                    r'(?:' + brand_name.lower() + r')\s+(?:use[sd]?|work[sd]? with|partner[sd]? with|ship[sd]? (?:with|via|through|using))\s+([A-Za-z\s]+)'
                ]
                
                for pattern in patterns:
                    for result in search_results:
                        result_text = result.text.lower()
                        matches = re.findall(pattern, result_text)
                        
                        for match in matches:
                            provider_name = match.strip()
                            
                            # Filter out general terms
                            skip_terms = ['their', 'the', 'a', 'an', 'this', 'that', 'these', 'those', 'our', 'your']
                            if provider_name in skip_terms or len(provider_name) < 4:
                                continue
                                
                            # Check against common 3PLs for partial matches
                            matched_provider = None
                            for common_3pl in common_3pls:
                                if common_3pl.lower() in provider_name:
                                    matched_provider = common_3pl
                                    break
                            
                            if matched_provider:
                                provider_name = matched_provider
                            
                            if provider_name not in seen_providers:
                                seen_providers.add(provider_name)
                                
                                # Get the context
                                context = ""
                                full_matches = re.findall(r'[^.?!]*\b' + re.escape(provider_name) + r'\b[^.?!]*[.?!]', result_text)
                                if full_matches:
                                    context = full_matches[0].strip()
                                
                                # Get the link
                                link_elem = result.find("a")
                                link = link_elem.get("href") if link_elem else "#"
                                
                                providers.append({
                                    "3PL Provider": provider_name.title(),
                                    "Context": context,
                                    "Source": link,
                                    "Confidence": "Medium" if matched_provider else "Low"
                                })
        except Exception as e:
            st.error(f"Error searching for 3PL providers: {str(e)}")
            continue
    
    # Check LinkedIn for company connections
    if brand_url:
        try:
            domain = extract_domain(brand_url)
            linkedin_search = f"{domain} logistics fulfillment 3PL site:linkedin.com"
            search_url = f"https://www.google.com/search?q={quote_plus(linkedin_search)}&num=20"
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Get search result text
                search_results = soup.find_all("div", class_=re.compile("g|result"))
                
                for result in search_results:
                    result_text = result.text.lower()
                    
                    # Check for mentions of common 3PLs
                    for provider in common_3pls:
                        if provider.lower() in result_text:
                            # Found a potential 3PL reference
                            if provider not in seen_providers:
                                seen_providers.add(provider)
                                
                                # Get the link
                                link_elem = result.find("a")
                                link = link_elem.get("href") if link_elem else "#"
                                
                                providers.append({
                                    "3PL Provider": provider,
                                    "Context": "Found on LinkedIn",
                                    "Source": link,
                                    "Confidence": "Medium"
                                })
        except:
            pass
    
    # Look for case studies from 3PL providers
    for provider in common_3pls:
        try:
            case_study_search = f"{brand_name} case study site:{provider.lower().replace(' ', '')}.com"
            search_url = f"https://www.google.com/search?q={quote_plus(case_study_search)}&num=10"
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200 and "did not match any documents" not in response.text:
                # Found a potential case study
                if provider not in seen_providers:
                    seen_providers.add(provider)
                    
                    providers.append({
                        "3PL Provider": provider,
                        "Context": f"Potential case study found on {provider}'s website",
                        "Source": f"https://www.google.com/search?q={quote_plus(case_study_search)}",
                        "Confidence": "High"
                    })
        except:
            continue
    
    # Check for job listings mentioning logistics partners
    try:
        job_search = f"{brand_name} (fulfillment OR logistics OR warehouse OR distribution) (job OR careers) -apply"
        search_url = f"https://www.google.com/search?q={quote_plus(job_search)}&num=20"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        response = requests.get(search_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Get search result text
            search_results = soup.find_all("div", class_=re.compile("g|result"))
            
            for result in search_results:
                result_text = result.text.lower()
                
                # Check for mentions of common 3PLs in job postings
                for provider in common_3pls:
                    if provider.lower() in result_text:
                        # Found a potential 3PL reference in job posting
                        if provider not in seen_providers:
                            seen_providers.add(provider)
                            
                            # Get the link
                            link_elem = result.find("a")
                            link = link_elem.get("href") if link_elem else "#"
                            
                            providers.append({
                                "3PL Provider": provider,
                                "Context": "Found in job posting",
                                "Source": link,
                                "Confidence": "Medium"
                            })
    except:
        pass
    
    return providers

# Streamlit UI
st.title("Brand Retailer & 3PL Finder")
st.write("Find retailers that carry a specific brand's products and their fulfillment providers")

brand_name = st.text_input("Enter Brand Name:")
brand_url = st.text_input("Enter Brand Website URL (optional):")
industry = st.text_input("Enter Industry (optional):")
filters = st.text_input("Enter Additional Filters (comma-separated, optional):")
filters_list = [f.strip() for f in filters.split(',')] if filters else []

tab1, tab2 = st.tabs(["Retailers", "3PL Providers"])

with tab1:
    if st.button("Find Retailers", key="retailer_button"):
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

with tab2:
    st.info("This feature attempts to identify 3PL (third-party logistics) fulfillment providers used by a brand. Results are experimental and should be verified.")
    
    if st.button("Find 3PL Providers", key="3pl_button"):
        if not brand_name:
            st.error("Please enter a brand name to search.")
        else:
            with st.spinner(f"Searching for 3PL fulfillment providers used by {brand_name}..."):
                results = find_3pl_providers(brand_name, brand_url)
            
            if results:
                st.success(f"Found {len(results)} potential 3PL providers for {brand_name}")
                
                # Create DataFrame
                df = pd.DataFrame(results)
                
                # Sort by confidence
                df = df.sort_values(by="Confidence", key=lambda x: x.map({"High": 3, "Medium": 2, "Low": 1}), ascending=False)
                
                # Display results
                st.dataframe(df)
                
                # Download option
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download 3PL Results as CSV", csv, f"{brand_name}_3pl_providers.csv", "text/csv")
                
                # Show disclaimer
                st.warning("Note: 3PL information is often not publicly disclosed. These results are based on public web mentions and should be verified through other means.")
            else:
                st.warning("No 3PL providers found. This information is often not publicly available.")
                
                st.info("Common 3PL providers you could check manually:")
                top_3pls = [
                    "ShipBob", "Deliverr (Shopify)", "ShipMonk", "Fulfillment by Amazon (FBA)", 
                    "Red Stag Fulfillment", "ShipHero", "Flexport", "Whiplash", "Radial"
                ]
                for provider in top_3pls:
                    st.markdown(f"- {provider}")
                
                st.markdown("""
                **Tips for verifying 3PL providers:**
                - Order a product from the brand and check the shipping/return label
                - Look at the brand's careers page for logistics/fulfillment positions
                - Check the brand's LinkedIn page for connections to logistics companies
                - Search for case studies on 3PL provider websites
                - Review press releases about the brand's fulfillment operations
                """)

# Additional information about the app
with st.expander("About this app"):
    st.write("""
    This app helps you find retailers that carry a specific brand's products and identifies potential 3PL fulfillment providers used by the brand.
    
    **Retailer Finder Features:**
    - Scrapes Google Shopping results to identify online retailers
    - Uses multiple search strategies to maximize results
    - Excludes the brand's own website from results
    - Identifies product pages and pricing information when available
    
    **3PL Provider Finder Features:**
    - Searches for mentions of known 3PL providers in connection with the brand
    - Looks for case studies, LinkedIn connections, and direct mentions
    - Assigns confidence scores based on the quality of matches
    - Provides context snippets to help verify relationships
    
    **Tips for best results:**
    - Enter the exact brand name
    - If you know the brand's website, enter it to exclude the brand's own site from results
    - Specify the industry to get more relevant results (e.g., "cosmetics", "electronics")
    - Use filters to narrow down results (e.g., "usa", "official retailer")
    
    **Limitations:**
    - 3PL information is often not publicly disclosed and results should be verified
    - Google Shopping results can vary by location and time
    - Some retailers may be missed, especially smaller or regional ones
    - The app cannot access private/paid databases that might contain more comprehensive information
    """)

# Add footer with timestamp
st.markdown("---")
st.markdown(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
