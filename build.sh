#!/bin/bash
echo "🚀 Starting build process for BetAnalyzer..."

# Exit on error
set -e

# Install system dependencies for Render
if [ "$RENDER" = "true" ]; then
    echo "📦 Installing system dependencies (Tesseract OCR for betslip images)..."
    apt-get update -qq
    apt-get install -y -qq tesseract-ocr tesseract-ocr-eng wget curl
    echo "✅ Tesseract OCR installed successfully"
fi

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip --quiet

# Install Python dependencies
echo "📦 Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt --quiet

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p static/css static/js templates logs
mkdir -p engine/storage_engine/bookie_storage/football

# Verify installations
echo "🔍 Verifying installations..."
python -c "import flask; print(f'Flask version: {flask.__version__}')"
python -c "import requests; print(f'Requests version: {requests.__version__}')"
python -c "import PIL; print(f'Pillow version: {PIL.__version__}')"

if [ "$RENDER" = "true" ]; then
    echo "🔍 Verifying Tesseract installation..."
    tesseract --version || echo "⚠️ Tesseract not found in PATH"
fi

echo "✅ Build complete! 🚀"