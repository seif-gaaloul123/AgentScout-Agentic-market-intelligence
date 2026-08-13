FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt taskiq-redis && \
    playwright install --with-deps chromium

COPY . .

CMD ["taskiq", "worker", "main:broker"]
