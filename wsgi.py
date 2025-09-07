#!/usr/bin/env python3
"""
WSGI entry point for both Render and Railway deployment
"""

import os
from app import create_app

# Create the Flask application instance
application = create_app()

if __name__ == "__main__":
    # Get port from environment variable (both Render and Railway use PORT)
    port = int(os.environ.get('PORT', 5000))
    
    # Bind to all interfaces for cloud deployment
    application.run(host='0.0.0.0', port=port)