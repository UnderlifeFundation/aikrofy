#!/bin/bash

# PymAI Setup Script
# Run this script to set up the development environment

echo "🥊 Setting up PymAI Multi-Agent System..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip3 install -r requirements.txt

# Copy environment file
if [ ! -f .env ]; then
    echo "📄 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your credentials"
fi

# Create uploads directory
mkdir -p uploads

# Initialize git if not already
if [ ! -d .git ]; then
    echo "🔄 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit: PymAI Multi-Agent System"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit the .env file with your API keys and database credentials"
echo "2. Set up your MySQL database and update DATABASE_URL in .env"
echo "3. Run the following commands to start:"
echo ""
echo "   source venv/bin/activate"
echo "   flask db init"
echo "   flask db migrate -m 'Initial migration'"
echo "   flask db upgrade"
echo "   flask run"
echo ""
echo "The application will be available at http://localhost:5000"
