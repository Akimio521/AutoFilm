#!/bin/bash

if [[ ! -f $CONFIG_PATH ]]; then
    echo "配置文件 $CONFIG_PATH 不存在，请到映射目录下进行设置！"
fi

if [[ "$INTERVAL" -eq 0 ]]; then
    echo "正在执行主程序..."
    python /app/main.py --config_path $CONFIG_PATH --log_level $LOG_LEVEL
    echo "执行完成，容器即将退出。"
else
    while true; do
        echo "正在执行主程序..."
        python /app/main.py --config_path $CONFIG_PATH --log_level $LOG_LEVEL
        echo "等待 $INTERVAL 秒后再次执行..."
        sleep $INTERVAL
    done
fi