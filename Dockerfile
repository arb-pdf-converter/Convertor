FROM python:3.11-slim

# Install LibreOffice + minimal deps
RUN apt-get update && apt-get install -y \
    libreoffice-writer \
    libreoffice-core \
    openjdk-17-jre-headless \
    fonts-liberation \
    fonts-dejavu-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Create & fix permissions
RUN mkdir -p uploads /tmp /var/lib/libreoffice /root/.config \
    && chmod 777 uploads /tmp /var/lib/libreoffice /root/.config

EXPOSE 10000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "300", "--workers", "1"]
