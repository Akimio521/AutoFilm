FROM python:3.11-alpine

ENV INTERVAL=3600 \
    TZ=Asia/Shanghai

WORKDIR "/app"

COPY . .
RUN apk update \
    && apk upgrade \
    && apk add bash \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf \
        ./config/* \
        ./.github \
        .git \
        ./.gitignore \
        ./Dockerfile \
        ./README.md \
        ./requirements.txt \
        ./LICENSE \
        /tep/* \
        /var/lib/apt/lists/* \
        /var/tmp/* \
    && chmod +x entrypoint.sh \
    && sed -i 's/\r//' entrypoint.sh

VOLUME ["/app/config", "/app/media"]
ENTRYPOINT ["/app/entrypoint.sh"]
