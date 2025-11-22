from app import app

def handler(event, context):
    """Netlify serverless function handler."""
    # Import the serverless WSGI handler
    try:
        from serverless_wsgi import handle_request
        return handle_request(app, event, context)
    except ImportError:
        return {
            'statusCode': 500,
            'body': 'serverless-wsgi not installed. Add it to requirements.txt'
        }
