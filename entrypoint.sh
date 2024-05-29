#!/bin/bash


if [[ ! -f ./config/config.yaml ]]; then
    echo "config.yaml 不存在，正在从项目中下载。请到映射目录下进行设置！"
    curl -s ${proxy}${yaml_url} -o ./config/config.yaml
	# 在 yaml 文件中增加注释
    echo "# 修改完成后请执行'docker restart $container_id'重启容器" >> ./config/config.yaml
fi

if [[ "$INTERVAL" -eq 0 ]]; then
    echo "正在执行主程序..."
    python main.py
    echo "执行完成，程序将关闭。"
else
    while true; do
        echo "正在执行主程序..."
        python main.py
        echo "等待 $INTERVAL 秒后再次执行..."
        sleep $INTERVAL
    done
fi
