#!/bin/bash
echo "🚀 Starting build process for BetAnalyzer..."

# Exit on error
set -e

# Install system dependencies for Render
if [ "$RENDER" = "true" ]; then
    echo "========================================="
    echo "📦 Installing Tesseract OCR on Render..."
    echo "========================================="
    
    # Update package list
    echo "📦 Updating package list..."
    apt-get update -qq
    
    # Remove any existing Tesseract (clean install)
    echo "🗑️ Removing any existing Tesseract installation..."
    apt-get remove -y tesseract-ocr tesseract-ocr-eng || true
    apt-get autoremove -y || true
    
    # Install Tesseract with all dependencies
    echo "📦 Installing Tesseract OCR..."
    apt-get install -y -qq \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-fra \
        tesseract-ocr-deu \
        tesseract-ocr-spa \
        tesseract-ocr-ita \
        tesseract-ocr-por \
        tesseract-ocr-rus \
        tesseract-ocr-ara \
        libtesseract-dev \
        libleptonica-dev
    
    # Verify installation
    echo "🔍 Verifying Tesseract installation..."
    if [ -f "/usr/bin/tesseract" ]; then
        echo "✅ Tesseract found at: /usr/bin/tesseract"
        /usr/bin/tesseract --version || echo "⚠️ Version check failed"
        
        # Test Tesseract with a simple command
        echo "🧪 Testing Tesseract..."
        echo "Hello World" | /usr/bin/tesseract stdin stdout -l eng || echo "⚠️ Test failed"
    else
        echo "❌ Tesseract not found at /usr/bin/tesseract"
        # Try to find it
        find /usr -name "tesseract" 2>/dev/null || echo "Tesseract not found anywhere"
    fi
    
    # Set environment variable
    export TESSERACT_CMD=/usr/bin/tesseract
    echo "✅ TESSERACT_CMD set to: $TESSERACT_CMD"
    
    echo "========================================="
    echo "✅ Tesseract installation complete!"
    echo "========================================="
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

# Verify Python installations
echo "🔍 Verifying Python installations..."
python -c "import flask; print(f'✅ Flask version: {flask.__version__}')"
python -c "import requests; print(f'✅ Requests version: {requests.__version__}')"
python -c "import PIL; print(f'✅ Pillow version: {PIL.__version__}')"
python -c "import pytesseract; print(f'✅ PyTesseract version: {pytesseract.__version__}')"

if [ "$RENDER" = "true" ]; then
    echo "🔍 Final Tesseract verification..."
    echo "Tesseract path: $(which tesseract 2>/dev/null || echo 'Not found')"
    tesseract --version 2>/dev/null || echo "Tesseract command not found"
fi

echo "========================================="
echo "✅ Build complete! 🚀"
echo "========================================="