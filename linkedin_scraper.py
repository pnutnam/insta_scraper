import logging
import time
import re
from typing import Dict, Optional, List
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from driver_utils import get_driver

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self):
        pass
        
    def _get_driver(self):
        return get_driver()

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
            "url": url,
            "industry": None,
            "type": None,
            "specialties": None
        }

        try:
            driver = self._get_driver()
            
            # Google Referral Trick: Go to Google first
            logger.info("Navigating to Google first to simulate referral...")
            driver.get("https://www.google.com")
            time.sleep(2)
            
            # Now go to LinkedIn
            driver.get(url)
            
            # Wait for potential content load
            time.sleep(5)
            
            # Check for Authwall (redirect to login)
            current_url = driver.current_url
            if "linkedin.com/authwall" in current_url:
                logger.warning("Hit LinkedIn Authwall. Google referral trick failed.")
                return data

            # Popup Dismissal Logic
            try:
                # Look for common modal close buttons
                # 'button.modal__dismiss', 'button[aria-label="Dismiss"]', 'icon.mercado-match'
                close_buttons = driver.find_elements(By.CSS_SELECTOR, "button.modal__dismiss, button[aria-label='Dismiss'], button.contextual-sign-in-modal__modal-dismiss-btn")
                for btn in close_buttons:
                    if btn.is_displayed():
                        logger.info("Dismissing login popup...")
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(1)
            except Exception as e:
                logger.warning(f"Error dismissing popup: {e}")

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract Employee Count
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
            about_section = soup.find('h2', string=re.compile(r"About", re.IGNORECASE))
            if about_section:
                parent = about_section.find_parent()
                if parent:
                    about_text = parent.get_text(separator="\n", strip=True)
                    about_text = about_text.replace("About us", "").replace("About", "").strip()
                    data["about"] = about_text[:500] + "..." if len(about_text) > 500 else about_text
            
            # Fallback About
            if not data["about"]:
                meta_desc = soup.find('meta', property='og:description')
                if meta_desc:
                    data["about"] = meta_desc.get('content')

            # Extract Location
            hq_text = soup.find(string=re.compile(r"Headquarters", re.IGNORECASE))
            if hq_text:
                parent = hq_text.find_parent()
                if parent:
                    data["location"] = parent.get_text(strip=True).replace("Headquarters", "").strip()

            # Extract Additional Details (Industry, Type, Specialties)
            # Helper to find value by label
            def get_detail(label_pattern):
                # Strategy 1: Look for <dt> containing the label
                dt = soup.find('dt', string=re.compile(label_pattern, re.IGNORECASE))
                if dt:
                    dd = dt.find_next_sibling('dd')
                    if dd:
                        return dd.get_text(strip=True)
                
                # Strategy 2: Look for text node and check parent/siblings (fallback)
                label = soup.find(string=re.compile(label_pattern, re.IGNORECASE))
                if label:
                    parent = label.find_parent()
                    if parent:
                        next_sibling = parent.find_next_sibling()
                        if next_sibling:
                            return next_sibling.get_text(strip=True)
                return None

            data["industry"] = get_detail(r"^Industry$")
            data["type"] = get_detail(r"^Type$")
            data["specialties"] = get_detail(r"^Specialties$")
            
            # Fallback for Industry from top card if not found
            if not data["industry"]:
                subtitle = soup.find('div', class_=re.compile(r"top-card.*subtitle", re.IGNORECASE))
                if subtitle:
                    parts = [p.strip() for p in subtitle.get_text(separator="|").split("|") if p.strip()]
                    if parts and "," not in parts[0]:
                         data["industry"] = parts[0]

            # Refine Company Size
            if not data["employee_count"]:
                data["employee_count"] = get_detail(r"^Company size$")
            
            # Refine Location
            if not data["location"]:
                data["location"] = get_detail(r"^Headquarters$")
            
        except Exception as e:
            logger.error(f"Error scraping LinkedIn page {url}: {e}")
        finally:
            if driver:
                driver.quit()
        
        return data
