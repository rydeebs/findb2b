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
