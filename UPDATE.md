我将帮助您添加API触发功能。需要修改以下几个文件：

首先在配置文件中添加API配置项（config.yaml.example）：

config.yaml.example
Apply
Settings:
API_ENABLE: True                     # 启用API接口
API_PORT: 8000                       # API服务端口
API_KEY: your_secret_key             # API访问密钥

# ... 保持其他配置不变 ...
添加API路由模块：

api.py
Apply
from fastapi import APIRouter, Security, HTTPException, status
from fastapi.security import APIKeyHeader

from app.core import settings, logger
from app.modules import Alist2Strm, Ani2Alist

router = APIRouter()
security = APIKeyHeader(name="X-API-Key")

async def get_api_key(api_key: str = Security(security)) -> str:
if api_key != settings.API_KEY:
raise HTTPException(
status_code=status.HTTP_401_UNAUTHORIZED,
detail="Invalid API Key"
)
return api_key

@router.post("/trigger/alist2strm")
async def trigger_alist2strm(
server_id: str,
_: str = Security(get_api_key)
):
logger.info(f"API触发Alist2Strm任务：{server_id}")
# 查找对应配置
server_config = next((s for s in settings.AlistServerList if s["id"] == server_id), None)
if not server_config:
raise HTTPException(status_code=404, detail="Server not found")

    await Alist2Strm(**server_config).run()
    return {"status": "success"}

@router.post("/trigger/ani2alist")
async def trigger_ani2alist(
server_id: str,
_: str = Security(get_api_key)
):
logger.info(f"API触发Ani2Alist任务：{server_id}")
server_config = next((s for s in settings.Ani2AlistList if s["id"] == server_id), None)
if not server_config:
raise HTTPException(status_code=404, detail="Server not found")

    await Ani2Alist(**server_config).run()
    return {"status": "success"}
修改主程序启动逻辑：

main.py
Apply
from fastapi import FastAPI
import uvicorn

# ... 原有导入保持不变 ...
from app.modules.api import router as api_router

def start_api_server():
app = FastAPI(title=settings.APP_NAME)
app.include_router(api_router)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.API_PORT,
        log_config=None
    )

if __name__ == "__main__":
print_logo()
logger.info(f"AutoFilm {settings.APP_VERSION} 启动中...")

    # 启动API服务器
    if settings.API_ENABLE:
        from threading import Thread
        Thread(target=start_api_server, daemon=True).start()
        logger.info(f"API服务已启动在 {settings.API_PORT} 端口")

    # ... 保持原有调度器逻辑不变 ...
更新依赖：

requirements.txt
fastapi==0.111.0
uvicorn==0.29.0
python-multipart==0.0.9
使用示例：


bash
# 触发Alist2Strm任务
curl -X POST -H "X-API-Key: your_secret_key" http://localhost:8000/trigger/alist2strm?server_id=动漫

# 触发Ani2Alist任务
curl -X POST -H "X-API-Key: your_secret_key" http://localhost:8000/trigger/ani2alist?server_id=动画库
主要改动点：

使用FastAPI提供RESTful API
通过API Key进行身份验证
保持原有定时任务的同时启动API服务
支持通过server_id参数触发特定任务
异步处理请求不阻塞主程序
注意：需要先安装新增的依赖项，并在配置文件中启用API功能。

根据当前配置，建议对Dockerfile进行以下优化改进：


Dockerfile
Apply
# ... 保留现有基础配置 ...

FROM python:3.12.7-alpine

ENV TZ=Asia/Shanghai
VOLUME ["/config", "/logs", "/media"]

# 添加运行时依赖
RUN apk update && \
apk add --no-cache \
tzdata \
curl && \
cp /usr/share/zoneinfo/${TZ} /etc/localtime && \
echo ${TZ} > /etc/timezone

# 创建非root用户
RUN adduser -D appuser && \
chown -R appuser:appuser /app

# 切换用户
USER appuser

# ... 保留后续配置 ...
主要改进点说明：

时区支持增强：显式安装tzdata包并配置时区文件（原配置仅设置TZ变量可能不完全生效）
安全优化：创建专用appuser用户运行应用，避免使用root权限
基础工具：添加curl用于容器调试（可按需移除）
层合并优化：将多个RUN指令合并减少镜像层数
当前Dockerfile已具备良好的多阶段构建结构，以上是可选的优化项。如果不需要调试工具，可以移除curl包的安装。这些修改能帮助生成更安全、时区支持更完善的Docker镜像。

根据当前配置中API_PORT: 8000的设置，建议在 Dockerfile 中添加端口声明。以下是需要修改的部分：


Dockerfile
Apply
# ... 保留现有配置 ...

FROM python:3.12.7-alpine

ENV TZ=Asia/Shanghai
VOLUME ["/config", "/logs", "/media"]
EXPOSE 8000  # 新增端口暴露声明

# ... 保留后续配置 ...
修改说明：

添加 EXPOSE 8000 指令声明容器监听端口
该声明本身不会自动发布端口，但能：
帮助其他开发者快速了解服务端口
在使用 docker run -P 时自动绑定随机公网端口
与 docker-compose 配置形成互补
实际运行时仍需通过 -p 参数映射端口：


```bash
docker run -d -p 8000:8000 your_image
```