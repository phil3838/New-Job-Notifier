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
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse
from pathlib import Path

load_dotenv(Path(__file__).parent/'.env')

JSON_FILE_PATH = './job_listings/flare.json'
CONFIG = {
    'FLARE_CAREER_PAGE': os.getenv('FLARE_CAREER_PAGE'),
    'DISCORD_WEBHOOK': os.getenv('DISCORD_WEBHOOK_URL'),
    'DISCORD_AVATAR': os.getenv('DISCORD_AVATAR_URL', '')
}


logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def validate_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def scrape_with_selenium():
    driver = None
    try:
        driver = setup_driver()
        
        if not validate_url(CONFIG['FLARE_CAREER_PAGE']):
            raise ValueError(f"Invalid URL: CONFIG['FLARE_CAREER_PAGE']")

        url=str(CONFIG['FLARE_CAREER_PAGE'])
        driver.get(url)
        time.sleep(20)

        final_html = driver.page_source
        soup = BeautifulSoup(final_html, 'html.parser')
        
        job_selectors = [
            '.BambooHR-ATS-Jobs-Item',
            '.job-listing',
        ]

        for selector in job_selectors:
            elements = soup.select(selector)
            if elements:
                text = elements[0].get_text(strip=True)[:100]

        all_links = soup.find_all('a', href=True)
        job_links = []
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if any(keyword in href.lower() or keyword in text.lower() for keyword in ['job', 'career', 'position', 'apply']):
                job_links.append((text, href))

        
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        job_data = []
        if os.path.exists(JSON_FILE_PATH) and os.path.getsize(JSON_FILE_PATH) > 0:
            try:
                with open(JSON_FILE_PATH, 'r') as file:
                    job_data = json.load(file)
            except json.JSONDecodeError:
                logging.warning("Existing JSON file was corrupted, starting fresh")
        
        
                 
        if job_links:
            job_links_dict = {
                text: href for text, href in job_links
                if text.lower() not in ['careers', 'apply'] and text.strip()
            }
            
            new_jobs = compare_jobs(job_data, job_links_dict)
        
            if new_jobs:
                send_discord_notification(new_jobs)

            today_entry = {
                "date": current_date,
                "jobs": job_links_dict
            }
            job_data.append(today_entry)

        with open(JSON_FILE_PATH, 'w') as file:
            json.dump(job_data, file, indent=4)

        return final_html

    except Exception as e:
        logging.error(f"Scraping failed: {str(e)}", exc_info=True)
        return None
    finally:
        if driver:
            driver.quit()

def send_discord_notification(new_jobs):
    if not new_jobs:
        return
    
    message = "🚀 **New Job Postings Detected @ Flare**\n\n"
    for job_title, job_url in new_jobs.items():
        if job_url.startswith('//'):
            job_url = f"https:{job_url}"
            
            message += f"• [{job_title}]({job_url})\n"
    
    payload = {
        "content": message,
        "username": "Job Announcer"
        ""
    }
    
    try:
        response = requests.post(CONFIG['DISCORD_WEBHOOK'], json=payload)
        response.raise_for_status()
        logging.info("Discord notification sent successfully")
    except Exception as e:
        logging.error(f"Failed to send Discord notification: {e}")
        
def compare_jobs(previous_jobs, current_jobs):
    if not previous_jobs:
        return current_jobs
    
    latest_previous_jobs = previous_jobs[-1]["jobs"] if previous_jobs else {}
    
    new_jobs = {
        title: url for title, url in current_jobs.items()
        if title not in latest_previous_jobs
    }
    
    return new_jobs

if __name__ == "__main__":
    try:
        html_content = scrape_with_selenium()
        if html_content:
            logging.info("Scraping completed successfully!")
        else:
            logging.error("Scraping failed!")
            
    except Exception as e:
        logging.error(f"Fatal error in main: {e}", exc_info=True)
