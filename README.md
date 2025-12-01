# Instagram Business Profile Scraper (V2)

A robust, multi-source scraping tool designed to extract comprehensive business intelligence starting from a single Instagram handle.

![Instagram Bio](assets/instagram_bio.png)

## 🚀 Features

- **Multi-Source Enrichment**: Automatically navigates from **Instagram** -> **Linktree** -> **Company Website** -> **Facebook** -> **LinkedIn** to build a complete profile.
- **Parallel Crawling**: V2 engine uses threaded enrichment to crawl multiple website links simultaneously, significantly reducing execution time.
- **Smart Data Extraction**:
  - **Role Prioritization**: Intelligently selects key personnel (Owner, Founder, CEO) from LinkedIn employee lists.
  - **Strict Email Matching**: Validates emails against the company domain to ensure accuracy, falling back to bio emails only when necessary.
  - **Location-Aware Search**: Uses Instagram bio location to disambiguate common company names on LinkedIn.
- **Resilience & Fallbacks**:
  - Handles rate limits and login requirements.
  - Conditional Facebook scraping (only attempts login if contact info is missing).
  - Robust error handling and logging.

## 🛠️ Installation

1. **Clone the repository**:

    ```bash
    git clone <repository-url>
    cd instagram_scraper
    ```

2. **Set up a virtual environment**:

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3. **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Install Playwright browsers** (if required by specific modules, though Selenium is primary):

    ```bash
    playwright install
    ```

## 📖 Usage

Run the V2 scraper with a target Instagram handle:

```bash
python main_scraper_v2.py <instagram_handle>
```

**Example:**

```bash
python main_scraper_v2.py kite_media
```

### Output

The tool generates a flat JSON file (e.g., `kite_media_profile_v2.json`) containing the consolidated business profile:

```json
{
  "first_name": "Garrett",
  "last_name": "Kite",
  "email": "info@kitemedia.com",
  "role": "Owner @ Kite Media",
  "company": "Kite Media",
  "website": "https://linktr.ee/kitemedia",
  "metadata": {
    "username": "kite_media",
    "full_name": "Kite Media",
    "bio": "...",
    "enriched_data": { ... },
    "linkedin_data": { ... }
  }
}
```

## 🏗️ Architecture

The scraper follows a logical enrichment flow to gather and verify data:

```mermaid
graph TD
    A[Start: Instagram Handle] --> B[Scrape Instagram Bio];
    B --> C{Has Linktree?};
    C -- Yes --> D[Resolve Linktree URLs];
    C -- No --> E[Use Bio URL];
    D --> F[Parallel Web Crawl];
    E --> F;
    F --> G[Extract Contact Info & Social Links];
    G --> H{Missing Phone/Address?};
    H -- Yes --> I[Conditional Facebook Scrape];
    H -- No --> J[Skip Facebook];
    I --> K[LinkedIn Search & Scrape];
    J --> K;
    K --> L[Smart Data Consolidation];
    L --> M[Final JSON Output];
```

## 📸 Visuals

### Linktree Resolution

The scraper automatically resolves Linktree URLs to find the actual business website.
![Linktree](assets/linktree.png)

### LinkedIn Enrichment

It finds the correct LinkedIn company page to extract employee details and company size.
![LinkedIn Profile](assets/linkedin_profile.png)

## 🗺️ Roadmap

- [ ] **API Integration**: Expose the scraper as a REST API (Flask/FastAPI).
- [ ] **Proxy Rotation**: Implement smart proxy rotation to avoid rate limiting on high-volume scrapes.
- [ ] **Headless Improvements**: Further optimize headless browser performance for faster execution.
- [ ] **Database Sink**: Add option to save results directly to a PostgreSQL/MongoDB database.

## 📄 License

[MIT License](LICENSE)
