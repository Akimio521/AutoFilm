FROM python:3.12.7-alpine

ENV TZ=Asia/Shanghai
VOLUME ["/config", "/logs", "/media"]

RUN apk update &&\
    apk upgrade &&\
    apk add bash &&\
    rm -rf /tep /var/lib/apt/lists /var/tmp

COPY requirements.txt requirements.txt

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf requirements.txt

COPY app /app

CMD python /app/main.py
