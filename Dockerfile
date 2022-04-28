FROM python:latest
LABEL Maintainer="tontan2203"

WORKDIR /usr/app/src

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY scraper.py .

CMD (source /config/.env || :) && python scraper.py && tail -f /dev/null