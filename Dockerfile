FROM python:3.11-slim

# FIXED: Minimal LibreOffice + Java + permissions
RUN apt-get update && apt-get install -y \
    libreoffice-writer \
    libreoffice-core \
    openjdk-17-jre-headless \
    fonts-liberation \
    fonts-dejavu-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* \
    && mkdir -p /tmp /var/lib/libreoffice /home/.config \
    && chmod 777 /tmp /var/lib/libreoffice /home/.config

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p uploads && chmod 777 uploads

EXPOSE 10000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "300"]
