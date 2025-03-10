import os
import subprocess
import requests
from bs4 import BeautifulSoup
import streamlit as st
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import quote_plus

def ensure_chrome_installed():
    """Ensures Google Chrome is installed on Linux-based systems (e.g., Streamlit Cloud)."""
    if not os.path.exists("/usr/bin/google-chrome"):
        print("Installing Google Chrome...")
        subprocess.run("wget -qO- https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb > google-chrome.deb", shell=True)
        subprocess.run("sudo dpkg -i google-chrome.deb", shell=True)
        subprocess.run("sudo apt-get -f install -y", shell=True)

def search_google_shopping(brand_name, num_results=30):
    """
    Uses Selenium to scrape Google Shopping for retailer URLs.
    """
    ensure_chrome_installed()
    chromedriver_autoinstaller.install()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    query = brand_name.replace(" ", "+")
    search_url = f"https://www.google.com/search?tbm=shop&q={query}"
    driver.get(search_url)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    retailers = []
    brand_name_lower = brand_name.lower().replace(" ", "")
    
    for result in soup.find_all("a", href=True):
        url = result["href"]
        if "url?q=" in url and "google.com" not in url:
            clean_url = url.split("url?q=")[-1].split("&")[0]
            if brand_name_lower in clean_url.lower():
                retailers.append(clean_url)
            if len(retailers) >= num_results:
                break
    
    driver.quit()
    return retailers

def find_retailers_comprehensive(brand_name, brand_website=None, industry=None, product_skus=None, include_where_to_buy=True):
    all_retailers = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    progress_steps = 7
    current_step = 0
    
    status_text.text(f"Searching Google Shopping for {brand_name} products...")
    google_shopping_retailers = search_google_shopping(brand_name, num_results=30)
    
    for retailer in google_shopping_retailers:
        all_retailers.append({
            'Brand': brand_name,
            'Retailer': retailer.split('.')[0].capitalize(),
            'Domain': retailer,
            'Search_Source': "Google Shopping",
            'Link': retailer
        })
    
    progress_bar.progress(1.0)
    status_text.text(f"Found {len(all_retailers)} retailers carrying {brand_name}")
    
    return all_retailers
