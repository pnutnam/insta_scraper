#!/bin/bash

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "⚠️ Virtual environment not found. Running setup first..."
    ./setup.sh
fi

# Activate and run
source venv/bin/activate
echo "🚀 Starting Instagram Scraper Web UI..."
python app.py
