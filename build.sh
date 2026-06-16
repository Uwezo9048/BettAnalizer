#!/bin/bash
echo "🚀 Starting build process for BetAnalyzer..."

# Exit on error
set -e

# Install system dependencies for Render
if [ "$RENDER" = "true" ]; then
    echo "========================================="
    echo "📦 Installing Tesseract OCR on Render..."
    echo "========================================="
    
    # Update package list (with non-interactive mode)
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    
    # Install Tesseract with all dependencies
    echo "📦 Installing Tesseract OCR..."
    apt-get install -y -qq \
        tesseract-ocr \
        tesseract-ocr-eng \
        libtesseract-dev \
        libleptonica-dev
    
    # Verify installation
    echo "🔍 Verifying Tesseract installation..."
    if [ -f "/usr/bin/tesseract" ]; then
        echo "✅ Tesseract found at: /usr/bin/tesseract"
        /usr/bin/tesseract --version || echo "⚠️ Version check failed"
    else
        echo "❌ Tesseract not found at /usr/bin/tesseract"
        # Try to find it
        find /usr -name "tesseract" 2>/dev/null || echo "Tesseract not found"
    fi
    
    # Set environment variable for this session
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

# Verify installations
echo "🔍 Verifying Python installations..."
python -c "import flask; print(f'✅ Flask version: {flask.__version__}')"
python -c "import requests; print(f'✅ Requests version: {requests.__version__}')"
python -c "import PIL; print(f'✅ Pillow version: {PIL.__version__}')"
python -c "import pytesseract; print(f'✅ PyTesseract version: {pytesseract.__version__}')"

if [ "$RENDER" = "true" ]; then
    echo "🔍 Final Tesseract verification..."
    # Check if Tesseract exists
    if [ -f "/usr/bin/tesseract" ]; then
        echo "✅ Tesseract confirmed at /usr/bin/tesseract"
        export TESSERACT_CMD=/usr/bin/tesseract
        echo "✅ TESSERACT_CMD set to: $TESSERACT_CMD"
    else
        echo "❌ Tesseract not found on Render!"
        # Try to find it
        echo "Searching for Tesseract..."
        find / -name "tesseract" -type f 2>/dev/null | head -5 || echo "Tesseract not found"
    fi
fi

echo "========================================="
echo "✅ Build complete! 🚀"
echo "========================================="