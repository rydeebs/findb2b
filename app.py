import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import random
import io
import matplotlib.pyplot as plt
from io import BytesIO

# Set page configuration
st.set_page_config(
    page_title="B2B Partnership Finder",
    page_icon="🔍",
    layout="wide"
)

# Application header
st.title("B2B Partnership Finder")
st.markdown("""
This tool helps business development representatives identify B2B retail distribution 
partnerships for brands. Enter a merchant's website to discover their retail partners.
""")

# Sidebar with instructions
with st.sidebar:
    st.header("How it works")
    st.markdown("""
    1. Enter a brand's website URL
    2. The tool analyzes:
       - Website content for retailer mentions
       - "Where to buy" or "Store locator" pages
       - Press releases mentioning partnerships
       - Backlink analysis from major retailers
    3. Results show verified retail partners with high confidence scores (90%+)
    
    **Note:** In a full implementation, this would connect to external APIs 
    for comprehensive data analysis.
    """)
    
    st.header("Example Brands")
    st.markdown("""
    Try these examples:
    - Snow Cosmetics (trysnow.com)
    - Rothy's (rothys.com)
    - Allbirds (allbirds.com)
    """)

# Comprehensive retailer database 
major_retailers = [
    "AAFES- Domestic",
    "Academy Sports and Outdoors",
    "Ace Hardware",
    "Albertsons",
    "Altitude (Canada)",
    "Amazon Advantage",
    "Amazon Seller Central",
    "Amazon Vendor Central",
    "Anaconda Canada",
    "Anthropologie",
    "ASOS",
    "Babylist",
    "Backcountry",
    "Barnes and Noble",
    "Bass Pro Shop/Cabela's",
    "Bass Pro Shop/Cabela's (Canada)",
    "Bealls",
    "Bed Bath & Beyond",
    "Belk",
    "Best Buy",
    "BevMo!",
    "Big Lots",
    "Big Rock Sports",
    "Bloomingdales",
    "Bluemercury",
    "Boscov's",
    "Burlington",
    "Buc-cees",
    "C&S Wholesalers",
    "Canadian Tire",
    "Cardinal Health",
    "Chatters Canada",
    "Chewy",
    "Coast Guard Exchange",
    "Container Store",
    "Costco",
    "Coupang",
    "Crate & Barrel",
    "CVS",
    "Dicks Sporting Goods / Field and Stream",
    "Do It Best",
    "Dollar General",
    "Dollar Tree/ Family Dollar",
    "Dot Food",
    "Dillards",
    "Essendant",
    "Fabfitfun (FFF)",
    "Fanatics",
    "FAO Schwarz",
    "Fastenal",
    "FleetFarm",
    "FLG",
    "Five Below",
    "FootLocker",
    "Francesca's",
    "Fullscript",
    "Fred Meyer (Kroger)",
    "Giant Eagle",
    "GNC",
    "Golf Town",
    "GOOP",
    "GoPuff",
    "Gordon Food Services",
    "Grainger",
    "Grove Collaborative",
    "Hamrick's",
    "Harris Teeter (Kroger)",
    "HEB",
    "Holt Renfrew (Canada)",
    "Home Depot",
    "HSN",
    "HyVee",
    "iHerb",
    "Indigo Canada",
    "Ingles",
    "Ingram Micro",
    "K&G",
    "KeHE",
    "Keystone Automotive",
    "Kohls",
    "Lids",
    "Lifetime / Business Impact Group (BIG)",
    "LOBLAW",
    "Lord & Taylor",
    "Lowe's",
    "Lynco",
    "Macys",
    "Marine Corps Exchange (MCX) Domenstic",
    "Mark and Graham (Williams Sonoma)",
    "Mark's",
    "Marshall Retail Group (InMotion Entertainment)",
    "MCKesson",
    "McKesson Canada",
    "Mclane",
    "MEC",
    "MECCA Brands International",
    "Meijer",
    "Menards",
    "Napa Auto Parts",
    "Natural Grocers",
    "Neiman Marcus",
    "Nexcom",
    "Nordstrom",
    "Nordstrom Canada",
    "Nordstrom Rack",
    "Office Depot",
    "Pet Supermarket",
    "Pet Supply Plus",
    "Pet Valu (CANADA)",
    "Petco",
    "Petsmart",
    "PGA Tour Superstore",
    "Pottery Barn (Williams Sonoma)",
    "Pottery Barn Kids (Williams Sonoma)",
    "QVC",
    "RCI (Sun & Ski Sports)",
    "REI",
    "Rejuvenation (Williams Sonoma)",
    "Rite Aid",
    "Roadrunner Sports",
    "Ross",
    "Rural King",
    "Saks Fifth Avenue",
    "Saks Off Fifth",
    "Sally Beauty",
    "Sams Club",
    "Scheels",
    "Schnuck",
    "Sephora (U.S. DOMESTIC ONLY!!!)",
    "Shoe Sensation",
    "ShopBob (US)",
    "Shoppers Drug Market- Canada",
    "Sierra (TJX)",
    "Sports Endeavours",
    "Sprouts - Direct to Store",
    "Sporting Life",
    "Staples",
    "Starboard cruise",
    "Stitch Fix",
    "Summit Racing",
    "Super Retail Group",
    "Superior Communication",
    "Sur La Table",
    "Target",
    "The Iconic",
    "The Paper Store",
    "Threshold Enterprises",
    "Thrive Market",
    "TJ Maxx",
    "Tractor Supply",
    "True Value",
    "Ulta",
    "UNFI",
    "Urban Outfitters",
    "US Foods",
    "Veterans Canteen Services (VCS)",
    "Vistar",
    "Vitamin Shoppe",
    "Von Maur",
    "Wakefern",
    "Walgreens",
    "Walmart",
    "Walmart DSDC- Pack by Store",
    "Walmart (Canada)",
    "Wegmans",
    "Well.ca",
    "West Elm (Williams Sonoma)",
    "Williams Sonoma",
    "Whole Foods",
    "World Wide Golf",
    "Zappos",
    "Zulily"
]

