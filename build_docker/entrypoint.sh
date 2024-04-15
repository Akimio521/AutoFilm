#!/bin/bash

#获取容器名
container_id=$(hostname)

# 检查本地 version.py 中的 APP_VERSION
local_version=$(grep 'APP_VERSION = ' version.py | cut -d"'" -f2)

# 下载远程 version.py 文件并读取其中的 APP_VERSION
remote_version=$(curl -s https://mirror.ghproxy.com/https://raw.githubusercontent.com/Akimio521/AutoFilm/main/version.py | grep 'APP_VERSION = ' | cut -d"'" -f2)

# 比较本地和远程版本，如果远程版本高，则更新应用
if [[ "$remote_version" != "$local_version" ]]; then
    echo "获取到新版本: $remote_version, 正在更新程序..."
    git clone https://mirror.ghproxy.com/https://github.com/Akimio521/AutoFilm.git ./tmp
    cp -r ./tmp/* ./
    rm -rf ./tmp
fi

# 检查是否存在 config.yaml 文件，如果不存在则下载并重命名
if [[ ! -f ./config/config.yaml ]]; then
    echo "config.yaml 不存在，正在从项目中下载。请到映射目录下进行设置！"
    curl -s https://mirror.ghproxy.com/https://raw.githubusercontent.com/Akimio521/AutoFilm/main/config/config.yaml.example -o ./config/config.yaml
	# 在 yaml 文件中增加注释
    echo "# 修改完成后请执行'docker restart $container_id'重启容器" >> ./config/config.yaml
fi

# 使用环境变量中的时间间隔循环执行 Python 应用
while true; do
    echo "正在执行主程序..."
    python main.py
    echo "等待 $INTERVAL 秒后再次执行..."
    sleep $INTERVAL
done
