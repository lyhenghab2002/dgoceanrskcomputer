#!/usr/bin/env python3
"""
Test script to run the Flask app locally with proper configuration
"""

import os
from app import app

# Set local database configuration
os.environ['MYSQL_HOST'] = 'localhost'
os.environ['MYSQL_USER'] = 'root'
os.environ['MYSQL_PASSWORD'] = '12345'  # Your local MySQL password
os.environ['MYSQL_DB'] = 'computershop5'
os.environ['MYSQL_PORT'] = '3306'

if __name__ == '__main__':
    print("Starting Flask app locally...")
    print("Database: localhost:3306/computershop5")
    print("Access the app at: http://localhost:5000")
    
    # Use the create_app function to get the properly configured app
    from app import create_app
    app = create_app()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