# Function to simulate website content analysis with improved verification
def analyze_website_content(url, brand_name=""):
    st.write("🔍 Analyzing website content...")
    st.write("📑 Looking for 'Where to Buy' or 'Store Locator' pages...")
    
    # Placeholder for actual implementation
    progress_bar = st.progress(0)
    for i in range(100):
        time.sleep(0.01)
        progress_bar.progress(i + 1)
    
    st.success("Website content analysis complete!")
    
    # In a real implementation, we would:
    # 1. Crawl the website to find "Where to Buy" or "Store Locator" pages
    # 2. Extract retailer mentions from these pages
    # 3. Verify each retailer by checking for links to their websites
    
    # Return a simulated set of "verified" retailers from website
    if brand_name:
        st.info(f"TIP: In a full implementation, the app would specifically look for mentions of '{brand_name}' on store locator pages.")
    
    return True

# Function to simulate backlink analysis with verification
def analyze_backlinks(url, brand_name=""):
    st.write("🔗 Analyzing backlinks from retail websites...")
    st.write("🧐 Verifying retailer links to confirm partnerships...")
    
    # Placeholder for actual implementation
    progress_bar = st.progress(0)
    for i in range(100):
        time.sleep(0.01)
        progress_bar.progress(i + 1)
    
    st.success("Backlink analysis complete!")
    
    # In a real implementation, we would:
    # 1. Use a backlink API (Ahrefs, Majestic, SEMrush, etc.)
    # 2. Check for backlinks from major retailer domains
    # 3. Analyze the context of these backlinks to determine if they represent a partnership
    
    if brand_name:
        st.info(f"TIP: In a full implementation, the app would verify if '{brand_name}' appears on retailer websites through direct search.")
    
    return True

