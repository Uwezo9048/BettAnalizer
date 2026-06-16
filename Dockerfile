FROM python:3.11-slim

# Install Tesseract with explicit package names
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libleptonica-dev \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create symlink if needed (sometimes tesseract installs to a different location)
RUN if [ -f "/usr/bin/tesseract" ]; then \
        echo "Tesseract found at /usr/bin/tesseract"; \
    elif [ -f "/usr/local/bin/tesseract" ]; then \
        ln -s /usr/local/bin/tesseract /usr/bin/tesseract; \
    else \
        echo "Tesseract not found in standard locations"; \
    fi

# Verify Tesseract installation
RUN tesseract --version || echo "Tesseract not available"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV TESSERACT_CMD=/usr/bin/tesseract
ENV RENDER=true
ENV LIVE_FEEDS_ENABLED=true
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "app:app"]