from flask import Flask, render_template, request, jsonify
import logging
from instagram_scraper import InstagramScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """
    API endpoint to scrape an Instagram profile.
    Expects JSON: { "handle": "username" }
    """
    data = request.get_json()
    handle = data.get('handle')
    
    if not handle:
        return jsonify({'error': 'Instagram handle is required'}), 400
        
    try:
        # Initialize scraper (using public access for now)
        # In a real app, you might want to manage sessions or use a pool of workers
        scraper = InstagramScraper()
        
        # Login if credentials are in config (optional)
        # scraper.login() 
        
        logger.info(f"Received scrape request for: {handle}")
        profile_info = scraper.get_profile_info(handle)
        
        if profile_info:
            return jsonify({'success': True, 'data': profile_info})
        else:
            return jsonify({'success': False, 'error': 'Profile not found or could not be scraped'}), 404
            
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
