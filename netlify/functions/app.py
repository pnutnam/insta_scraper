import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import app
import serverless_wsgi

def handler(event, context):
    """Netlify serverless function handler."""
    return serverless_wsgi.handle_request(app, event, context)
