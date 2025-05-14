from fastapi import APIRouter, Security, HTTPException, status, Depends  # 新增 Depends
from fastapi.security import APIKeyHeader

from app.core import settings, logger
from app.modules import Alist2Strm, Ani2Alist

router = APIRouter()
security = APIKeyHeader(name="X-API-Key")

async def get_api_key(api_key: str = Depends(security)) -> str:  # 修改 Security 为 Depends
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return api_key

@router.post("/trigger/alist2strm")
async def trigger_alist2strm(
    server_id: str,
    _: str = Depends(get_api_key)  # 修改 Security 为 Depends
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
    _: str = Depends(get_api_key)  # 修改 Security 为 Depends
):
    logger.info(f"API触发Ani2Alist任务：{server_id}")
    server_config = next((s for s in settings.Ani2AlistList if s["id"] == server_id), None)
    if not server_config:
        raise HTTPException(status_code=404, detail="Server not found")

    await Ani2Alist(**server_config).run()
    return {"status": "success"}