FROM python:3.11-slim

# Install LibreOffice
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    libreoffice-core \
    libreoffice-common \
    fonts-dejavu \
    fonts-liberation \
    && apt-get clean

# Set working dir
WORKDIR /app

# Copy files
COPY . .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Create uploads folder
RUN mkdir -p uploads

# Start app
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
