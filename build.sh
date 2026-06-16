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
    
    # Verify Tesseract installation
    echo "🔍 Verifying Tesseract installation..."
    if [ -f "/usr/bin/tesseract" ]; then
        echo "✅ Tesseract found at /usr/bin/tesseract"
        /usr/bin/tesseract --version || echo "⚠️ Tesseract version check failed"
    else
        echo "⚠️ Tesseract not found at /usr/bin/tesseract"
        # Try to find it
        which tesseract || echo "Tesseract not in PATH"
    fi
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

# Verify installations
echo "🔍 Verifying Python installations..."
python -c "import flask; print(f'Flask version: {flask.__version__}')"
python -c "import requests; print(f'Requests version: {requests.__version__}')"
python -c "import PIL; print(f'Pillow version: {PIL.__version__}')"
python -c "import pytesseract; print(f'PyTesseract version: {pytesseract.__version__}')"

if [ "$RENDER" = "true" ]; then
    echo "🔍 Final Tesseract verification..."
    # Set TESSERACT_CMD environment variable
    export TESSERACT_CMD=/usr/bin/tesseract
    echo "✅ TESSERACT_CMD set to: $TESSERACT_CMD"
fi

echo "✅ Build complete! 🚀"