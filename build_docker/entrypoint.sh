#!/bin/bash

#获取容器名
container_id=$(hostname)

# 设置基础URL和代理
code_url="https://github.com/Akimio521/AutoFilm.git"
version_url="https://raw.githubusercontent.com/Akimio521/AutoFilm/main/version.py"
yaml_url="https://raw.githubusercontent.com/Akimio521/AutoFilm/main/config/config.yaml.example"

if [[ "$CN_UPDATE" == "true" ]]; then
    proxy="https://mirror.ghproxy.com/"
else
    proxy=""
fi

# 检查本地 version.py 中的 APP_VERSION
local_version=$(grep 'APP_VERSION = ' version.py | cut -d"'" -f2)

# 下载远程 version.py 文件并读取其中的 APP_VERSION
remote_version=$(curl -s ${proxy}${version_url} | grep 'APP_VERSION = ' | cut -d"'" -f2)

# 比较本地和远程版本，如果设置了AUTO_UPDATE为true且远程版本高，则更新应用
if [[ "$AUTO_UPDATE" == "true" && "$remote_version" != "$local_version" ]]; then
    echo "环境变量 AUTO_UPDATE 设置为 true，正在执行自动更新程序，获取到新版本: $remote_version"
    git clone ${proxy}${code_url} ./tmp
    cp -r ./tmp/* ./
    rm -rf ./tmp
fi

# 检查是否存在 config.yaml 文件，如果不存在则下载并重命名
if [[ ! -f ./config/config.yaml ]]; then
    echo "config.yaml 不存在，正在从项目中下载。请到映射目录下进行设置！"
    curl -s ${proxy}${yaml_url} -o ./config/config.yaml
	# 在 yaml 文件中增加注释
    echo "# 修改完成后请执行'docker restart $container_id'重启容器" >> ./config/config.yaml
fi

# 使用环境变量中的时间间隔循环执行 Python 应用
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
