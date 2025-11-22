import json
import os

# Define the notebook structure
notebook = {
    "cells": [],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.8.5"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

def add_cell(cell_type, source):
    notebook["cells"].append({
        "cell_type": cell_type,
        "metadata": {},
        "outputs": [],
        "source": source if isinstance(source, list) else source.splitlines(keepends=True),
        "execution_count": None
    })

# Cell 1: Install dependencies
add_cell("code", "!pip install instaloader beautifulsoup4 requests pandas")

# Cell 2: Config
with open("config.py", "r") as f:
    config_content = f.read()
add_cell("code", config_content)

# Cell 3: LinkTreeResolver
with open("link_tree_resolver.py", "r") as f:
    resolver_content = f.read()
    # Remove import config as it's now in the same scope
    resolver_content = resolver_content.replace("import config", "")
    # Fix usage of config.VAR to VAR since they are in global scope now
    # Actually, keeping config.VAR might fail if config is not a module.
    # We should probably create a Config class or just replace config.VAR with VAR.
    # Let's replace config.VAR with VAR for simplicity in notebook
    import re
    resolver_content = re.sub(r'config\.([A-Z_]+)', r'\1', resolver_content)
add_cell("code", resolver_content)

# Cell 4: InstagramScraper
with open("instagram_scraper.py", "r") as f:
    scraper_content = f.read()
    # Remove imports that are already handled or local
    scraper_content = scraper_content.replace("from link_tree_resolver import LinkTreeResolver", "")
    # Replace config usage if any (scraper doesn't use config directly much, but let's check)
    # It seems scraper doesn't use config.py directly in the code I saw, but let's be safe.
    scraper_content = re.sub(r'config\.([A-Z_]+)', r'\1', scraper_content)
add_cell("code", scraper_content)

# Cell 5: Usage Example
usage_example = """
# Usage Example

# Initialize scraper
# Note: For public profiles, login might not be strictly necessary but recommended for stability.
# If you have credentials, set them in the config variables above or pass them here.
scraper = InstagramScraper()
scraper.login()

# Test with a handle
handle = "linktr.ee" # Example handle, or use a real one
print(f"Scraping profile: {handle}")
info = scraper.get_profile_info(handle)

if info:
    print("Found profile info:")
    print(f"Username: {info['username']}")
    print(f"Bio Link: {info['external_url']}")
    if info.get('resolved_website_links'):
        print("Resolved Website Links:", info['resolved_website_links'])
    if info.get('resolved_social_links'):
        print("Resolved Social Links:", info['resolved_social_links'])
else:
    print("Failed to scrape profile.")
"""
add_cell("code", usage_example)

# Write notebook
with open("instagram_scraper.ipynb", "w") as f:
    json.dump(notebook, f, indent=2)

print("Notebook created successfully.")
