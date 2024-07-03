FROM python:3.12.4-alpine

ENV TZ=Asia/Shanghai \
    CONFIG_PATH=/app/config/config.yaml \
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

WORKDIR "/app"

COPY main.py autofilm.py version.py /app/
COPY modules /app/modules

VOLUME ["/app/config", "/app/media"]
ENTRYPOINT ["/entrypoint.sh"]
