FROM python:3.11-slim

# Install LibreOffice + fonts (HIGH QUALITY)
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-draw \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-dejavu \
    ttf-mscorefonts-installer \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create uploads folder
RUN mkdir -p uploads && chmod 777 uploads

# Expose port
EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:10000/api/health || exit 1

# Start with gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "180", "--workers", "1"]