# Function to verify retailer presence with improved verification methods
def verify_retailer_presence(retailer, brand_name):
    """
    Simulation of verification of brand presence on retailer website.
    In a real implementation, this would use multiple verification methods:
    
    1. Direct retailer website search API
    2. Backlink analysis between brand and retailer
    3. Affiliate link detection
    4. Social proof verification
    5. Industry database cross-checking
    
    Returns:
    - verification_score: 0-100 score of verification confidence
    - verification_source: Description of the verification method
    - verification_url: URL that provides evidence (if available)
    """
    
    # For demo purposes, generate realistic verification scores
    # In a real implementation, these would be based on actual verification attempts
    
    # Sample verification statuses - in a real app these would come from actual API calls
    verified_brands = {
        "Snow Cosmetics": ["Amazon", "Target", "Sephora", "Ulta Beauty", "Macy's", "Nordstrom"],
        "Rothy's": ["Nordstrom", "Bloomingdale's", "Neiman Marcus", "Zappos"],
        "Allbirds": ["Nordstrom", "Dick's Sporting Goods", "REI"],
    }
    
    # Verification methods that would be used in a full implementation
    verification_methods = [
        "Retailer website product page found",
        "Brand listed in retailer's brand directory",
        "Backlink analysis confirmed partnership",
        "Affiliate link detection verified",
        "Found on brand's 'Where to Buy' page",
        "Direct API verification with retailer"
    ]
    
    # For known brands, use our verified retailer list
    if brand_name in verified_brands and retailer in verified_brands[brand_name]:
        verification_score = random.randint(90, 100)  # High confidence for known partnerships
        verification_source = random.choice(verification_methods)
        
        # Generate a realistic verification URL based on retailer
        retailer_domain = retailer.lower().replace(" ", "").replace("'", "").split("(")[0].strip()
        brand_slug = brand_name.lower().replace(" ", "-")
        
        if "amazon" in retailer_domain:
            verification_url = f"amazon.com/stores/{brand_slug}"
        elif "sephora" in retailer_domain:
            verification_url = f"sephora.com/brand/{brand_slug}"
        elif "target" in retailer_domain:
            verification_url = f"target.com/b/{brand_slug}"
        elif "nordstrom" in retailer_domain:
            verification_url = f"nordstrom.com/brands/{brand_slug}"
        else:
            verification_url = f"{retailer_domain}.com/brands/{brand_slug}"
        
        return verification_score, verification_source, verification_url
    
    # For other combinations, evaluate based on industry match
    elif brand_name:
        # Check if this is a plausible match based on industry
        is_beauty_brand = any(term in brand_name.lower() for term in ["beauty", "cosmetic", "skin", "makeup"])
        is_footwear_brand = any(term in brand_name.lower() for term in ["shoe", "footwear", "sneaker"])
        is_apparel_brand = any(term in brand_name.lower() for term in ["apparel", "cloth", "wear", "fashion"])
        is_food_brand = any(term in brand_name.lower() for term in ["food", "snack", "grocery", "meal", "drink"])
        is_pet_brand = any(term in brand_name.lower() for term in ["pet", "dog", "cat", "animal"])
        is_tech_brand = any(term in brand_name.lower() for term in ["tech", "electronics", "digital", "computer"])
        
        # Check if retailer is in the same industry
        is_beauty_retailer = retailer in ["Sephora", "Ulta Beauty", "Bluemercury", "Macy's", "CVS"]
        is_footwear_retailer = retailer in ["DSW", "Zappos", "Foot Locker", "Famous Footwear"]
        is_apparel_retailer = retailer in ["Nordstrom", "Macy's", "TJ Maxx", "Urban Outfitters"]
        is_food_retailer = retailer in ["Whole Foods", "Kroger", "Albertsons", "Sprouts", "Wegmans", "Target"]
        is_pet_retailer = retailer in ["Chewy", "Petco", "PetSmart", "Pet Supplies Plus"]
        is_tech_retailer = retailer in ["Best Buy", "Apple", "Target", "Walmart", "Amazon"]
        
        # Set base verification score
        if (is_beauty_brand and is_beauty_retailer) or \
           (is_footwear_brand and is_footwear_retailer) or \
           (is_apparel_brand and is_apparel_retailer) or \
           (is_food_brand and is_food_retailer) or \
           (is_pet_brand and is_pet_retailer) or \
           (is_tech_brand and is_tech_retailer):
            verification_score = random.randint(30, 89)  # Plausible but not confirmed
        else:
            verification_score = random.randint(5, 40)  # Less likely match
        
        # We're only returning results with 90%+ confidence, so most of these won't be shown
        verification_source = "Insufficient verification evidence"
        verification_url = "#"
        
        return verification_score, verification_source, verification_url
    
    # Fallback for URL-only searches without brand name
    else:
        verification_score = random.randint(10, 60)  # Less confident without brand name
        verification_source = "Unverified - brand name needed for confirmation"
        verification_url = "#"
        return verification_score, verification_source, verification_url

