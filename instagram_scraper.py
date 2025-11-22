"""Module for scraping Instagram profile bio links."""

import instaloader
import logging
import re
from typing import Optional, Dict

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
    
    def get_profile_info(self, instagram_handle: str) -> Optional[Dict[str, str]]:
        """
        Get profile information from Instagram.
        
        Args:
            instagram_handle: Instagram username (without @)
            
        Returns:
            Dictionary with profile info including bio link, or None if failed
        """
        try:
            # Remove @ if present
            handle = instagram_handle.lstrip('@')
            
            # Load profile
            profile = instaloader.Profile.from_username(self.loader.context, handle)
            
            # Initialize resolver and enricher
            from link_tree_resolver import LinkTreeResolver
            from website_enricher import WebsiteEnricher
            resolver = LinkTreeResolver()
            enricher = WebsiteEnricher()
            
            external_url = profile.external_url
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
            
            # Extract Instagram Address
            instagram_address = None
            try:
                # Try to get business address if available (this might need login or specific fields)
                # Instaloader doesn't always expose this directly in the public API without login
                # We can try to parse it from the bio or look at the raw node data if available
                # For now, let's look for address-like patterns in the bio as a fallback
                # or check if we can access 'business_address_json' from the internal node
                if hasattr(profile, '_node') and profile._node.get('business_address_json'):
                     import json
                     addr_json = profile._node.get('business_address_json')
                     if addr_json:
                         # It's usually a JSON string
                         try:
                             addr_data = json.loads(addr_json)
                             parts = [addr_data.get('street_address'), addr_data.get('city_name'), 
                                      addr_data.get('zip_code'), addr_data.get('country_code')]
                             instagram_address = ", ".join([p for p in parts if p])
                         except:
                             pass
            except Exception as e:
                logger.warning(f"Failed to extract IG address: {e}")

            # De-duplicate addresses
            unique_website_addresses = []
            if enriched_data.get('addresses'):
                for web_addr in enriched_data['addresses']:
                    if not instagram_address or not self._are_addresses_similar(instagram_address, web_addr):
                        unique_website_addresses.append(web_addr)
            
            # Update enriched data with filtered addresses
            enriched_data['addresses'] = unique_website_addresses

            # Scrape Facebook if link found
            fb_data = {}
            for link in resolved_links['social_links']:
                if 'facebook.com' in link:
                    try:
                        logger.info(f"Found Facebook link: {link}, scraping...")
                        from facebook_scraper import FacebookScraper
                        fb_scraper = FacebookScraper()
                        fb_data = fb_scraper.scrape_page(link)
                        
                        # Merge FB data into enriched_data with labels
                        if fb_data.get('emails'):
                            for email in fb_data['emails']:
                                if email not in enriched_data.get('emails', []):
                                    enriched_data.setdefault('emails', []).append(email) # We'll need to handle source labeling in UI or here
                                    # Actually, let's keep fb_data separate in the info dict so UI can label it easily
                        
                        if fb_data.get('phones'):
                            for phone in fb_data['phones']:
                                # Check if number already exists
                                existing_nums = [p['number'] if isinstance(p, dict) else p for p in enriched_data.get('phones', [])]
                                if phone['number'] not in existing_nums:
                                    enriched_data.setdefault('phones', []).append(phone)

                    except Exception as e:
                        logger.warning(f"Error scraping Facebook: {e}")
                    break # Only scrape one FB page

            info = {
                'username': profile.username,
                'full_name': profile.full_name,
                'bio': profile.biography,
                'external_url': external_url,
                'resolved_website_links': resolved_links['website_links'],
                'resolved_social_links': resolved_links['social_links'],
                'enriched_data': enriched_data,
                'facebook_data': fb_data, # Pass separately for explicit labeling if needed
                'instagram_address': instagram_address,
                'followers': profile.followers,
                'following': profile.followees,
                'is_business': profile.is_business_account,
                'is_verified': profile.is_verified,
            }
            
            logger.info(f"Successfully scraped profile: {handle}")
            logger.info(f"External URL: {info['external_url']}")
            
            return info
            
        except instaloader.exceptions.ProfileNotExistsException:
            logger.error(f"Profile not found: {instagram_handle}")
            return None
        except instaloader.exceptions.ConnectionException as e:
            logger.error(f"Connection error while fetching profile {instagram_handle}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching profile {instagram_handle}: {e}")
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
