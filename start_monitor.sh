#!/bin/bash

# Quick Start Script for Unified Ticket Monitor

echo "=========================================="
echo "Unified Ticket Monitor - Quick Start"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << 'EOF'
# Pushbullet Configuration
PUSHBULLET_API_KEY=your_pushbullet_api_key_here

# Travel Dates (Format: YYYY-MM-DD)
TRAVEL_DATE=2026-04-15
RETURN_DATE=2026-04-20

# Search Configuration
SEARCH_ONWORD=True
SEARCH_RETURN=True

# Check interval in minutes
CHECK_INTERVAL_MINUTES=3
EOF
    echo "✅ Created .env template"
    echo "📝 Please edit .env file with your actual values"
    echo ""
    echo "To edit: nano .env"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -q -r requirements.txt
echo "✅ Dependencies installed"

echo ""
echo "=========================================="
echo "Starting Unified Ticket Monitor..."
echo "=========================================="
echo ""
echo "Monitoring both BDTickets.com and BusBD.com"
echo "Press Ctrl+C to stop"
echo ""

# Run the unified monitor
python main_unified.py