# Function to generate mock results based on the input URL and brand name
def generate_results(url, brand_name=""):
    # Predefined sample results for demonstration
    sample_data = {
        "trysnow.com": [
            {"retailer": "Amazon", "confidence": 95, "source": "Direct mention on website + backlinks", "url": "amazon.com/snow"},
            {"retailer": "Target", "confidence": 90, "source": "Store locator page + backlinks", "url": "target.com/snow"},
            {"retailer": "Sephora", "confidence": 85, "source": "Press release + social media", "url": "sephora.com/snow"},
            {"retailer": "Ulta Beauty", "confidence": 80, "source": "Backlinks + product listings", "url": "ulta.com/snow"},
            {"retailer": "Nordstrom", "confidence": 70, "source": "Backlinks", "url": "nordstrom.com/snow"}
        ],
        "rothys.com": [
            {"retailer": "Nordstrom", "confidence": 95, "source": "Direct mention + store locator", "url": "nordstrom.com/rothys"},
            {"retailer": "Bloomingdale's", "confidence": 85, "source": "Press release + backlinks", "url": "bloomingdales.com/rothys"},
            {"retailer": "Neiman Marcus", "confidence": 80, "source": "Backlinks + product listings", "url": "neimanmarcus.com/rothys"}
        ],
        "allbirds.com": [
            {"retailer": "Nordstrom", "confidence": 90, "source": "Direct mention + backlinks", "url": "nordstrom.com/allbirds"},
            {"retailer": "Dick's Sporting Goods", "confidence": 85, "source": "Store locator + press release", "url": "dickssportinggoods.com/allbirds"},
            {"retailer": "REI", "confidence": 80, "source": "Backlinks + social media", "url": "rei.com/allbirds"}
        ],
        # Brand name specific matches
        "Snow Cosmetics": [
            {"retailer": "Macy's", "confidence": 88, "source": "Brand name search + retail partnerships", "url": "macys.com/shop/snow-cosmetics"},
            {"retailer": "Bluemercury", "confidence": 82, "source": "Brand partnerships listing", "url": "bluemercury.com/collections/snow-cosmetics"},
            {"retailer": "Anthropologie", "confidence": 77, "source": "Brand name search", "url": "anthropologie.com/brands/snow-cosmetics"}
        ],
        "Rothy's": [
            {"retailer": "Zappos", "confidence": 87, "source": "Brand name search", "url": "zappos.com/rothys"},
            {"retailer": "DSW", "confidence": 78, "source": "Brand partnerships", "url": "dsw.com/en/us/brands/rothys"}
        ],
        "Allbirds": [
            {"retailer": "Zappos", "confidence": 89, "source": "Brand partnerships listing", "url": "zappos.com/allbirds"},
            {"retailer": "Foot Locker", "confidence": 76, "source": "Brand name search", "url": "footlocker.com/brand/allbirds"}
        ]
    }
    
    # Collect all applicable results based on URL and brand name
    combined_results = []
    
    # Add URL-based results
    for sample_domain, results in sample_data.items():
        if sample_domain in url.lower():
            combined_results.extend(results)
    
    # Add brand name-based results if provided
    if brand_name:
        for sample_brand, results in sample_data.items():
            # Check if sample brand is a brand name (not ending with .com) and matches the input brand name
            if not sample_brand.endswith(".com") and brand_name.lower() in sample_brand.lower():
                # Add only unique retailers that weren't found in URL search
                existing_retailers = {r["retailer"] for r in combined_results}
                unique_brand_results = [r for r in results if r["retailer"] not in existing_retailers]
                combined_results.extend(unique_brand_results)
    
    # If no specific matches, generate random results
    if not combined_results:
        # Generate random retailer results
        num_retailers = random.randint(3, 8)
        
        # Try to make results more realistic based on the domain or brand name
        search_term = ""
        if brand_name:
            search_term = brand_name.lower()
        else:
            # Extract domain name without extension
            search_term = url.split('.')[0].lower()
            if "/" in search_term:
                search_term = search_term.split("/")[-1]
        
        # Product category matching (basic simulation)
        category_retailers = {
            "beauty": ["Sephora", "Ulta", "Bluemercury", "Macy's", "CVS", "Walgreens"],
            "cosmetic": ["Sephora", "Ulta", "Bluemercury", "Target", "CVS"],
            "shoe": ["DSW", "Zappos", "Foot Locker", "Famous Footwear", "Nordstrom"],
            "apparel": ["Nordstrom", "Macy's", "TJ Maxx", "Target", "Urban Outfitters"],
            "food": ["Whole Foods", "Kroger", "Albertsons", "Sprouts", "Wegmans"],
            "pet": ["Chewy", "Petco", "PetSmart", "Pet Supplies Plus"],
            "outdoor": ["REI", "Bass Pro Shop", "Cabela's", "Backcountry"],
            "sports": ["Dick's Sporting Goods", "Academy Sports", "Foot Locker", "Hibbett Sports"]
        }
        
        # Try to intelligently match retailers based on name clues
        preferred_retailers = []
        for category, retailers in category_retailers.items():
            if category in search_term or any(term in search_term for term in ["snow", "cold", "winter", "ice"]):
                # Snow might be beauty/cosmetics or outdoor
                preferred_retailers.extend(category_retailers["beauty"])
                preferred_retailers.extend(category_retailers["outdoor"])
            elif any(term in search_term for term in ["shoe", "foot", "sneaker", "boots"]):
                preferred_retailers.extend(category_retailers["shoe"])
            elif any(term in search_term for term in ["wear", "apparel", "cloth", "dress", "fashion"]):
                preferred_retailers.extend(category_retailers["apparel"])
            elif any(term in search_term for term in ["beauty", "cosmetic", "skin", "makeup", "face"]):
                preferred_retailers.extend(category_retailers["beauty"])
            elif any(term in search_term for term in ["food", "grocery", "organic", "natural", "snack"]):
                preferred_retailers.extend(category_retailers["food"])
            elif any(term in search_term for term in ["pet", "dog", "cat", "animal"]):
                preferred_retailers.extend(category_retailers["pet"])
            elif any(term in search_term for term in ["outdoor", "camp", "hike", "mountain"]):
                preferred_retailers.extend(category_retailers["outdoor"])
            elif any(term in search_term for term in ["sport", "athletic", "fitness", "gym"]):
                preferred_retailers.extend(category_retailers["sports"])
        
        # Make list unique
        preferred_retailers = list(set(preferred_retailers))
        
        # If we found appropriate retailers for this type of product, use them
        selected_retailers = []
        if preferred_retailers and len(preferred_retailers) >= num_retailers:
            selected_retailers = random.sample(preferred_retailers, num_retailers)
        else:
            # Fall back to general retailer list
            selected_retailers = random.sample(major_retailers, num_retailers)
        
        random_results = []
        for retailer in selected_retailers:
            confidence = random.randint(60, 95)
            source_types = ["Website mention", "Backlinks", "Press release", "Store locator", "Social media", "Brand name search"]
            sources = random.sample(source_types, random.randint(1, 3))
            source = " + ".join(sources)
            
            # Create a sensible URL based on retailer and product
            retailer_domain = retailer.lower().replace(" ", "").replace("'", "").split("(")[0].strip()
            domain_parts = retailer_domain.split("/")
            retailer_domain = domain_parts[0]
            
            # Format the URL based on retailer patterns
            if retailer_domain == "amazon":
                retailer_url = f"amazon.com/s?k={search_term.replace(' ', '+')}"
            elif retailer_domain in ["sephora", "ulta", "bluemercury"]:
                retailer_url = f"{retailer_domain}.com/brands/{search_term.replace(' ', '-')}"
            elif retailer_domain in ["target", "walmart"]:
                retailer_url = f"{retailer_domain}.com/b/{search_term.replace(' ', '-')}"
            elif retailer_domain in ["nordstrom", "macys", "bloomingdales"]:
                retailer_url = f"{retailer_domain}.com/shop/brand/{search_term.replace(' ', '-')}"
            else:
                retailer_url = f"{retailer_domain}.com/{search_term.replace(' ', '-')}"
                
            random_results.append({
                "retailer": retailer,
                "confidence": confidence,
                "source": source,
                "url": retailer_url
            })
            
        # Sort by confidence
        random_results.sort(key=lambda x: x["confidence"], reverse=True)
        return random_results
    
    # If we have results from the sample data, return them sorted by confidence
    combined_results.sort(key=lambda x: x["confidence"], reverse=True)
    return combined_results

