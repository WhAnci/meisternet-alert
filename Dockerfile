FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV BROWSER=chrome
ENV CHROME_BINARY_PATH=/usr/bin/chromium
ENV CHROME_DRIVER_PATH=/usr/bin/chromedriver
ENV SELENIUM_HEADLESS=true
ENV DATA_FILE=/data/data.csv
ENV BOT_SETTINGS_FILE=/data/bot_settings.json

RUN printf 'Acquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/99force-ipv4 \
    && sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
