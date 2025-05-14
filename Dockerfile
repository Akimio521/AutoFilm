FROM python:3.12.7-alpine AS builder
WORKDIR /builder

RUN apk update && \
    apk add --no-cache \
    build-base \
    linux-headers

# 安装构建依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir cython setuptools

COPY setup.py setup.py
COPY app ./app

RUN python setup.py

RUN apk del build-base linux-headers && \
    find app -type f \( -name "*.py" ! -name "main.py" ! -name "__init__.py" -o -name "*.c" \) -delete 

FROM python:3.12.7-alpine

ENV TZ=Asia/Shanghai
VOLUME ["/config", "/logs", "/media"]
#EXPOSE 8000  # 新增端口暴露声明

# 添加运行时依赖
RUN apk update && \
    apk add --no-cache \
    tzdata \
    curl && \
    cp /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo ${TZ} > /etc/timezone

# 创建非root用户
RUN adduser -D appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# 切换用户
USER appuser

RUN apk update && \
    apk add --no-cache \
    build-base \
    linux-headers

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt 

COPY --from=builder /builder/app /app

RUN apk del build-base linux-headers && \
    rm -rf /tmp/* 

ENTRYPOINT ["python", "/app/main.py"]