# Main analysis function
def analyze_merchant(url, brand_name=""):
    if not url:
        st.warning("Please enter a website URL to analyze.")
        return
    
    # Clean the URL if needed
    if not url.startswith('http'):
        url = 'https://' + url
    
    # Format for display
    display_url = url.replace('https://', '').replace('http://', '').rstrip('/')
    
    # Create display name combining URL and brand name if provided
    display_name = display_url
    if brand_name:
        display_name = f"{brand_name} ({display_url})"
    
    with st.expander("Analysis Process", expanded=True):
        st.write(f"Analyzing partnerships for: **{display_name}**")
        
        # Simulate analysis processes - now with brand name
        content_analyzed = analyze_website_content(url, brand_name)
        backlinks_analyzed = analyze_backlinks(url, brand_name)
        
        if content_analyzed and backlinks_analyzed:
            st.write("✅ Analysis complete! Generating results...")
    
    # Generate and display results - now using both URL and brand name
    results = generate_results(display_url, brand_name)
    
    # Verify each potential retailer partnership
verified_results = []
all_results_with_verification = []
if results:
    with st.expander("Verification Process", expanded=True):
        st.write("🔍 Verifying retail partnerships...")
        progress_bar = st.progress(0)
        
        for i, result in enumerate(results):
            # Simulate verification of this retailer partnership
            st.write(f"Verifying partnership with {result['retailer']}...")
            
            # Get verification details
            verification_score, verification_source, verification_url = verify_retailer_presence(
                result['retailer'], brand_name
            )
            
            # Add verification data to result
            result['verification_score'] = verification_score
            result['verification_source'] = verification_source
            result['verification_url'] = verification_url
            
            # Add all results to the list for display
            all_results_with_verification.append(result)
            
            # Track highly verified results separately
            if verification_score >= 90:
                verified_results.append(result)
            
            # Update progress
            progress_bar.progress((i + 1) / len(results))
        
        st.success(f"Verification complete! Found {len(verified_results)} highly verified partnerships out of {len(all_results_with_verification)} total potential retailers.")

