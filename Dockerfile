FROM python:3.11-slim

# ============================================
# INSTALL TESSERACT OCR
# ============================================
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-spa \
    tesseract-ocr-ita \
    tesseract-ocr-por \
    libtesseract-dev \
    libleptonica-dev \
    && rm -rf /var/lib/apt/lists/*

# Verify Tesseract installation
RUN tesseract --version

# ============================================
# SETUP PYTHON ENVIRONMENT
# ============================================
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# ============================================
# ENVIRONMENT VARIABLES
# ============================================
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV RENDER=true
ENV LIVE_FEEDS_ENABLED=true
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# ============================================
# EXPOSE PORT AND RUN
# ============================================
EXPOSE 5000

CMD ["gunicorn", "app:app"]