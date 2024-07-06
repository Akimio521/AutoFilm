FROM python:3.12.4-alpine

ENV TZ=Asia/Shanghai \
    CONFIG_PATH=/config/config.yaml \
    LOG_LEVEL=INFO\
    INTERVAL=3600

COPY entrypoint.sh entrypoint.sh

RUN sed -i 's/\r//' entrypoint.sh \
    && chmod +x entrypoint.sh

RUN apk update \
    && apk upgrade \
    && apk add bash \
    && rm -rf \
        /tep \
        /var/lib/apt/lists \
        /var/tmp

COPY requirements.txt requirements.txt

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf requirements.txt

COPY app /app

VOLUME ["/config", "/media"]
ENTRYPOINT ["/entrypoint.sh"]