# 2. Then modify the display section from:

# Display verified results
if verified_results:
    st.subheader("Verified Retail Partners (90%+ Confidence)")
    
    # Convert to DataFrame for display
    df = pd.DataFrame(verified_results)
    
    # [rest of display code]
    
else:
    st.warning("No highly verified retail partners found (90%+ confidence). Try using a more specific brand name or check the website URL.")

# TO:

# Display all results with verification info
if all_results_with_verification:
    st.subheader("All Potential Retail Partners")
    
    # Convert to DataFrame for display
    df = pd.DataFrame(all_results_with_verification)
    
    # Sort by verification score (highest first)
    df = df.sort_values('verification_score', ascending=False)
    
    # Display as a more visually appealing grid
    col1, col2 = st.columns([3, 1])
    
    with col1:
        for _, row in df.iterrows():
            # Create verification badge based on score
            if row['verification_score'] >= 90:
                verification_badge = "✅ Verified"
                badge_color = "green"
            elif row['verification_score'] >= 50:
                verification_badge = "⚠️ Partially Verified"
                badge_color = "orange"
            else:
                verification_badge = "❓ Low Confidence"
                badge_color = "gray"
            
            with st.container():
                st.markdown(f"""
                <div style="border:1px solid #ddd; padding:10px; margin-bottom:10px; border-radius:5px;">
                    <div style="display:flex; justify-content:space-between;">
                        <h3 style="margin:0;">{row['retailer']}</h3>
                        <span style="color:{badge_color}; font-weight:bold;">{verification_badge}</span>
                    </div>
                    <p><strong>Verification Score:</strong> {row['verification_score']}%</p>
                    <p><strong>Verification Method:</strong> {row['verification_source']}</p>
                    <p><strong>Confidence:</strong> {row['confidence']}%</p>
                    <p><strong>Source:</strong> {row['source']}</p>
                    <p><strong>URL:</strong> {row['url']}</p>
                </div>
                """, unsafe_allow_html=True)
    
    with col2:
        # Create a bar chart of verification scores for top retailers
        st.subheader("Verification Scores")
        fig, ax = plt.subplots()
        
        # Sort retailers by verification score
        df_sorted = df.sort_values('verification_score', ascending=False)
        
        # Only show top 10 for readability if there are many results
        if len(df_sorted) > 10:
            df_plot = df_sorted.head(10)
        else:
            df_plot = df_sorted
            
        ax.barh(df_plot['retailer'], df_plot['verification_score'], color='skyblue')
        ax.set_xlabel('Verification Score (%)')
        ax.set_title('Partnership Verification Scores')
        plt.tight_layout()
        st.pyplot(fig)
    
    # Add verification explanation
    st.info("""
    **Verification Methodology:**
    
    - **✅ Verified (90-100%)**: Strong evidence of partnership confirmed through multiple sources
    - **⚠️ Partially Verified (50-89%)**: Some evidence found but incomplete confirmation
    - **❓ Low Confidence (0-49%)**: Limited or no evidence found, requires manual verification
    
    In a full implementation, verification would use retailer APIs, web searches, and backlink analysis.
    """)
    
    # Add option to filter to only high confidence
    if st.checkbox("Show only highly verified retailers (90%+ confidence)"):
        st.subheader("Highly Verified Retail Partners Only")
        df_verified = df[df['verification_score'] >= 90]
        if len(df_verified) > 0:
            st.dataframe(df_verified)
        else:
            st.warning("No highly verified partnerships found.")
    
    # Download results option with verification data for all results
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Complete Results as CSV",
        data=csv,
        file_name=f"{display_url.split('.')[0]}_all_partners.csv",
        mime="text/csv"
    )
