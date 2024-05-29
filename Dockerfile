FROM python:3.11-alpine

ENV INTERVAL=3600 \
    TZ=Asia/Shanghai

WORKDIR "/app"

COPY . .
RUN apk update \
    && apk upgrade \
    && apk add git curl \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf \
        ./config/* \
        ./.github \
        ./.gitignore \
        ./Dockerfile \
        ./README.md \
        ./requirements.txt \
        ./LICENSE \
        /tep/* \
        /var/lib/apt/lists/* \
        /var/tmp/*

# 赋予入口点脚本执行权限
RUN chmod +x entrypoint.sh

VOLUME ["/app/config", "/app/media"]
ENTRYPOINT ["/entrypoint.sh"]
