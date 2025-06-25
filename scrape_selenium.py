import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import os
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def setup_driver():
    """Setup Chrome driver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_with_selenium():
    """Scrape the page using Selenium and save to files"""
    driver = None
    try:
        logging.info("Setting up Chrome driver...")
        driver = setup_driver()
        
        url = 'https://flare.io/company/careers/'
        logging.info(f"Navigating to: {url}")
        
        driver.get(url)
        
        time.sleep(5)
        
        logging.info("Waiting for JavaScript to load...")
        time.sleep(20)
        
        final_html = driver.page_source
        
        soup = BeautifulSoup(final_html, 'html.parser')
        
        if 'cloudflare' in final_html.lower() and 'challenge' in final_html.lower():
            logging.warning("🚨 Cloudflare challenge detected in page content")
        elif 'cloudflare' in final_html.lower():
            logging.info("Cloudflare present but no challenge detected")
        else:
            logging.info("✅ No Cloudflare detected")
        
        job_indicators = ['job', 'career', 'position', 'hiring', 'bamboohr', 'apply']
        logging.info("=== JOB CONTENT ANALYSIS ===")
        for indicator in job_indicators:
            count = final_html.lower().count(indicator)
            if count > 0:
                logging.info(f"Found '{indicator}' {count} times in page")
        
        elements_count = {
            'links': len(soup.find_all('a')),
            'divs': len(soup.find_all('div')),
            'spans': len(soup.find_all('span')),
            'list_items': len(soup.find_all('li')),
            'buttons': len(soup.find_all('button')),
            'forms': len(soup.find_all('form')),
            'scripts': len(soup.find_all('script'))
        }
        
        logging.info("=== ELEMENT COUNTS ===")
        for element, count in elements_count.items():
            logging.info(f"{element}: {count}")
    
        job_selectors = [
            '.BambooHR-ATS-Jobs-Item',
            '.job-listing',
            '.career-item',
            '.position-item',
            '[class*="job"]',
            '[class*="career"]'
        ]
        
        logging.info("=== JOB SELECTOR SEARCH ===")
        for selector in job_selectors:
            elements = soup.select(selector)
            if elements:
                logging.info(f"✅ Found {len(elements)} elements with selector '{selector}'")
                for i, elem in enumerate(elements[:3]):
                    text = elem.get_text(strip=True)[:100]
                    logging.info(f"   {i+1}. {text}")
            else:
                logging.info(f"❌ No elements found with selector '{selector}'")
        
        all_links = soup.find_all('a', href=True)
        job_links = []
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if any(keyword in href.lower() or keyword in text.lower() for keyword in ['job', 'career', 'position', 'apply']):
                job_links.append((text, href))
        
        json_file_path = 'job_listings.json'
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        if os.path.exists(json_file_path) and os.path.getsize(json_file_path) > 0:
            with open(json_file_path, 'r') as file:
                try:
                    job_data = json.load(file)
                except json.JSONDecodeError:
                    job_data=[]
        
        if job_links:
            job_links_dict = {text: href for text, href in job_links}
            
            today_entry = {
                "date": current_date,
                "jobs": job_links_dict
            }
            job_data.append(today_entry)
        
        with open(json_file_path, 'w') as file:
            json.dump(job_data, file, indent=4)
    
        logging.info(f"Saved {len(job_links)} job links to {json_file_path}")
        
        if job_links:
            logging.info(f"=== POTENTIAL JOB LINKS ({len(job_links)}) ===")
            for text, href in job_links[:10]:
                logging.info(f"Link: {text} -> {href}")
        
        return final_html
        
    except Exception as e:
        logging.error(f"Error in scraping: {e}")
        return None
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    logging.info("Starting scraper with Selenium...")
    html_content = scrape_with_selenium()
    
    if html_content:
        logging.info("✅ Scraping completed successfully!")
        logging.info("📁 Check the generated HTML files to inspect the content.")
    else:
        logging.error("❌ Scraping failed!")