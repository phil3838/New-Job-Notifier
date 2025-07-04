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

JSON_FILE_PATH = './job_listings/botpress.json'  
CONFIG = {
    'CAREER_PAGE_URL': os.getenv('BOTPRESS_CAREER_PAGE'),
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
        
        if not validate_url(CONFIG['CAREER_PAGE_URL']):
            raise ValueError(f"Invalid URL: {CONFIG['CAREER_PAGE_URL']}")

        url = str(CONFIG['CAREER_PAGE_URL'])
        driver.get(url)
        time.sleep(10)

        final_html = driver.page_source
        soup = BeautifulSoup(final_html, 'html.parser')
        
        job_items = soup.select('li.whr-item')

        job_links = []
        for item in job_items:
            title_element = item.select_one('h3.whr-title a')
            if not title_element:
                continue
            
            job_title = title_element.get_text(strip=True)
            job_url = title_element['href']
            
            location_element = item.select_one('li.whr-location')
            location = location_element.get_text(strip=True).replace('Location:','').strip() if location_element else ""
            
            department = ""
            prev_element = item.find_previous_sibling()
            while prev_element:
                if prev_element.name == 'h2' and 'whr-group' in prev_element.get('class', []):
                    department = prev_element.get_text(strip=True)
                    break
                prev_element = prev_element.find_previous_sibling()
            
            
            display_parts = []
            if department:
                display_parts.append(f"[{department}]")
            display_parts.append(job_title)
            if location:
                display_parts.append(f"- {location}")
            
            display_text = " ".join(display_parts)
            job_links.append((display_text, job_url))
            
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        job_data = []
        if os.path.exists(JSON_FILE_PATH) and os.path.getsize(JSON_FILE_PATH) > 0:
            try:
                with open(JSON_FILE_PATH, 'r') as file:
                    job_data = json.load(file)
            except:
                logging.warning("Existing JSON file was corrupted, starting fresh")
                    
        if job_links:
            job_links_dict = {
                text: href for text, href in job_links
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
    
    message = "🚀 **New Job Postings Detected @ Botpress**\n\n"
    for job_title, job_url in new_jobs.items():
        message += f"• [{job_title}]({job_url})\n"
        
    payload = {
        "content": message,
        "username": "Job Scraper Bot",
        "avatar_url": CONFIG['DISCORD_AVATAR']
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