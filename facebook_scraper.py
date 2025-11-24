"""Module for scraping public Facebook pages using Selenium."""

import logging
import re
import time
from typing import Dict, Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from driver_utils import get_driver
import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FacebookScraper:
    """Scrapes public Facebook pages for contact info using Selenium."""

    def __init__(self):
        self.email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    def _get_driver(self):
        """Setup headless Chrome driver."""
        return get_driver()

    def scrape_page(self, url: str) -> Dict:
        """
        Scrape a Facebook page for contact info.
        
        Args:
            url: The Facebook page URL
            
        Returns:
            Dictionary with extracted data
        """
        results = {
            'emails': set(),
            'phones': [],
            'website': None
        }
        
        if not url or 'facebook.com' not in url:
            return self._format_results(results)

        driver = None
        try:
            logger.info(f"Scraping Facebook page with Selenium: {url}")
            driver = self._get_driver()
            driver.get(url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Handle Login Popup
            self._dismiss_login_popup(driver)
            
            # Scroll down to trigger lazy loading
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Get page source
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            text = soup.get_text(" ", strip=True)
            
            # 1. Extract Emails (Regex)
            emails = self.email_regex.findall(text)
            for email in emails:
                if len(email) < 50 and not email.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    results['emails'].add(email.lower())
            
            # Check mailto links
            for a in soup.find_all('a', href=True):
                if 'mailto:' in a['href']:
                    email = a['href'].replace('mailto:', '').split('?')[0]
                    if self.email_regex.match(email):
                        results['emails'].add(email.lower())

            # Check meta tags
            meta_email = soup.find('meta', property='og:email')
            if meta_email and meta_email.get('content'):
                results['emails'].add(meta_email['content'].lower())

            # 2. Extract Phones
            # Look for phone patterns in text
            # Simple regex for US numbers +1 or (xxx)
            phones = re.findall(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
            seen_phones = set()
            for p in phones:
                clean_p = re.sub(r'[^\d]', '', p)
                if len(clean_p) >= 10 and clean_p not in seen_phones:
                    results['phones'].append({
                        'number': p.strip(),
                        'label': 'Facebook Page',
                        'score': 5
                    })
                    seen_phones.add(clean_p)

            return self._format_results(results)
            
        except Exception as e:
            logger.warning(f"Failed to scrape Facebook page {url}: {e}")
            return self._format_results(results)
        finally:
            if driver:
                driver.quit()

    def _dismiss_login_popup(self, driver):
        """Try to close the login popup."""
        try:
            # Press ESC first, often works
            webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
            
            # Look for "Close" button (X icon)
            # Facebook changes these often, but usually it's a div with role="button" and aria-label="Close"
            close_btn = driver.find_elements(By.CSS_SELECTOR, '[aria-label="Close"]')
            if close_btn:
                close_btn[0].click()
                logger.info("Clicked Close button on popup")
                time.sleep(1)
                return

            # Sometimes it's a specific "Not Now" button
            not_now = driver.find_elements(By.XPATH, "//span[text()='Not Now']")
            if not_now:
                not_now[0].click()
                logger.info("Clicked Not Now button")
                time.sleep(1)
                
        except Exception as e:
            logger.debug(f"Popup dismissal failed (might not be present): {e}")

    def _format_results(self, results: Dict) -> Dict:
        return {
            'emails': list(results['emails']),
            'phones': results['phones'],
            'website': results['website']
        }
