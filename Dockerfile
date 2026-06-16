FROM python:3.11-slim

# Install Tesseract OCR
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libleptonica-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set Tesseract path
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV RENDER=true

# Expose port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "app:app"]