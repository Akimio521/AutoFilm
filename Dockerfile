FROM python:3.12.7-alpine

ENV TZ=Asia/Shanghai
VOLUME ["/config", "/logs", "/media"]

RUN apk update && \
    apk add --no-cache \
    build-base \
    linux-headers

COPY requirements.txt requirements.txt

# 安装构建依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir cython setuptools

COPY app ./app

RUN cd app && \
    python setup.py && \
    rm -rf build && \
    cd .. 

RUN apk del build-base linux-headers && \
    find app -type f \( -name "*.py" ! -name "main.py" ! -name "__init__.py" -o -name "*.c" \) -delete && \
    rm -rf /tmp/* && \
    rm requirements.txt && \
    pip uninstall -y cython setuptools

CMD ["python", "/app/main.py"]