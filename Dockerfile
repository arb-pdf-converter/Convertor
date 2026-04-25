FROM python:3.11-slim

# Install LibreOffice (LIGHTWEIGHT version)
RUN apt-get update && apt-get install -y \
    libreoffice-writer \
    libreoffice-core \
    fonts-liberation \
    fonts-dejavu-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

WORKDIR /app

COPY . .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Setup folders
RUN mkdir -p uploads && chmod 777 uploads /tmp

EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:10000/api/health || exit 1

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "300", "--workers", "1", "--threads", "2"]
