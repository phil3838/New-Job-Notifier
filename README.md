# New Job Notifier

## Overview
This Python script monitors job listings on specific company websites and sends notifications via Discord when new job opportunities are discovered. Designed to be run as a cron job on Linux systems for automated job tracking.

## Features
- Web scraping of company job pages
- Tracking and comparing job listings daily
- JSON-based job listing storage
- Discord notifications for new job opportunities

## Prerequisites
- Python 3.10+
- Linux environment (recommended)


## Website Scraping Customization

### Important Note: Website Variability
Each company's website has a unique HTML structure, class names, and page architecture. This script serves as a **template model** that requires careful customization for each specific target website.

#### Typical Customization Points
- HTML element selectors
- CSS class names for job listings
- Handling dynamic content (JavaScript-rendered pages)
- URL parsing and link extraction
- Specific keyword matching for job links

## Environment Setup

### 1. Setup virtual environment (recommended):
```bash
   # Create the virtual environment
   python -m venv venv

   # Activate it
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
```

### 2. Install module dependencies

```ini
pip install -r requirements.txt
```


### 3. Create your `.env` file

Create a new file named `.env` in the `scraper/` directory with the following contents:

```ini
# Required variables
ANY_CAREER_PAGE=https://career.page/
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here

# Optional variables
DISCORD_AVATAR_URL=https://example.com/path/to/avatar.png
```

## Example Customization Process
```python
def scrape_specific_company_jobs(soup):
    job_links = []
    
    # Modify these selectors based on the specific website
    job_containers = soup.find_all('div', class_='job-listing-specific-class')
    
    for container in job_containers:
        job_title = container.find('h3', class_='job-title-class')
        job_link = container.find('a', class_='apply-link-class')
        
        # Custom filtering and processing
        if job_title and job_link:
            job_links.append((job_title.text, job_link['href']))
    
    return job_links
```