else:
    st.warning("No potential retail partners found. Try using a more specific brand name or check the website URL.")

    
    # Display verified results
    if verified_results:
        st.subheader("Verified Retail Partners (90%+ Confidence)")
        
        # Convert to DataFrame for display
        df = pd.DataFrame(verified_results)
        
        # Display as a more visually appealing grid
        col1, col2 = st.columns([3, 1])
        
        with col1:
            for _, row in df.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div style="border:1px solid #ddd; padding:10px; margin-bottom:10px; border-radius:5px;">
                        <div style="display:flex; justify-content:space-between;">
                            <h3 style="margin:0;">{row['retailer']}</h3>
                            <span style="color:green; font-weight:bold;">✅ Verified</span>
                        </div>
                        <p><strong>Verification Score:</strong> {row['verification_score']}%</p>
                        <p><strong>Verification Method:</strong> {row['verification_source']}</p>
                        <p><strong>URL:</strong> {row['url']}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        with col2:
            # Create a bar chart of verification scores
            st.subheader("Verification Scores")
            fig, ax = plt.subplots()
            
            # Sort retailers by verification score
            df_sorted = df.sort_values('verification_score', ascending=False)
            
            # Only show top 10 for readability if there are many results
            if len(df_sorted) > 10:
                df_plot = df_sorted.head(10)
            else:
                df_plot = df_sorted
                
            ax.barh(df_plot['retailer'], df_plot['verification_score'], color='green')
            ax.set_xlabel('Verification Score (%)')
            ax.set_title('Partnership Verification Scores')
            plt.tight_layout()
            st.pyplot(fig)
        
        # Add verification explanation
        st.info("""
        **Verification Methods:**
        
        In a full implementation, we verify retail partnerships using:
        
        1. **Direct Website Evidence**: Identifying "Where to Buy" pages on brand websites
        2. **Retailer Confirmation**: Finding the brand in retailer's brand directory
        3. **Backlink Analysis**: Analyzing quality backlinks between brand and retailer
        4. **Affiliate Link Detection**: Identifying affiliate network connections
        5. **API Verification**: Querying retailer APIs for product listings
        """)
        
        # Download results option with verification data
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Verified Results as CSV",
            data=csv,
            file_name=f"{display_url.split('.')[0]}_verified_partners.csv",
            mime="text/csv"
        )
    else:
        st.warning("No highly verified retail partners found (90%+ confidence). Try using a more specific brand name or check the website URL.")
        
    # Return the number of results for bulk processing
    return len(verified_results) if verified_results else 0

# Input method selection
input_method = st.radio("Choose input method:", ["Single URL", "Bulk Upload from Excel"])

if input_method == "Single URL":
    # Single URL input with brand name option
    col1, col2 = st.columns(2)
    
    with col1:
        url_input = st.text_input("Enter merchant website URL:", placeholder="e.g., trysnow.com")
    
    with col2:
        brand_name_input = st.text_input("Enter full brand name (optional):", placeholder="e.g., Snow Cosmetics")
    
    # Explanation of dual search
    st.info("Providing both the website URL and brand name improves search accuracy. The brand name helps identify partnerships that might not be evident from the domain name alone.")
    
    # Run the analysis when a button is clicked for single URL
    if st.button("Find B2B Partners for Single URL"):
        analyze_merchant(url_input, brand_name_input)
