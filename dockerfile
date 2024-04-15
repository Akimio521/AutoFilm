# 使用 Python 3.10.8 的基础镜像
FROM python:3.10.8

# 安装 Git 和 Curl（用于下载远程文件）
RUN apt-get update && apt-get install -y git curl

# 设置工作目录
WORKDIR /app

# 克隆代码库到当前工作目录
RUN git clone https://github.com/Akimio521/AutoFilm.git ./

# 重命名配置文件
RUN mv config/config.yaml.example config/config.yaml

# 安装依赖项
RUN pip install --no-cache-dir -r requirements.txt

# 将入口点脚本添加到容器中
COPY entrypoint.sh /entrypoint.sh

# 赋予入口点脚本执行权限
RUN chmod +x /entrypoint.sh

# 设置默认的时间间隔环境变量，单位为秒
ENV INTERVAL=3600
ENV TZ=Asia/Shanghai

# 设置容器的默认入口点
ENTRYPOINT ["/entrypoint.sh"]
