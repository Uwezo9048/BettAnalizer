#!/bin/bash
echo "🚀 Starting build process for BetAnalyzer..."

# Install Tesseract OCR for Render (if running on Render)
if [ "$RENDER" = "true" ]; then
    echo "📦 Installing Tesseract OCR for image processing..."
    apt-get update
    apt-get install -y tesseract-ocr tesseract-ocr-eng
    echo "✅ Tesseract OCR installed successfully"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p static/css static/js templates logs

echo "✅ Build complete! 🚀"