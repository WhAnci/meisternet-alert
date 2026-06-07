FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV BROWSER=chrome
ENV CHROME_BINARY_PATH=/usr/bin/chromium
ENV CHROME_DRIVER_PATH=/usr/bin/chromedriver
ENV SELENIUM_HEADLESS=true
ENV DATA_FILE=/data/data.csv
ENV BOT_SETTINGS_FILE=/data/bot_settings.json

RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
