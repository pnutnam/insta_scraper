import logging
import time
import re
from typing import Dict, Optional, List
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self):
        self.options = Options()
        self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
    def _get_driver(self):
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)

    def scrape_company_page(self, url: str) -> Dict[str, str]:
        """
        Scrapes a public LinkedIn company page for details.
        Returns a dictionary with extracted info.
        """
        logger.info(f"Scraping LinkedIn page: {url}")
        driver = None
        data = {
            "employee_count": None,
            "follower_count": None,
            "about": None,
            "location": None,
            "url": url
        }

        try:
            driver = self._get_driver()
            driver.get(url)
            
            # Wait for potential content load
            time.sleep(5)
            
            # Check for Authwall (redirect to login)
            current_url = driver.current_url
            if "linkedin.com/authwall" in current_url or "linkedin.com/login" in current_url:
                logger.warning("Hit LinkedIn Authwall/Login redirect. Public access blocked.")
                return data

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract Employee Count
            # Look for "10,001+ employees" or "View all X employees"
            # Often in a dd tag or specific class, but text search is more robust for public pages
            
            # Strategy 1: Look for "employees" text
            employee_text = soup.find(string=re.compile(r"[\d,]+\+?\s+employees", re.IGNORECASE))
            if employee_text:
                data["employee_count"] = employee_text.strip()
            
            # Strategy 2: Look for "View all X employees" link
            if not data["employee_count"]:
                view_all_link = soup.find('a', string=re.compile(r"View all.*employees", re.IGNORECASE))
                if view_all_link:
                    data["employee_count"] = view_all_link.get_text(strip=True).replace("View all", "").replace("employees", "").strip()

            # Extract Follower Count
            follower_text = soup.find(string=re.compile(r"[\d,]+\s+followers", re.IGNORECASE))
            if follower_text:
                data["follower_count"] = follower_text.strip()

            # Extract About
            # Often in a section with "About us" or similar
            about_section = soup.find('h2', string=re.compile(r"About", re.IGNORECASE))
            if about_section:
                # The text is usually in a sibling or parent's sibling
                # This is tricky on dynamic pages, try finding the paragraph following the header
                parent = about_section.find_parent()
                if parent:
                    about_text = parent.get_text(separator="\n", strip=True)
                    # Clean up the header itself
                    about_text = about_text.replace("About us", "").replace("About", "").strip()
                    data["about"] = about_text[:500] + "..." if len(about_text) > 500 else about_text
            
            # Fallback About: Look for meta description
            if not data["about"]:
                meta_desc = soup.find('meta', property='og:description')
                if meta_desc:
                    data["about"] = meta_desc.get('content')

            # Extract Location
            # Often in the "locations" section or near the top
            # This is harder to pinpoint without specific classes, but let's try a heuristic
            # Look for "Headquarters"
            hq_text = soup.find(string=re.compile(r"Headquarters", re.IGNORECASE))
            if hq_text:
                # Usually "Headquarters: City, State"
                parent = hq_text.find_parent()
                if parent:
                    data["location"] = parent.get_text(strip=True).replace("Headquarters", "").strip()

        except Exception as e:
            logger.error(f"Error scraping LinkedIn page {url}: {e}")
        finally:
            if driver:
                driver.quit()
        
        return data
