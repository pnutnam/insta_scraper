import logging
from linkedin_scraper import LinkedInScraper

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    scraper = LinkedInScraper()
    url = "https://www.linkedin.com/company/umcinc/"
    
    logger.info(f"Testing LinkedIn scraper for: {url}")
    data = scraper.scrape_company_page(url)
    
    logger.info("\\n=== SCRAPE RESULTS ===")
    logger.info(f"Website: {data.get('website')}")
    logger.info(f"Industry: {data.get('industry')}")
    logger.info(f"Company Size: {data.get('company_size')}")
    logger.info(f"Headquarters: {data.get('headquarters')}")
    logger.info(f"Founded: {data.get('founded')}")
    logger.info(f"Type: {data.get('type')}")
    logger.info(f"Specialties: {data.get('specialties')}")
    logger.info(f"\\nLocations ({len(data.get('locations', []))}):")
    for loc in data.get('locations', []):
        logger.info(f"  - {loc}")
    logger.info(f"\\nEmployees ({len(data.get('employees', []))}):")
    for emp in data.get('employees', []):
        logger.info(f"  - {emp['name']} - {emp['title']}")
        logger.info(f"    URL: {emp['profile_url']}")
