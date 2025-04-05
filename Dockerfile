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

# 安装编译依赖来构建psutil
RUN apk update && \
    apk add --no-cache \
    gcc \
    python3-dev \
    musl-dev \
    linux-headers

COPY requirements.txt requirements.txt
# 确保requirements.txt中包含psutil
RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

COPY --from=builder /builder/app /app

# 删除不再需要的编译工具
RUN apk del gcc python3-dev musl-dev linux-headers && \
    rm -rf /tmp/* 

ENTRYPOINT ["python", "/app/main.py"]
