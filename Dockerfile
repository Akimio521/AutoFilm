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
COPY setup.py.simple setup.py.simple
COPY app ./app

# 跳过 Cython 编译以解决架构兼容性问题
RUN mv setup.py setup.py.original && \
    mv setup.py.simple setup.py && \
    python setup.py && \
    mv setup.py.original setup.py

RUN apk del build-base linux-headers && \
    find app -type f \( -name "*.c" \) -delete && \
    find app -type f -name "*.py" ! -name "main.py" ! -name "__init__.py" ! -name "config.py" ! -name "log.py" ! -name "version.py" -delete

FROM python:3.12.7-alpine

ENV TZ=Asia/Shanghai
VOLUME ["/config", "/logs", "/media"]

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