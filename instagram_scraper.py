"""Module for scraping Instagram profile bio links."""

import instaloader
import logging
import re
import time
from typing import Dict, Optional, List
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from link_tree_resolver import LinkTreeResolver
from website_enricher import WebsiteEnricher
from facebook_scraper import FacebookScraper

logger = logging.getLogger(__name__)


class InstagramScraper:
    """Scrapes Instagram profiles to extract bio links."""
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Instagram scraper.
        
        Args:
            username: Instagram username for login (optional)
            password: Instagram password for login (optional)
        """
        self.loader = instaloader.Instaloader()
        self.username = username
        self.password = password
        self.logged_in = False
        
    def _selenium_login(self, driver, username, password):
        """
        Log in to Instagram using Selenium.
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            logger.info("Logging in to Instagram via Selenium...")
            driver.get("https://www.instagram.com/accounts/login/")
            time.sleep(5)

            # Accept cookies if present (optional, but good practice)
            try:
                cookie_btn = driver.find_element(By.XPATH, "//button[text()='Allow all cookies']")
                cookie_btn.click()
                time.sleep(2)
            except:
                pass

            # Enter username
            user_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            user_input.send_keys(username)
            time.sleep(1)

            # Enter password
            pass_input = driver.find_element(By.NAME, "password")
            pass_input.send_keys(password)
            time.sleep(1)
            pass_input.send_keys(Keys.RETURN)

            logger.info("Waiting for login to complete...")
            time.sleep(12) # Increased wait time for login

            # Check for login errors
            try:
                error_element = driver.find_element(By.XPATH, "//*[contains(text(), 'Sorry') or contains(text(), 'incorrect') or contains(text(), 'try again')]")
                if error_element:
                    logger.error(f"Login error detected: {error_element.text}")
                    return False
            except:
                pass  # No error found, continue

            # Verify we're logged in by checking if we're redirected away from login page
            current_url = driver.current_url
            logger.info(f"Current URL after login: {current_url}")
            
            if "/accounts/login" in current_url:
                logger.error("Still on login page after login attempt - login may have failed")
                # Take a screenshot for debugging
                try:
                    driver.save_screenshot("/tmp/instagram_login_failed.png")
                    logger.info("Login failure screenshot saved to /tmp/instagram_login_failed.png")
                except:
                    pass
                return False

            # Handle "Save Info" popup
            try:
                save_info_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[text()='Not now']"))
                )
                save_info_btn.click()
                time.sleep(2)
                logger.info("Dismissed 'Save Info' popup")
            except:
                logger.info("No 'Save Info' popup found")
            
            # Handle "Turn on Notifications" popup
            try:
                notif_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()='Not Now']"))
                )
                notif_btn.click()
                time.sleep(2)
                logger.info("Dismissed 'Notifications' popup")
            except:
                logger.info("No 'Notifications' popup found")

            logger.info("Selenium login completed successfully.")
            return True
        except Exception as e:
            logger.error(f"Selenium login failed: {e}")
            return False

    def _scrape_with_selenium(self, username: str) -> Dict:
        """
        Fallback scraping using Selenium when API fails.
        """
        logger.info(f"Falling back to Selenium for {username}...")
        driver = None
        info = {
            'username': username,
            'full_name': None,
            'biography': None,
            'external_url': None,
            'followers': 0,
            'following': 0,
            'posts': 0,
            'is_business_account': False,
            'profile_pic_url': None,
            'is_private': False,
            'verified': False
        }
        
        try:
            from driver_utils import get_driver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            driver = get_driver()
            
            # Login if credentials provided
            if self.username and self.password:
                login_success = self._selenium_login(driver, self.username, self.password)
                if not login_success:
                    logger.error("Login failed, cannot proceed with scraping")
                    driver.quit()
                    return None

            url = f"https://www.instagram.com/{username}/"
            driver.get(url)
            time.sleep(8) # Increased initial wait time
            
            # Check if page exists
            if "Page Not Found" in driver.title:
                logger.warning(f"Profile {username} not found via Selenium.")
                return None

            # Enhanced wait strategy: Scroll to trigger lazy loading
            logger.info("Scrolling page to trigger content loading...")
            for i in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
            
            logger.info("Waiting for dynamic content to stabilize...")
            time.sleep(5)

            # Take a screenshot for debugging
            try:
                screenshot_path = f"/tmp/instagram_{username}_debug.png"
                driver.save_screenshot(screenshot_path)
                logger.info(f"Screenshot saved to {screenshot_path}")
            except Exception as e:
                logger.warning(f"Could not save screenshot: {e}")

            # Extract data using meta tags (more reliable than dynamic classes)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Meta Description often has "X Followers, Y Following, Z Posts"
            meta_desc = soup.find('meta', property='og:description')
            if meta_desc:
                desc_content = meta_desc.get('content', '')
                # Parse "100 Followers, 200 Following, 50 Posts"
                parts = desc_content.split(' - ')[0].split(', ')
                for part in parts:
                    if 'Followers' in part:
                        info['followers'] = int(part.replace('Followers', '').replace('k', '000').replace('m', '000000').replace('.', '').replace(',', '').strip())
                    elif 'Following' in part:
                        info['following'] = int(part.replace('Following', '').replace(',', '').strip())
                    elif 'Posts' in part:
                        info['posts'] = int(part.replace('Posts', '').replace(',', '').strip())

            # Full Name
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title_content = og_title.get('content', '')
                # "Name (@username) • Instagram photos..."
                if '(' in title_content:
                    info['full_name'] = title_content.split('(')[0].strip()
            
            # Biography - try to extract from page
            try:
                # Look for bio in various possible locations
                bio_candidates = soup.find_all('span', string=True)
                for candidate in bio_candidates:
                    text = candidate.get_text().strip()
                    # Bio is usually longer than a few words and not a navigation item
                    if len(text) > 20 and not any(nav in text.lower() for nav in ['followers', 'following', 'posts', 'meta', 'about', 'privacy']):
                        info['biography'] = text
                        logger.info(f"Found potential bio: {text[:50]}...")
                        break
            except Exception as e:
                logger.warning(f"Could not extract bio: {e}")
            
            # External URL (Bio Link) - Enhanced detection
            bio_links = soup.find_all('a', href=True)
            logger.info(f"Found {len(bio_links)} total links on page.")
            
            # Filter out common Instagram navigation/footer links
            excluded_patterns = [
                '/accounts/', '/explore/', '/legal/', '/web/',
                'about.instagram.com', 'about.meta.com', 'help.instagram.com',
                'developers.facebook.com', 'play.google.com', 'ms-windows-store',
                'threads.com', 'meta.ai'
            ]
            
            potential_bio_links = []
            for link in bio_links:
                href = link['href']
                text = link.get_text().strip()
                
                # Skip excluded patterns
                if any(pattern in href for pattern in excluded_patterns):
                    continue
                    
                # Look for external links or known bio link services
                if any(service in href for service in ['linktr.ee', 'l.instagram.com', 'bio.site', 'campsite.bio', 'beacons.ai', 'linkin.bio']):
                    potential_bio_links.append((href, text))
                    logger.info(f"Potential bio link found: {href} (Text: '{text}')")
            
            # Process potential bio links
            for href, text in potential_bio_links:
                if 'l.instagram.com' in href:
                    parsed = urlparse(href)
                    query = parse_qs(parsed.query)
                    if 'u' in query:
                        info['external_url'] = query['u'][0]
                        logger.info(f"Extracted bio link from redirect: {info['external_url']}")
                        break
                else:
                    info['external_url'] = href
                    logger.info(f"Extracted direct bio link: {info['external_url']}")
                    break
            
            if not info['external_url']:
                logger.warning(f"No bio link found for {username}. Profile may not have one set.")

            
            return info

        except Exception as e:
            logger.error(f"Selenium fallback failed for {username}: {e}")
            return None
        finally:
            if driver:
                driver.quit()

    def login(self) -> bool:
        """
        Login to Instagram if credentials are provided.
        
        Returns:
            True if login successful or not needed, False otherwise
        """
        if not self.username or not self.password:
            logger.info("No credentials provided, using public access")
            return True
            
        try:
            self.loader.login(self.username, self.password)
            self.logged_in = True
            logger.info("Successfully logged in to Instagram")
            return True
        except Exception as e:
            logger.error(f"Failed to login to Instagram: {e}")
            return False
    
    def _google_search_linkedin(self, query: str) -> Optional[str]:
        """
        Search Google for a LinkedIn profile using Custom Search JSON API.
        """
        try:
            import requests
            import config
            
            if not hasattr(config, 'GOOGLE_API_KEY') or not hasattr(config, 'GOOGLE_SEARCH_CX'):
                logger.error("Google API credentials not found in config.py")
                return None

            logger.info(f"Searching Google API for: {query}")
            
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': config.GOOGLE_API_KEY,
                'cx': config.GOOGLE_SEARCH_CX,
                'q': query,
                'num': 3  # We only need top results
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'items' not in data:
                logger.info("No results found in Google API response")
                return None
                
            for item in data['items']:
                link = item.get('link')
                if link and "linkedin.com/company" in link:
                    logger.info(f"Found matching LinkedIn link via API: {link}")
                    return link
            
            logger.info("No LinkedIn company links found in API results")
            return None

        except Exception as e:
            logger.error(f"Google API search error: {e}")
            return None
    
    def get_profile_info(self, instagram_handle: str) -> Optional[Dict]:
        """
        Scrapes basic profile info.
        """
        info = None
        try:
            # Remove @ if present
            handle = instagram_handle.lstrip('@')
            
            # Try Instaloader first
            try:
                profile = instaloader.Profile.from_username(self.loader.context, handle)
                info = {
                    'username': profile.username,
                    'full_name': profile.full_name,
                    'biography': profile.biography,
                    'external_url': profile.external_url,
                    'followers': profile.followers,
                    'following': profile.followees,
                    'posts': profile.mediacount,
                    'is_business_account': profile.is_business_account,
                    'profile_pic_url': profile.profile_pic_url,
                    'is_private': profile.is_private,
                    'verified': profile.is_verified
                }
                logger.info(f"Successfully scraped {handle} with Instaloader")
                
            except (instaloader.ConnectionException, instaloader.QueryReturnedNotFoundException, instaloader.LoginRequiredException) as e:
                logger.warning(f"Instaloader failed for {handle} ({e}). Attempting Selenium fallback...")
                info = self._scrape_with_selenium(handle)
                if not info:
                    logger.error(f"All scraping methods failed for {handle}")
                    return None

            if not info:
                return None

            # Initialize resolver and enricher
            resolver = LinkTreeResolver()
            enricher = WebsiteEnricher()
            
            external_url = info.get('external_url')
            resolved_links = {'social_links': [], 'website_links': []}
            enriched_data = {}
            
            if external_url:
                if resolver.is_link_tree(external_url):
                    logger.info(f"Detected link tree: {external_url}, resolving...")
                    resolved_links = resolver.resolve_url(external_url)
                    logger.info(f"Resolved {len(resolved_links['website_links'])} website links")
                else:
                    # If not a link tree, treat the external URL as a website link
                    resolved_links['website_links'].append(external_url)
            
            # Enrich from website links
            if resolved_links['website_links']:
                # For now, just enrich the first website found to save time
                target_site = resolved_links['website_links'][0]
                logger.info(f"Enriching data from website: {target_site}")
                enriched_data = enricher.enrich_url(target_site)
                
                # Merge found social links
                for sl in enriched_data.get('social_links', []):
                    if sl not in resolved_links['social_links']:
                        resolved_links['social_links'].append(sl)
            
            # Extract Instagram Address (only if we have profile object from instaloader)
            instagram_address = None
            # (Skipping complex address extraction for now to keep it simple and robust)

            # De-duplicate addresses
            unique_website_addresses = []
            if enriched_data.get('addresses'):
                for web_addr in enriched_data['addresses']:
                    # Simplified check since we might not have instagram_address
                    unique_website_addresses.append(web_addr)
            
            # Update enriched data with filtered addresses
            enriched_data['addresses'] = unique_website_addresses

            # Scrape Facebook if link found
            fb_data = {}
            for link in resolved_links['social_links']:
                if 'facebook.com' in link:
                    try:
                        logger.info(f"Found Facebook link: {link}, scraping...")
                        fb_scraper = FacebookScraper()
                        fb_data = fb_scraper.scrape_page(link)
                        
                        # Merge FB data into enriched_data with labels
                        if fb_data.get('emails'):
                            for email in fb_data['emails']:
                                if email not in enriched_data.get('emails', []):
                                    enriched_data.setdefault('emails', []).append(email)
                        
                        if fb_data.get('phones'):
                            for phone in fb_data['phones']:
                                # Check if number already exists
                                existing_nums = [p['number'] if isinstance(p, dict) else p for p in enriched_data.get('phones', [])]
                                if phone['number'] not in existing_nums:
                                    enriched_data.setdefault('phones', []).append(phone)

                    except Exception as e:
                        logger.warning(f"Error scraping Facebook: {e}")
                    break # Only scrape one FB page
            
            # Scrape LinkedIn if link found
            linkedin_data = None
            linkedin_url = None
            
            # Check resolved links first
            for link in resolved_links['social_links']:
                if 'linkedin.com/company' in link:
                    linkedin_url = link
                    break
            
            # Fallback: Google Search for LinkedIn if not found
            if not linkedin_url and info.get('full_name'):
                logger.info("No LinkedIn link found. Attempting Google Search fallback...")
                try:
                    # Construct query
                    # Try to extract City, State from address for a better search
                    location_part = ""
                    if enriched_data.get('addresses'):
                        addr = list(enriched_data['addresses'])[0]
                        # Simple heuristic: take the last 2 parts of the address (usually City, State Zip)
                        parts = addr.split(',')
                        if len(parts) >= 2:
                            location_part = f"{parts[-2]} {parts[-1]}"
                        else:
                            location_part = addr
                    
                    query = f"site:linkedin.com/company {info['full_name']} {location_part}".strip()
                    
                    logger.info(f"Searching Google for: {query}")
                    linkedin_url = self._google_search_linkedin(query)
                    
                    # If specific query fails, try broader query
                    if not linkedin_url:
                        query = f"site:linkedin.com/company {info['full_name']}".strip()
                        logger.info(f"Retrying with broader query: {query}")
                        linkedin_url = self._google_search_linkedin(query)

                    if linkedin_url:
                        logger.info(f"Found LinkedIn URL via Google: {linkedin_url}")
                except Exception as e:
                    logger.warning(f"Google search fallback failed: {e}")

            if linkedin_url:
                try:
                    logger.info(f"Scraping LinkedIn: {linkedin_url}")
                    from linkedin_scraper import LinkedInScraper
                    li_scraper = LinkedInScraper()
                    linkedin_data = li_scraper.scrape_company_page(linkedin_url)
                except Exception as e:
                    logger.warning(f"Error scraping LinkedIn: {e}")

            # Construct final result
            result = {
                'username': info['username'],
                'full_name': info['full_name'],
                'bio': info['biography'],
                'external_url': external_url,
                'resolved_website_links': resolved_links['website_links'],
                'resolved_social_links': resolved_links['social_links'],
                'enriched_data': enriched_data,
                'facebook_data': fb_data,
                'linkedin_data': linkedin_data,
                'instagram_address': instagram_address,
                'followers': info['followers'],
                'following': info['following'],
                'is_business': info['is_business_account'],
                'is_verified': info['verified'],
            }
            
            logger.info(f"Successfully scraped profile: {handle}")
            return result

        except Exception as e:
            logger.error(f"Unexpected error scraping {instagram_handle}: {e}")
            return None

    def _are_addresses_similar(self, addr1: str, addr2: str) -> bool:
        """Check if two addresses are similar enough to be considered duplicates."""
        def normalize(s):
            return re.sub(r'[^\w\s]', '', s.lower())
        
        n1 = normalize(addr1)
        n2 = normalize(addr2)
        
        # Simple containment check
        return n1 in n2 or n2 in n1
    
    def get_bio_link(self, instagram_handle: str) -> Optional[str]:
        """
        Get the bio link from an Instagram profile.
        
        Args:
            instagram_handle: Instagram username (without @)
            
        Returns:
            Bio link URL or None if not found
        """
        profile_info = self.get_profile_info(instagram_handle)
        if profile_info:
            return profile_info.get('external_url')
        return None
