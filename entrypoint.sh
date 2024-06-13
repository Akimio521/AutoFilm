#!/bin/bash

if [[ ! -f /app/config/config.yaml ]]; then
    echo "配置文件 config.yaml 不存在，请到映射目录下进行设置！"
fi

if [[ "$INTERVAL" -eq 0 ]]; then
    echo "正在执行主程序..."
    python main.py
    echo "执行完成，容器即将退出。"
else
    while true; do
        echo "正在执行主程序..."
        python /app/main.py
        echo "等待 $INTERVAL 秒后再次执行..."
        sleep $INTERVAL
    done
fi