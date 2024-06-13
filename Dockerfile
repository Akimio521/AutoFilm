FROM python:3.11-alpine

ENV INTERVAL=3600 \
    TZ=Asia/Shanghai

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

VOLUME ["/app/config", "/app/media"]
ENTRYPOINT ["/entrypoint.sh"]
