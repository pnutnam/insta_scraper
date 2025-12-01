"""Module for enriching profile data by scraping business websites (V2 - No Social Scraping)."""

import logging
import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Set, Optional
from urllib.parse import urljoin, urlparse
import phonenumbers
import config

logger = logging.getLogger(__name__)

class WebsiteEnricherV2:
    """Scrapes business websites to extract contact info and social links (Fast version)."""

    def __init__(self):
        self.headers = {'User-Agent': config.USER_AGENT}
        # Regex for email extraction
        self.email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        # Keywords to find secondary pages
        self.contact_keywords = ['contact', 'contact us', 'get in touch', 'contact us today']
        self.about_keywords = ['about', 'about us', 'our story']

    def enrich_url(self, url: str) -> Dict:
        """
        Scrape a website and its secondary pages for contact info.
        Does NOT scrape found social media links (Facebook/LinkedIn).
        
        Args:
            url: The website URL to scrape
            
        Returns:
            Dictionary with extracted data
        """
        results = {
            'phones': [], # List of dicts: {number, label, score}
            'emails': set(),
            'addresses': set(),
            'social_links': set(),
            'scraped_pages': []
        }
        
        if not url:
            return self._format_results(results)

        try:
            # 1. Scrape Homepage
            logger.info(f"Enriching website: {url}")
            soup = self._scrape_page(url)
            if not soup:
                return self._format_results(results)
                
            results['scraped_pages'].append(url)
            self._extract_data(soup, results, url)
            
            # Fallback: If no social links or emails found, and not root domain, try root domain
            if not results['social_links'] and not results['emails']:
                parsed = urlparse(url)
                root_url = f"{parsed.scheme}://{parsed.netloc}"
                if url.rstrip('/') != root_url.rstrip('/'):
                    logger.info(f"No results from {url}, attempting fallback to root: {root_url}")
                    root_soup = self._scrape_page(root_url)
                    if root_soup:
                        results['scraped_pages'].append(root_url)
                        self._extract_data(root_soup, results, root_url)
                        # Update soup to root soup for secondary page discovery
                        soup = root_soup
                        url = root_url
            
            # 2. Find and Scrape Secondary Pages (Contact/About)
            secondary_pages = self._find_secondary_pages(soup, url)
            for page_url in secondary_pages:
                if page_url not in results['scraped_pages']:
                    logger.info(f"Scraping secondary page: {page_url}")
                    sub_soup = self._scrape_page(page_url)
                    if sub_soup:
                        results['scraped_pages'].append(page_url)
                        self._extract_data(sub_soup, results, page_url)
            
            # REMOVED: Facebook and LinkedIn scraping logic
            # This allows the enricher to be fast and purely focused on the website.
            # Social scraping will be handled by the main orchestrator.

            # Sort phones by score descending
            results['phones'].sort(key=lambda x: x['score'], reverse=True)
            
            return self._format_results(results)
            
        except Exception as e:
            logger.error(f"Error enriching website {url}: {e}")
            return self._format_results(results)

    def _scrape_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page."""
        try:
            response = requests.get(url, headers=self.headers, timeout=config.REQUEST_TIMEOUT)
            
            # Handle "soft 404s"
            if response.status_code >= 400:
                if len(response.text) > 500:
                    logger.warning(f"Got status {response.status_code} for {url} but content length is {len(response.text)}. Proceeding as soft 404.")
                else:
                    logger.warning(f"Failed to fetch {url}: Status {response.status_code}")
                    return None
            
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    def _extract_data(self, soup: BeautifulSoup, results: Dict, base_url: str):
        """Extract all data from a soup object."""
        text = soup.get_text(" ", strip=True)
        
        # Extract Emails
        emails = self.email_regex.findall(text)
        for email in emails:
            if len(email) < 50 and not email.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                results['emails'].add(email.lower())
                
        # Extract Phones with Context
        seen_numbers = {p['number'] for p in results['phones']}
        
        for element in soup.find_all(['p', 'div', 'span', 'li', 'td', 'a']):
            if len(element.find_all(recursive=False)) > 3:
                continue
                
            elem_text = element.get_text(" ", strip=True)
            if not elem_text:
                continue
                
            try:
                for match in phonenumbers.PhoneNumberMatcher(elem_text, "US"):
                    formatted = phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                    
                    if formatted in seen_numbers:
                        continue
                        
                    score = 0
                    if 'contact' in base_url.lower(): score += 10
                    if element.find_parent(['header', 'footer']): score += 5
                    
                    label = self._get_phone_label(element, formatted)
                    if 'main' in label.lower() or 'office' in label.lower() or 'headquarters' in label.lower():
                        score += 5
                    
                    results['phones'].append({
                        'number': formatted,
                        'label': label,
                        'score': score
                    })
                    seen_numbers.add(formatted)
            except Exception:
                pass
            
        # Extract Addresses
        state_zip_regex = re.compile(r'\b[A-Z]{2}[,.]?\s+\d{5}(?:-\d{4})?\b')
        street_regex = re.compile(r'\d+\s+[A-Za-z0-9\s,.]+\s+(?:St|Ave|Rd|Dr|Blvd|Ln|Drive|Street|Avenue|Road|Suite|Ste|Way|Circle|Cir)\b', re.IGNORECASE)
        suite_regex = re.compile(r'(?:Suite|Ste|Unit|Apt)\s+#?\w+', re.IGNORECASE)
        label_regex = re.compile(r'^[A-Za-z\s]+:$')
        noise_regex = re.compile(r'(?:Contact|Call|Text|Book Now|Follow|Us|Location|Email|Phone|Hours|Open|Mon|Tue|Wed|Thu|Fri|Sat|Sun).*?[:\-]?', re.IGNORECASE)
        
        address_candidates = set()
        
        for elem in soup.find_all(['div', 'p', 'span', 'li', 'td', 'address']):
            if len(elem.find_all(recursive=False)) > 3:
                continue
            
            lines = elem.get_text("\n", strip=True).split('\n')
            current_address_buffer = []
            has_state_zip = False
            
            for line in lines:
                line = line.strip()
                if not line or len(line) > 150: 
                    if current_address_buffer and has_state_zip:
                        full_addr = " ".join(current_address_buffer)
                        full_addr = noise_regex.sub('', full_addr).strip()
                        if len(full_addr) > 10:
                            address_candidates.add(full_addr)
                    current_address_buffer = []
                    has_state_zip = False
                    continue
                
                is_component = False
                if label_regex.match(line): is_component = True
                elif street_regex.search(line) and any(c.isdigit() for c in line): is_component = True
                elif suite_regex.search(line): is_component = True
                elif state_zip_regex.search(line):
                    is_component = True
                    has_state_zip = True
                elif elem.name == 'address':
                    is_component = True
                    if state_zip_regex.search(line): has_state_zip = True

                if is_component:
                    current_address_buffer.append(line)
                else:
                    if current_address_buffer and has_state_zip:
                        full_addr = " ".join(current_address_buffer)
                        full_addr = noise_regex.sub('', full_addr).strip()
                        if len(full_addr) > 10:
                            address_candidates.add(full_addr)
                    current_address_buffer = []
                    has_state_zip = False
            
            if current_address_buffer and has_state_zip:
                full_addr = " ".join(current_address_buffer)
                full_addr = noise_regex.sub('', full_addr).strip()
                if len(full_addr) > 10:
                    address_candidates.add(full_addr)
            
        for addr in address_candidates:
            results['addresses'].add(addr)

        # Extract Social Links
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(base_url, href)
            if self._is_social_link(full_url):
                results['social_links'].add(full_url)

    def _get_phone_label(self, element, phone_number):
        """Try to find a label for the phone number from context."""
        text = element.get_text(" ", strip=True)
        clean_text = text.replace(phone_number, "").strip()
        clean_text = re.sub(r'[\(\)\-\.\s\d]{7,}', '', clean_text).strip()
        
        if clean_text and len(clean_text) < 50:
            return clean_text.strip(': -')
            
        prev = element.find_previous_sibling()
        if prev:
            prev_text = prev.get_text(" ", strip=True)
            if prev_text and len(prev_text) < 50:
                return prev_text.strip(': -')
                
        parent = element.parent
        if parent:
            prev_parent = parent.find_previous_sibling()
            if prev_parent:
                prev_parent_text = prev_parent.get_text(" ", strip=True)
                if prev_parent_text and len(prev_parent_text) < 50:
                    return prev_parent_text.strip(': -')
                    
        header = element.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if header:
            header_text = header.get_text(" ", strip=True)
            if len(header_text) < 50:
                return header_text.strip(': -')

        return "Phone"

    def _find_secondary_pages(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """Find Contact and About pages aggressively."""
        pages = set()
        for a in soup.find_all('a', href=True):
            text = a.get_text(" ", strip=True).lower()
            href = a['href'].lower()
            full_url = urljoin(base_url, a['href'])
            
            if urlparse(full_url).netloc != urlparse(base_url).netloc:
                continue
                
            if 'contact' in text or 'contact' in href:
                pages.add(full_url)
            elif 'about' in text or 'about' in href:
                pages.add(full_url)
                
        return pages

    def _is_social_link(self, url: str) -> bool:
        """Check if a URL is a social media link."""
        try:
            domain = urlparse(url).netloc.lower()
            for platform, domains in config.SOCIAL_PLATFORMS.items():
                for d in domains:
                    clean_d = d.split('/')[0]
                    if clean_d in domain:
                        return True
            return False
        except Exception:
            return False

    def _format_results(self, results: Dict) -> Dict:
        """Convert sets to lists for JSON serialization."""
        return {
            'phones': results['phones'],
            'emails': list(results['emails']),
            'addresses': list(results['addresses']),
            'social_links': list(results['social_links']),
            'scraped_pages': results['scraped_pages']
        }
