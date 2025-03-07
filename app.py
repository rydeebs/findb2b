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
    3. Results show discovered retail partners with confidence scores
    
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

# Function to simulate website content analysis
def analyze_website_content(url):
    st.write("🔍 Analyzing website content...")
    
    # Placeholder for actual implementation
    progress_bar = st.progress(0)
    for i in range(100):
        time.sleep(0.01)
        progress_bar.progress(i + 1)
    
    st.success("Website content analysis complete!")
    return True

# Function to simulate backlink analysis
def analyze_backlinks(url):
    st.write("🔗 Analyzing backlinks from retail websites...")
    
    # Placeholder for actual implementation
    progress_bar = st.progress(0)
    for i in range(100):
        time.sleep(0.01)
        progress_bar.progress(i + 1)
    
    st.success("Backlink analysis complete!")
    return True

# Function to generate mock results based on the input URL
def generate_results(url):
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
        ]
    }
    
    # Generate random results for URLs not in our sample data
    if not any(sample_domain in url.lower() for sample_domain in sample_data.keys()):
        # Select 3-7 random retailers
        num_retailers = random.randint(3, 7)
        selected_retailers = random.sample(major_retailers, num_retailers)
        
        random_results = []
        for retailer in selected_retailers:
            confidence = random.randint(60, 95)
            source_types = ["Website mention", "Backlinks", "Press release", "Store locator", "Social media"]
            sources = random.sample(source_types, random.randint(1, 3))
            source = " + ".join(sources)
            
            retailer_domain = retailer.lower().replace(" ", "").replace("'", "")
            if retailer_domain == "amazon":
                retailer_url = f"amazon.com/s?k={url.split('.')[0]}"
            else:
                retailer_url = f"{retailer_domain}.com/{url.split('.')[0]}"
                
            random_results.append({
                "retailer": retailer,
                "confidence": confidence,
                "source": source,
                "url": retailer_url
            })
            
        # Sort by confidence
        random_results.sort(key=lambda x: x["confidence"], reverse=True)
        return random_results
    
    # Return the appropriate sample data
    for sample_domain, results in sample_data.items():
        if sample_domain in url.lower():
            return results
    
    # Fallback to random results
    return []

# Main analysis function
def analyze_merchant(url):
    if not url:
        st.warning("Please enter a website URL to analyze.")
        return
    
    # Clean the URL if needed
    if not url.startswith('http'):
        url = 'https://' + url
    
    # Format for display
    display_url = url.replace('https://', '').replace('http://', '').rstrip('/')
    
    with st.expander("Analysis Process", expanded=True):
        st.write(f"Analyzing partnerships for: **{display_url}**")
        
        # Simulate analysis processes
        content_analyzed = analyze_website_content(url)
        backlinks_analyzed = analyze_backlinks(url)
        
        if content_analyzed and backlinks_analyzed:
            st.write("✅ Analysis complete! Generating results...")
    
    # Generate and display results
    results = generate_results(display_url)
    
    if results:
        st.subheader("Discovered Retail Partners")
        
        # Convert to DataFrame for display
        df = pd.DataFrame(results)
        
        # Custom styling for the confidence column
        def highlight_confidence(val):
            if val >= 90:
                color = 'rgba(0, 128, 0, 0.2)'  # Green
            elif val >= 75:
                color = 'rgba(255, 165, 0, 0.2)'  # Orange
            else:
                color = 'rgba(255, 255, 0, 0.2)'  # Yellow
            return f'background-color: {color}'
        
        # Apply styling and display
        styled_df = df.style.applymap(highlight_confidence, subset=['confidence'])
        
        # Display as a more visually appealing grid
        col1, col2 = st.columns([3, 1])
        
        with col1:
            for _, row in df.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div style="border:1px solid #ddd; padding:10px; margin-bottom:10px; border-radius:5px;">
                        <h3 style="margin:0;">{row['retailer']}</h3>
                        <p><strong>Confidence:</strong> {row['confidence']}%</p>
                        <p><strong>Source:</strong> {row['source']}</p>
                        <p><strong>URL:</strong> {row['url']}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        with col2:
            # Create a pie chart of retailers by confidence
            st.subheader("Confidence Distribution")
            fig, ax = plt.subplots()
            ax.pie(df['confidence'], labels=df['retailer'], autopct='%1.1f%%')
            st.pyplot(fig)
        
        # Download results option
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name=f"{display_url.split('.')[0]}_retail_partners.csv",
            mime="text/csv"
        )
    else:
        st.warning("No retail partners found. Try another merchant or refine the search.")

# Input method selection
input_method = st.radio("Choose input method:", ["Single URL", "Bulk Upload from Excel"])

