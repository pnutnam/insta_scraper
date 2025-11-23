from linkedin_scraper import LinkedInScraper
import json

def test_linkedin():
    scraper = LinkedInScraper()
    # Use Microsoft as a test case since we know it works publicly
    url = "https://www.linkedin.com/company/microsoft"
    print(f"Testing LinkedIn Scraper with {url}...")
    
    data = scraper.scrape_company_page(url)
    
    print("\nScraped Data:")
    print(json.dumps(data, indent=2))
    
    if data.get('employee_count'):
        print("\n✅ SUCCESS: Found employee count!")
    else:
        print("\n❌ FAILURE: Could not find employee count.")

if __name__ == "__main__":
    test_linkedin()
