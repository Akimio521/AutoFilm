FROM python:3.12.7-alpine

ENV TZ=Asia/Shanghai
VOLUME ["/config", "/logs", "/media"]

RUN apk update && \
    apk upgrade && \
    apk add bash build-base linux-headers --no-cache 

COPY requirements.txt requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf requirements.txt

RUN apk del build-base linux-headers && \
    rm -rf /tep /var/lib/apt/lists /var/tmp

COPY app /app

CMD python /app/main.py
