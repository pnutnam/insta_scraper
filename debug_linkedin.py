import logging
from linkedin_scraper import LinkedInScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    scraper = LinkedInScraper()
    url = "https://www.linkedin.com/company/umcinc/"
    
    logger.info(f"Testing LinkedIn scraper for: {url}")
    data = scraper.scrape_company_page(url)
    
    logger.info("\\n=== SCRAPE RESULTS ===")
    for key, value in data.items():
        logger.info(f"{key}: {value}")
