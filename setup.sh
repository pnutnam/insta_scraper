#!/bin/bash

# Exit on error
set -e

echo "🚀 Setting up Instagram Scraper environment..."

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install it first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists."
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "⬇️ Installing dependencies..."
pip install -r requirements.txt

echo "
✅ Setup complete!

To run the application:
1. Activate the environment: source venv/bin/activate
2. Run the app: python app.py

Or simply run: ./run.sh
"
