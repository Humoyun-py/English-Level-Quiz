#!/bin/bash

# English Level Quiz - Deployment Script

echo "🚀 Starting deployment..."

# Update pip
echo "📦 Updating pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install aiogram flask flask-cors gunicorn

# Try to install reportlab (optional for PDF certificates)
echo "📄 Installing reportlab (optional)..."
pip install reportlab || echo "⚠️ reportlab installation failed, PDF certificates will be disabled"

# Initialize database
echo "💾 Initializing database..."
python -c "from app import init_web_users_table; init_web_users_table()" || echo "Database will be created on first run"

echo "✅ Deployment complete!"
echo ""
echo "To run the web app:"
echo "  python app.py"
echo ""
echo "To run with gunicorn (production):"
echo "  gunicorn -w 4 -b 0.0.0.0:5000 app:app"
echo ""
echo "To run the Telegram bot:"
echo "  python bot.py"