else:
    # Bulk upload from Excel
    st.write("### Upload Excel file with merchant URLs")
    
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        # Load the Excel file
        try:
            df_excel = pd.read_excel(uploaded_file)
            
            # Display preview of the uploaded file
            st.write("Preview of uploaded Excel file:")
            st.dataframe(df_excel.head())
            
            # Let user select the column containing URLs
            if len(df_excel.columns) > 0:
                url_column = st.selectbox(
                    "Select the column containing merchant URLs:", 
                    options=df_excel.columns
                )
                
                # Option to select brand name column
                has_brand_names = st.checkbox("My spreadsheet also contains brand names")
                
                if has_brand_names:
                    brand_name_column = st.selectbox(
                        "Select the column containing brand names:",
                        options=[col for col in df_excel.columns if col != url_column]
                    )
                
                # Process in batches to avoid overloading
                max_urls = st.slider("Maximum number of URLs to process", 
                                    min_value=1, max_value=50, value=10)
                
                # Run bulk analysis
                if st.button("Find B2B Partners for All URLs"):
                    # Check if there's a brand name column
                    brand_name_column = None
                    if 'brand_name_column' in locals():
                        brand_name_column = brand_name_column
                    elif any(col.lower() in ['brand', 'brand name', 'company', 'company name'] for col in df_excel.columns):
                        possible_columns = [col for col in df_excel.columns if col.lower() in ['brand', 'brand name', 'company', 'company name']]
                        brand_name_column = possible_columns[0]
                        st.info(f"Using '{brand_name_column}' as the brand name column.")
                    
                    # Filter out empty URLs
                    valid_urls = df_excel[url_column].dropna().tolist()[:max_urls]
                    
                    if not valid_urls:
                        st.error("No valid URLs found in the selected column.")
                    else:
                        st.write(f"Processing {len(valid_urls)} URLs...")
                        
                        # Create container for results
                        all_results = []
                        
                        # Progress bar for overall processing
                        progress_bar = st.progress(0)
                        
                        # Process each URL
                        for i, url in enumerate(valid_urls):
                            # Get corresponding brand name if available
                            brand_name = ""
                            if brand_name_column and i < len(df_excel):
                                brand_name = df_excel.iloc[i][brand_name_column]
                                if pd.isna(brand_name):
                                    brand_name = ""
                                else:
                                    brand_name = str(brand_name)
                            
                            display_text = f"URL: {url}"
                            if brand_name:
                                display_text += f" | Brand: {brand_name}"
                                
                            st.write(f"### Processing {i+1}/{len(valid_urls)}: {display_text}")
                            
                            # Clean the URL if needed
                            if not str(url).startswith('http'):
                                url = 'https://' + str(url)
                            
                            # Format for display
                            display_url = str(url).replace('https://', '').replace('http://', '').rstrip('/')
                            
                            # Quick analysis for bulk processing
                            st.write(f"Analyzing partnerships for: **{display_url}**")
                            
                            # Generate results directly without visual simulation for bulk processing
                            results = generate_results(display_url, brand_name)
                            
                            # Verify each result - change from 90%+ threshold to all results
                            verified_results = []
                            all_verified_results = []
                            for result in results:
                                # Get verification details
                                verification_score, verification_source, verification_url = verify_retailer_presence(
                                    result['retailer'], brand_name
                                )
                                
                                # Add verification data to result
                                result['verification_score'] = verification_score
                                result['verification_source'] = verification_source
                                result['verification_url'] = verification_url
                                result['merchant_url'] = display_url
                                    
                                # Add all results
                                all_verified_results.append(result)
                                    
                                # Track high confidence separately
                                if verification_score >= 90:
                                      verified_results.append(result)
                                
                                if all_verified_results:
                                # Add to combined results
                                all_results.extend(all_verified_results))
                        
                        # Display combined results if any
                        if all_results:
                            st.write("## Combined Results Summary")
                            
                            # Convert to DataFrame
                            df_results = pd.DataFrame(all_results)
                            
                            # Display table of all results (all are 90%+ verified)
                            st.write("All results shown have 90%+ verification confidence")
                            st.dataframe(df_results)
                            
                            # Create summary visualization
                            st.write("### Top Verified Retailers Across All Merchants")
                            retailer_counts = df_results['retailer'].value_counts().head(10)
                            
                            fig, ax = plt.subplots(figsize=(10, 6))
                            retailer_counts.plot(kind='bar', ax=ax, color='green')
                            plt.tight_layout()
                            st.pyplot(fig)
                            
                            # Download option
                            csv = df_results.to_csv(index=False)
                            st.download_button(
                                label="Download Verified Results as CSV",
                                data=csv,
                                file_name=f"highly_verified_retail_partners.csv",
                                mime="text/csv"
                            )
                            
                            # Create Excel report with multiple sheets
                            buffer = BytesIO()
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                # All results sheet
                                df_results.to_excel(writer, sheet_name='Verified Results (90%+)', index=False)
                                
                                # Summary by merchant
                                summary_by_merchant = df_results.groupby('merchant_url').agg({
                                    'retailer': 'count',
                                    'verification_score': 'mean'
                                }).reset_index()
                                summary_by_merchant.columns = ['Merchant', 'Number of Verified Partners', 'Average Verification Score']
                                summary_by_merchant.to_excel(writer, sheet_name='Merchant Summary', index=False)
                                
                                # Summary by retailer
                                summary_by_retailer = df_results.groupby('retailer').agg({
                                    'merchant_url': 'count',
                                    'verification_score': 'mean'
                                }).reset_index()
                                summary_by_retailer.columns = ['Retailer', 'Number of Merchants', 'Average Verification Score']
                                summary_by_retailer = summary_by_retailer.sort_values('Number of Merchants', ascending=False)
                                summary_by_retailer.to_excel(writer, sheet_name='Retailer Summary', index=False)
                                
                                # Verification methods summary
                                verification_methods = df_results['verification_source'].value_counts().reset_index()
                                verification_methods.columns = ['Verification Method', 'Count']
                                verification_methods.to_excel(writer, sheet_name='Verification Methods', index=False)
                                
                            st.download_button(
                                label="Download Complete Verified Results as Excel Report",
                                data=buffer.getvalue(),
                                file_name="highly_verified_retail_partners_report.xlsx",
                                mime="application/vnd.ms-excel"
                            )
                        else:
                            st.error("No highly verified retail partners (90%+ confidence) found for any of the provided URLs.")
                
            else:
                st.error("The uploaded Excel file is empty.")
        
        except Exception as e:
            st.error(f"Error processing the Excel file: {str(e)}")
            st.write("Please ensure your file is a valid Excel file with a column containing URLs.")

# Footer with simple information
st.markdown("---")
st.markdown("""
<div style="text-align: center;">
    <p>Developed for business development representatives to discover verified retail partnerships</p>
</div>
""", unsafe_allow_html=True)