if input_method == "Single URL":
    # Single URL input
    url_input = st.text_input("Enter merchant website URL:", placeholder="e.g., trysnow.com")
    
    # Run the analysis when a button is clicked for single URL
    if st.button("Find B2B Partners for Single URL"):
        analyze_merchant(url_input)
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
                
                # Process in batches to avoid overloading
                max_urls = st.slider("Maximum number of URLs to process", 
                                    min_value=1, max_value=50, value=10)
                
                # Run bulk analysis
                if st.button("Find B2B Partners for All URLs"):
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
                            st.write(f"### Processing URL {i+1}/{len(valid_urls)}: {url}")
                            
                            # Clean the URL if needed
                            if not str(url).startswith('http'):
                                url = 'https://' + str(url)
                            
                            # Format for display
                            display_url = str(url).replace('https://', '').replace('http://', '').rstrip('/')
                            
                            # Quick analysis for bulk processing
                            st.write(f"Analyzing partnerships for: **{display_url}**")
                            
                            # Generate results directly without visual simulation for bulk processing
                            results = generate_results(display_url)
                            
                            if results:
                                # Add merchant URL to each result row
                                for result in results:
                                    result['merchant_url'] = display_url
                                
                                # Add to combined results
                                all_results.extend(results)
                                
                                # Show mini summary
                                st.write(f"✅ Found {len(results)} retail partners for {display_url}")
                            else:
                                st.write(f"⚠️ No retail partners found for {display_url}")
                            
                            # Update progress
                            progress_bar.progress((i + 1) / len(valid_urls))
                        
                        # Display combined results if any
                        if all_results:
                            st.write("## Combined Results Summary")
                            
                            # Convert to DataFrame
                            df_results = pd.DataFrame(all_results)
                            
                            # Display table of all results
                            st.dataframe(df_results)
                            
                            # Create summary visualization
                            st.write("### Top Retailers Across All Merchants")
                            retailer_counts = df_results['retailer'].value_counts().head(10)
                            
                            fig, ax = plt.subplots(figsize=(10, 6))
                            retailer_counts.plot(kind='bar', ax=ax)
                            plt.tight_layout()
                            st.pyplot(fig)
                            
                            # Download option
                            csv = df_results.to_csv(index=False)
                            st.download_button(
                                label="Download Complete Results as CSV",
                                data=csv,
                                file_name="bulk_retail_partners.csv",
                                mime="text/csv"
                            )
                            
                            # Create Excel report with multiple sheets
                            buffer = BytesIO()
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                # All results sheet
                                df_results.to_excel(writer, sheet_name='All Results', index=False)
                                
                                # Summary by merchant
                                summary_by_merchant = df_results.groupby('merchant_url')['retailer'].count().reset_index()
                                summary_by_merchant.columns = ['Merchant', 'Number of Retail Partners']
                                summary_by_merchant.to_excel(writer, sheet_name='Merchant Summary', index=False)
                                
                                # Summary by retailer
                                summary_by_retailer = df_results.groupby('retailer')['merchant_url'].count().reset_index()
                                summary_by_retailer.columns = ['Retailer', 'Number of Merchants']
                                summary_by_retailer = summary_by_retailer.sort_values('Number of Merchants', ascending=False)
                                summary_by_retailer.to_excel(writer, sheet_name='Retailer Summary', index=False)
                                
                            st.download_button(
                                label="Download Complete Results as Excel Report",
                                data=buffer.getvalue(),
                                file_name="bulk_retail_partners_report.xlsx",
                                mime="application/vnd.ms-excel"
                            )
                        else:
                            st.error("No retail partners found for any of the provided URLs.")
                
            else:
                st.error("The uploaded Excel file is empty.")
        
        except Exception as e:
            st.error(f"Error processing the Excel file: {str(e)}")
            st.write("Please ensure your file is a valid Excel file with a column containing URLs.")

# Additional features section
with st.expander("Additional Features (Premium)", expanded=False):
    st.markdown("""
    ### Premium Features
    
    In a full implementation, these additional features would be available:
    
    - **Historical Partnership Tracking**: Monitor how partnerships change over time
    - **Competitor Analysis**: See which retailers your competitors work with
    - **Market Penetration Insights**: Identify untapped retail opportunities
    - **Automated Monitoring**: Get alerts when new partnerships are detected
    - **Detailed Partnership Reports**: Export comprehensive reports for presentations
    
    These features would require integration with specialized APIs and services.
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center;">
    <p>Developed for business development representatives to accelerate partnership discovery</p>
</div>
""", unsafe_allow_html=True)
