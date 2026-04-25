FROM python:3.11-slim

# Install minimal LibreOffice + fix Java/path issues
RUN apt-get update && apt-get install -y \
    libreoffice-writer \
    libreoffice-core \
    default-jre-headless \
    fonts-liberation \
    fonts-dejavu-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/lib/libreoffice/program/soffice /usr/local/bin/soffice

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p uploads /tmp && chmod 777 uploads /tmp

EXPOSE 10000

CMD ["/usr/lib/libreoffice/program/soffice", "--headless", "--invisible", "--nocrash-report", "--nodefault", "--safemode", "--nologo", "--headless", "--convert-to", "docx", "--outdir", "/app/uploads", "/app/uploads/test.pdf"]
