import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
from urllib.parse import quote_plus, unquote, urlparse

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

def scrape_google_shopping(brand_name, brand_url=None):
    """
    Scrapes Google Shopping results for retailers selling a specific brand
    
    Args:
        brand_name: Name of the brand to search for
        brand_url: Optional brand website to exclude from results
    
    Returns:
        List of retailer dictionaries
    """
    # Clean up brand URL if provided
    brand_domain = extract_domain(brand_url) if brand_url else None
    
    # Prepare search query
    query = quote_plus(brand_name)
    
    # Direct Google Shopping URL
    url = f"https://www.google.com/search?q={query}&tbm=shop&num=100"
    
    # Use a realistic user agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    # Status indicator
    status = st.empty()
    status.info(f"Searching Google Shopping for: {brand_name}")
    
    try:
        # Make request with timeout
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            status.error(f"Google Shopping search failed: {response.status_code}")
            return []
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find shopping items
        retailers = []
        seen_domains = set()
        
        # Find merchant elements in shopping results
        merchant_elements = soup.find_all(["div", "span"], class_=re.compile("(merchant|sh-dlr__merchant)"))
        product_elements = soup.find_all(["div"], class_=re.compile("(sh-dgr__content|sh-dlr__list-result)"))
        
        # Process merchant elements
        for element in merchant_elements:
            # Find parent container
            parent = element
            for _ in range(5):  # Look up to 5 levels
                if parent.name == "div" and parent.get("class") and any("sh-" in c for c in parent.get("class", [])):
                    break
                parent = parent.parent
                if not parent:
                    break
            
            # Find links in the parent container
            links = parent.find_all("a", href=True) if parent else []
            
            for link in links:
                url = link["href"]
                
                # Extract actual URL from Google redirect
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
                
                # Extract domain
                domain = extract_domain(url)
                
                # Skip if it's the brand's own site
                if brand_domain and (domain == brand_domain or brand_domain in domain):
                    continue
                    
                # Skip common non-retailer sites
                skip_domains = ['google.', 'facebook.', 'instagram.', 'pinterest.', 'twitter.', 
                              'linkedin.', 'tiktok.', 'youtube.', 'reddit.']
                if any(skip in domain.lower() for skip in skip_domains):
                    continue
                
                # Skip if already seen
                if domain in seen_domains:
                    continue
                
                seen_domains.add(domain)
                
                # Find merchant name
                merchant_text = element.get_text().strip()
                from_match = re.search(r'from\s+(\w+)', merchant_text, re.IGNORECASE)
                if from_match:
                    merchant_name = from_match.group(1)
                else:
                    # Default to domain name
                    merchant_name = domain.split('.')[0].capitalize()
                
                # Find product name
                product_name = "Product page"
                title_elem = parent.find(["h3", "h4"]) or parent.find(class_=re.compile("(title|product-title)"))
                if title_elem:
                    product_name = title_elem.get_text().strip()
                
                # Find price
                price = "N/A"
                price_elem = parent.find(text=re.compile(r'\$[\d,]+\.\d{2}'))
                if price_elem:
                    price = price_elem
                
                retailers.append({
                    "Retailer": merchant_name,
                    "Domain": domain,
                    "Product": product_name,
                    "Price": price,
                    "Link": url
                })
        
        # Process product elements if we didn't find merchants directly
        if len(retailers) < 2:
            for product in product_elements:
                # Look for links in this product
                links = product.find_all("a", href=True)
                
                for link in links:
                    url = link["href"]
                    
                    # Extract actual URL from Google redirect
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
                    
                    # Extract domain
                    domain = extract_domain(url)
                    
                    # Skip if it's the brand's own site
                    if brand_domain and (domain == brand_domain or brand_domain in domain):
                        continue
                        
                    # Skip common non-retailer sites
                    skip_domains = ['google.', 'facebook.', 'instagram.', 'pinterest.', 'twitter.', 
                                  'linkedin.', 'tiktok.', 'youtube.', 'reddit.']
                    if any(skip in domain.lower() for skip in skip_domains):
                        continue
                    
                    # Skip if already seen
                    if domain in seen_domains:
                        continue
                    
                    seen_domains.add(domain)
                    
                    # Find product name
                    product_name = "Product page"
                    title_elem = product.find(["h3", "h4"]) or product.find(class_=re.compile("(title|product-title)"))
                    if title_elem:
                        product_name = title_elem.get_text().strip()
                    
                    # Find price
                    price = "N/A"
                    price_elem = product.find(text=re.compile(r'\$[\d,]+\.\d{2}'))
                    if price_elem:
                        price = price_elem
                    
                    # Find merchant name (look for "from X" text)
                    merchant_name = domain.split('.')[0].capitalize()
                    merchant_elem = product.find(text=re.compile(r'from\s+\w+', re.IGNORECASE))
                    if merchant_elem:
                        from_match = re.search(r'from\s+(\w+)', merchant_elem, re.IGNORECASE)
                        if from_match:
                            merchant_name = from_match.group(1)
                    
                    retailers.append({
                        "Retailer": merchant_name,
                        "Domain": domain,
                        "Product": product_name,
                        "Price": price,
                        "Link": url
                    })
        
        # Final fallback: look for all links in shopping results
        if len(retailers) < 2:
            # Get all links from the page
            for link in soup.find_all("a", href=True):
                url = link["href"]
                
                # Only process Google Shopping redirects
                if not ('url=' in url or 'aclk?' in url):
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
                
                # Extract domain
                domain = extract_domain(url)
                
                # Skip if it's the brand's own site
                if brand_domain and (domain == brand_domain or brand_domain in domain):
                    continue
                    
                # Skip common non-retailer sites
                skip_domains = ['google.', 'facebook.', 'instagram.', 'pinterest.', 'twitter.', 
                              'linkedin.', 'tiktok.', 'youtube.', 'reddit.']
                if any(skip in domain.lower() for skip in skip_domains):
                    continue
                
                # Skip if already seen
                if domain in seen_domains:
                    continue
                
                seen_domains.add(domain)
                
                # Get link text as product name if available
                product_name = link.get_text().strip() if link.get_text().strip() else "Product page"
                
                retailers.append({
                    "Retailer": domain.split('.')[0].capitalize(),
                    "Domain": domain,
                    "Product": product_name,
                    "Price": "N/A",
                    "Link": url
                })
        
        status.success(f"Found {len(retailers)} retailers on Google Shopping")
        return retailers
        
    except Exception as e:
        status.error(f"Error: {str(e)}")
        return []

# Streamlit UI
st.title("Brand Retailer Finder")
st.write("Find retailers that carry a specific brand's products on Google Shopping")

brand_name = st.text_input("Enter Brand Name:")
brand_url = st.text_input("Enter Brand Website URL (optional):")

if st.button("Find Retailers"):
    if not brand_name:
        st.error("Please enter a brand name to search.")
    else:
        with st.spinner(f"Searching for retailers that carry {brand_name}..."):
            results = scrape_google_shopping(brand_name, brand_url)
        
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
            st.warning("No retailers found on Google Shopping for this brand.")
            
            # Suggest direct checks
            st.info("You can manually check these common retailers:")
            common_retailers = {
                "Amazon": f"https://www.amazon.com/s?k={quote_plus(brand_name)}",
                "Target": f"https://www.target.com/s?searchTerm={quote_plus(brand_name)}",
                "Walmart": f"https://www.walmart.com/search?q={quote_plus(brand_name)}"
            }
            
            for retailer, url in common_retailers.items():
                st.markdown(f"- [{retailer}]({url})")

# Add footer with timestamp
st.markdown("---")
st.markdown(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
