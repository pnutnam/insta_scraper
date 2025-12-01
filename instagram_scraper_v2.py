"""Module for scraping Instagram profile bio links (V2 - Optimized)."""

import instaloader
import logging
import re
import time
import concurrent.futures
from typing import Dict, Optional, List
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from link_tree_resolver import LinkTreeResolver
from website_enricher_v2 import WebsiteEnricherV2
from facebook_scraper import FacebookScraper

logger = logging.getLogger(__name__)

class InstagramScraperV2:
    """Scrapes Instagram profiles to extract bio links (Optimized)."""
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.loader = instaloader.Instaloader()
        self.username = username
        self.password = password
        self.logged_in = False
        
    def login(self) -> bool:
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
                'num': 3
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
        info = None
        try:
            handle = instagram_handle.lstrip('@')
            
            # 1. Scrape Instagram (Instaloader)
            # This is synchronous but usually fast enough.
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
                
                # Extract email from bio if present
                email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
                bio_emails = email_regex.findall(profile.biography)
                if bio_emails:
                    info['bio_email'] = bio_emails[0]
                    logger.info(f"Extracted email from bio: {info['bio_email']}")
                
                logger.info(f"Successfully scraped {handle} with Instaloader")
            except Exception as e:
                logger.error(f"Instaloader failed for {handle}: {e}")
                return None # Fail fast if Instagram fails, or implement selenium fallback if critical

            if not info: return None

            # 2. Resolve Bio Link
            resolver = LinkTreeResolver()
            external_url = info.get('external_url')
            resolved_links = {'social_links': [], 'website_links': []}
            
            if external_url:
                if resolver.is_link_tree(external_url):
                    logger.info(f"Detected link tree: {external_url}, resolving...")
                    resolved_links = resolver.resolve_url(external_url)
                    logger.info(f"Resolved {len(resolved_links['website_links'])} website links")
                else:
                    resolved_links['website_links'].append(external_url)
            
            # 3. PARALLEL Website Enrichment
            enricher = WebsiteEnricherV2()
            enriched_data = {'phones': [], 'emails': [], 'addresses': [], 'social_links': []}
            
            if resolved_links['website_links']:
                logger.info(f"Enriching {len(resolved_links['website_links'])} websites in parallel...")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    # Submit all enrichment tasks
                    future_to_url = {executor.submit(enricher.enrich_url, url): url for url in resolved_links['website_links']}
                    
                    for future in concurrent.futures.as_completed(future_to_url):
                        url = future_to_url[future]
                        try:
                            data = future.result()
                            if data:
                                # Merge results
                                enriched_data['phones'].extend(data.get('phones', []))
                                enriched_data['emails'].extend(data.get('emails', []))
                                enriched_data['addresses'].extend(data.get('addresses', []))
                                enriched_data['social_links'].extend(data.get('social_links', []))
                                
                                # Also merge found social links into resolved_links for later use
                                for sl in data.get('social_links', []):
                                    if sl not in resolved_links['social_links']:
                                        resolved_links['social_links'].append(sl)
                                        
                        except Exception as e:
                            logger.error(f"Error enriching {url}: {e}")

            # Deduplicate enriched data
            enriched_data['emails'] = list(set(enriched_data['emails']))
            
            # Add bio email to enriched emails if not present
            if info.get('bio_email'):
                if info['bio_email'] not in enriched_data['emails']:
                    # Insert at beginning to prioritize it
                    enriched_data['emails'].insert(0, info['bio_email'])
            enriched_data['addresses'] = list(set(enriched_data['addresses']))
            enriched_data['social_links'] = list(set(enriched_data['social_links']))
            # Phones are list of dicts, dedupe by number
            unique_phones = []
            seen_nums = set()
            for p in enriched_data['phones']:
                if p['number'] not in seen_nums:
                    unique_phones.append(p)
                    seen_nums.add(p['number'])
            enriched_data['phones'] = unique_phones

            # 4. Conditional Facebook Scraping
            fb_data = {}
            has_phone = bool(enriched_data.get('phones'))
            has_address = bool(enriched_data.get('addresses')) or bool(info.get('instagram_address')) # Note: instagram_address not extracted in this simplified version
            
            should_scrape_fb = not (has_phone and has_address)
            
            if should_scrape_fb:
                logger.info(f"Missing contact info. Attempting Facebook scrape...")
                for link in resolved_links['social_links']:
                    if 'facebook.com' in link:
                        try:
                            logger.info(f"Found Facebook link: {link}, scraping with login...")
                            # Use provided credentials
                            fb_scraper = FacebookScraper(email="pnutnam2@gmail.com", password="TKD-qmh7ahd1dpr@qeu")
                            fb_data = fb_scraper.scrape_page(link)
                            
                            # Merge FB data
                            if fb_data.get('emails'):
                                for email in fb_data['emails']:
                                    if email not in enriched_data['emails']:
                                        enriched_data['emails'].append(email)
                            if fb_data.get('phones'):
                                for phone in fb_data['phones']:
                                    if phone['number'] not in seen_nums:
                                        enriched_data['phones'].append(phone)
                                        seen_nums.add(phone['number'])
                        except Exception as e:
                            logger.warning(f"Error scraping Facebook: {e}")
                        break 
            else:
                logger.info("Skipping Facebook scrape - already have phone and address")

            # 5. LinkedIn Scraping
            linkedin_data = None
            linkedin_url = None
            
            # Check resolved links first
            for link in resolved_links['social_links']:
                if 'linkedin.com/company' in link:
                    linkedin_url = link
                    break
            
            # Fallback: Google Search
            if not linkedin_url and info.get('full_name'):
                logger.info("No LinkedIn link found. Attempting Google Search fallback...")
                try:
                    # Extract location from bio for better search precision
                    location_query = ""
                    if info.get('biography'):
                        # Look for "Based in X" or "📍 X"
                        # Simple heuristic: take the line with "Based in" or "📍"
                        for line in info['biography'].split('\n'):
                            if 'based in' in line.lower() or '📍' in line:
                                # Clean up the line to get just the location text
                                clean_loc = line.replace('Based in', '').replace('📍', '').strip()
                                if clean_loc:
                                    location_query = f'"{clean_loc}"'
                                    break
                    
                    query = f'site:linkedin.com/company "{info["full_name"]}" {location_query}'.strip()
                    linkedin_url = self._google_search_linkedin(query)
                except Exception as e:
                    logger.warning(f"Google search fallback failed: {e}")

            if linkedin_url:
                try:
                    logger.info(f"Scraping LinkedIn: {linkedin_url}")
                    from linkedin_scraper_v2 import LinkedInScraperV2
                    li_scraper = LinkedInScraperV2()
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
                'followers': info['followers'],
                'following': info['following'],
                'is_business': info['is_business_account'],
                'is_verified': info['verified'],
                'all_emails': enriched_data['emails'],
                'all_phones': enriched_data['phones'],
                'all_addresses': enriched_data['addresses']
            }
            
            logger.info(f"Successfully scraped profile: {handle}")
            return result

        except Exception as e:
            logger.error(f"Unexpected error scraping {instagram_handle}: {e}")
            return None
