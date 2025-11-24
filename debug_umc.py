import logging
import time
from website_enricher import WebsiteEnricher
from instagram_scraper import InstagramScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_enricher_class():
    logger.info("--- Testing WebsiteEnricher Class ---")
    enricher = WebsiteEnricher()
    
    # Test 1: Soft 404 (should now work or fallback)
    url = "https://umc.us/careers"
    logger.info(f"Enriching: {url}")
    data = enricher.enrich_url(url)
    
    logger.info("Enriched Data Results:")
    logger.info(f"Emails: {data.get('emails')}")
    logger.info(f"Social Links: {data.get('social_links')}")
    logger.info(f"Scraped Pages: {data.get('scraped_pages')}")
    
    if data.get('social_links') or data.get('emails'):
        logger.info("SUCCESS: Enrichment found data!")
    else:
        logger.error("FAILURE: Enrichment returned empty data.")

def test_google_search_method():
    logger.info("--- Testing InstagramScraper._google_search_linkedin (API) ---")
    scraper = InstagramScraper()
    
    query = "site:linkedin.com/company UMC, Inc."
    logger.info(f"Searching for: {query}")
    
    linkedin_url = scraper._google_search_linkedin(query)
    
    if linkedin_url:
        logger.info(f"SUCCESS: Found LinkedIn URL: {linkedin_url}")
    else:
        logger.warning("FAILURE: No LinkedIn URL found via API")

if __name__ == "__main__":
    test_enricher_class()
    test_google_search_method()
