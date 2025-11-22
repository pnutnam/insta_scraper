"""Module for resolving Linktree and similar bio link pages."""

import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from urllib.parse import urlparse
import config

logger = logging.getLogger(__name__)

class LinkTreeResolver:
    """Resolves 'link in bio' pages to find actual business websites."""

    def __init__(self):
        self.headers = {'User-Agent': config.USER_AGENT}

    def is_link_tree(self, url: str) -> bool:
        """
        Check if a URL is a known link tree service.
        
        Args:
            url: The URL to check
            
        Returns:
            True if it's a link tree service, False otherwise
        """
        if not url:
            return False
            
        try:
            domain = urlparse(url).netloc.lower()
            # Remove 'www.' if present
            if domain.startswith('www.'):
                domain = domain[4:]
                
            for service in config.LINK_TREE_SERVICES:
                if service in domain:
                    return True
            return False
        except Exception:
            return False

    def resolve_url(self, url: str) -> Dict[str, List[str]]:
        """
        Resolve a link tree URL to find contained links.
        
        Args:
            url: The link tree URL to resolve
            
        Returns:
            Dictionary with 'social_links' and 'website_links'
        """
        results = {
            'social_links': [],
            'website_links': []
        }

        if not url:
            return results

        try:
            response = requests.get(url, headers=self.headers, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links
            for a in soup.find_all('a', href=True):
                href = a['href']
                if not href or href.startswith('#') or href.startswith('mailto:'):
                    continue
                    
                # Classify link
                if self._is_social_link(href):
                    if href not in results['social_links']:
                        results['social_links'].append(href)
                else:
                    # Avoid adding the link tree itself or empty links
                    if href != url and href not in results['website_links']:
                        results['website_links'].append(href)
                        
            # Limit number of links to check/return
            results['website_links'] = results['website_links'][:config.MAX_LINKS_TO_CHECK]
            
            return results
            
        except Exception as e:
            logger.error(f"Error resolving link tree {url}: {e}")
            return results

    def _is_social_link(self, url: str) -> bool:
        """Check if a URL is a social media link."""
        try:
            domain = urlparse(url).netloc.lower()
            for platform, domains in config.SOCIAL_PLATFORMS.items():
                for d in domains:
                    # Simple check if the domain part of the config exists in the url
                    # This is a basic check and can be improved
                    clean_d = d.split('/')[0] # get just domain from "linkedin.com/in/"
                    if clean_d in domain:
                        return True
            return False
        except Exception:
            return False
