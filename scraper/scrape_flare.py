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
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
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


def scrape_with_selenium():
    driver = None
    try:
        logging.info("Setting up Chrome driver...")
        driver = setup_driver()

        url = 'https://flare.io/company/careers/'
        driver.get(url)
        logging.info("Waiting for JavaScript to load...")
        time.sleep(20)

        final_html = driver.page_source
        soup = BeautifulSoup(final_html, 'html.parser')
        
        job_selectors = [
            '.BambooHR-ATS-Jobs-Item',
            '.job-listing',
        ]

        found_jobs = False
        for selector in job_selectors:
            elements = soup.select(selector)
            if elements:
                found_jobs = True
                if elements:
                    text = elements[0].get_text(strip=True)[:100]

        all_links = soup.find_all('a', href=True)
        job_links = []
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if any(keyword in href.lower() or keyword in text.lower() for keyword in ['job', 'career', 'position', 'apply']):
                job_links.append((text, href))

        json_file_path = './job_listings/flare.json'
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        job_data = []
        if os.path.exists(json_file_path) and os.path.getsize(json_file_path) > 0:
            try:
                with open(json_file_path, 'r') as file:
                    job_data = json.load(file)
            except json.JSONDecodeError:
                logging.warning("Existing JSON file was corrupted, starting fresh")

        if job_links:
            job_links_dict = {
                text: href for text, href in job_links
                if text.lower() not in ['careers', 'apply'] and text.strip()
            }

            today_entry = {
                "date": current_date,
                "jobs": job_links_dict
            }
            job_data.append(today_entry)

        with open(json_file_path, 'w') as file:
            json.dump(job_data, file, indent=4)

        return final_html

    except Exception as e:
        logging.error(f"Scraping failed: {str(e)}", exc_info=True)
        return None
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    html_content = scrape_with_selenium()
    if html_content:
        logging.info("Scraping completed - job listings updated")
    else:
        logging.error("Scraping failed - no data collected")
