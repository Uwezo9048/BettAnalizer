#!/bin/bash
echo "🚀 Installing dependencies..."

# Install Tesseract OCR for Render (Linux)
if [ "$RENDER" = "true" ]; then
    echo "📦 Installing Tesseract OCR..."
    apt-get update
    apt-get install -y tesseract-ocr tesseract-ocr-eng
fi

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Build complete!"