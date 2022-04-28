FROM ghcr.io/siwatinc/python-baseimage:python3

LABEL Maintainer="tontan2203"

WORKDIR /usr/app/src

COPY requirements.txt .

RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY scraper.py .

ADD ./entrypoint.sh /entrypoint.sh

CMD bash /entrypoint.sh
