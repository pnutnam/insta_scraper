"""Configuration settings for Instagram scraper."""

# Instagram settings
INSTAGRAM_USERNAME = None  # Optional: Set if you need to login
INSTAGRAM_PASSWORD = None  # Optional: Set if you need to login

# Scraping settings
MAX_LINKS_TO_CHECK = 20  # Maximum number of links to check from Linktree
REQUEST_TIMEOUT = 10  # Timeout for HTTP requests in seconds
MAX_RETRIES = 3  # Maximum number of retries for failed requests

# Link tree services to detect
LINK_TREE_SERVICES = [
    'linktr.ee',
    'linktree.com',
    'bio.link',
    'beacons.ai',
    'hoo.be',
    'solo.to',
    'allmylinks.com',
    'carrd.co',
    'taplink.cc',
    'linkpop.com',
    'shorby.com',
    'campsite.bio',
]

# Social media platforms to detect
SOCIAL_PLATFORMS = {
    'linkedin': ['linkedin.com/in/', 'linkedin.com/company/'],
    'facebook': ['facebook.com/', 'fb.com/', 'fb.me/'],
    'twitter': ['twitter.com/', 'x.com/'],
    'youtube': ['youtube.com/', 'youtu.be/'],
    'tiktok': ['tiktok.com/@'],
    'pinterest': ['pinterest.com/'],
    'instagram': ['instagram.com/'],
}

# Output settings
OUTPUT_CSV = 'customer_ledger.csv'
OUTPUT_JSON = 'customer_ledger.json'

# User agent for requests
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
