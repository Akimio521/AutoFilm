#!/bin/bash

if [[ ! -f $CONFIG_PATH ]]; then
    echo "配置文件 $CONFIG_PATH 不存在，请到映射目录下进行设置！"
fi

python /app/main.py