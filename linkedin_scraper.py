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
            "specialties": None,
            "website": None,
            "company_size": None,
            "headquarters": None,
            "founded": None,
            "locations": [],  # Multiple locations
            "employees": []   # Employee list with name, title, profile_url
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

            
            # Scroll down to load ALL content (especially company details section)
            logger.info("Scrolling to load company details...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(3)
            
            # Refresh soup after scrolling to get all loaded content
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Save page HTML for debugging
            with open('/tmp/linkedin_page.html', 'w') as f:
                f.write(soup.prettify())
            
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

            # Extract Location (Headquarters)
            hq_text = soup.find(string=re.compile(r"Headquarters", re.IGNORECASE))
            if hq_text:
                parent = hq_text.find_parent()
                if parent:
                    data["location"] = parent.get_text(strip=True).replace("Headquarters", "").strip()

            # Extract Additional Details (Industry, Type, Specialties, Website, Founded)
            # Helper to find value by label
            def get_detail(label_pattern):
                # Strategy 1: Look for <dt> containing the label
                # Find all dt tags and check their text content
                all_dts = soup.find_all('dt')
                for dt in all_dts:
                    dt_text = dt.get_text(strip=True)
                    if re.match(label_pattern, dt_text, re.IGNORECASE):
                        dd = dt.find_next_sibling('dd')
                        if dd:
                            # For website, extract href from anchor if present
                            if 'Website' in label_pattern:
                                link = dd.find('a', href=True)
                                if link:
                                    return link.get_text(strip=True)
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
            data["website"] = get_detail(r"^Website$")
            data["founded"] = get_detail(r"^Founded$")
            
            # Fallback for Industry from top card if not found
            if not data["industry"]:
                subtitle = soup.find('div', class_=re.compile(r"top-card.*subtitle", re.IGNORECASE))
                if not subtitle:
                    # Try h2 with top-card-layout__headline class
                    subtitle = soup.find('h2', class_=re.compile(r"top-card-layout__headline"))
                if subtitle:
                    parts = [p.strip() for p in subtitle.get_text(separator="|").split("|") if p.strip()]
                    if parts and "," not in parts[0]:
                         data["industry"] = parts[0]

            # Refine Company Size
            if not data["employee_count"]:
                data["employee_count"] = get_detail(r"^Company size$")
            
            # Extract detailed company size
            company_size = get_detail(r"^Company size$")
            if company_size:
                data["company_size"] = company_size
            
            # Refine Location
            if not data["location"]:
                data["location"] = get_detail(r"^Headquarters$")
            
            # Set headquarters from location if available
            if data["location"]:
                data["headquarters"] = data["location"]
            
            # Extract Locations - improved strategy
            # Strategy 1: Look for location list items
            location_items = soup.find_all('div', class_=re.compile(r'location'))
            for item in location_items:
                text = item.get_text(strip=True)
                # Match pattern like "Salt Lake City, Utah, US"
                if re.search(r'[A-Za-z\s]+,\s*[A-Za-z\s]+', text):
                    if text not in data["locations"] and len(text) < 100:
                        data["locations"].append(text)
            
            # Strategy 2: Find all text matching location pattern
            if len(data["locations"]) == 0:
                all_text = soup.get_text()
                # Look for common location patterns
                location_patterns = [
                    r'([A-Z][a-z\s]+,\s*[A-Z][a-z\s]+,\s*US)',
                    r'([A-Z][a-z\s]+,\s*[A-Z]{2},\s*US)',
                    r'([A-Z][a-z\s]+,\s*[A-Z][a-z\s]+)'
                ]
                for pattern in location_patterns:
                    matches = re.findall(pattern, all_text)
                    for match in matches:
                        if match not in data["locations"] and 'Primary' not in match:
                            data["locations"].append(match)
                            if len(data["locations"]) >= 5:  # Limit to 5 locations
                                break
                    if data["locations"]:
                        break
            
            # Extract Employees - Use h3/h4 structure
            # Find all employee cards - they contain both name (h3) and title (h4)
            employee_headings = soup.find_all('h3', class_=re.compile(r'base-main-card__title'))
            
            seen_names = set()
            for h3 in employee_headings:
                if len(data["employees"]) >= 10:
                    break
                
                # Get name from h3
                name = h3.get_text(strip=True)
                
                # Skip if empty or duplicate
                if not name or name in seen_names:
                    continue
                    
                # Skip if it looks like it's not a name (too short, or common non-name words)
                if len(name) < 3 or any(keyword in name.lower() for keyword in ['view', 'all', 'discover', 'see']):
                    continue
               
                seen_names.add(name)
                
                # Find the corresponding h4 (title) which is a sibling
                h4 = h3.find_next_sibling('h4')
                title = "Unknown"
                if h4:
                    title_text = h4.get_text(strip=True)
                    # Clean up title - remove "at Company" part
                    if ' at ' in title_text:
                        title = title_text.split(' at ')[0].strip()
                    else:
                        title = title_text
                
                # Find the profile URL from parent anchor
                parent_link = h3.find_parent('a', href=re.compile(r'/in/'))
                profile_url = None
                if parent_link:
                    href = parent_link.get('href', '')
                    if href.startswith('http'):
                        profile_url = href.split('?')[0]
                    else:
                        profile_url = "https://www.linkedin.com" + href.split('?')[0]
                
                # Add employee data
                if profile_url:  # Only add if we have a profile URL
                    employee_data = {
                        "name": name,
                        "title": title,
                        "profile_url": profile_url
                    }
                    data["employees"].append(employee_data)
            
        except Exception as e:
            logger.error(f"Error scraping LinkedIn page {url}: {e}")
        finally:
            if driver:
                driver.quit()
        
        return data
