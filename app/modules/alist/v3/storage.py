from json import loads, dumps
from typing import Literal
from types import FunctionType

from pydantic import BaseModel, ConfigDict, model_validator


class AlistStorage(BaseModel):
    """
    Alist 存储器模型
    """

    model_config = ConfigDict(
        ignored_types=(FunctionType, type(lambda: None))  # 覆盖 Cython 类型
    )

    id: int = 0  # 存储器 ID
    status: Literal["work", "disabled"] = "work"  # 存储器状态
    remark: str = ""  # 备注
    modified: str = ""  # 修改时间
    disabled: bool = False  # 是否禁用
    mount_path: str = ""  # 挂载路径
    order: int = 0  # 排序
    driver: str = "Local"  # 驱动器
    cache_expiration: int = 30  # 缓存过期时间
    addition: str = "{}"  # 附加信息
    enable_sign: bool = False  # 是否启用签名
    order_by: str = "name"  # 排序字段
    order_direction: str = "asc"  # 排序方向
    extract_folder: str = "front"  # 提取文件夹
    web_proxy: bool = False  # 是否启用 Web 代理
    webdav_policy: str = "native_proxy"  # WebDAV 策略
    down_proxy_url: str = ""  # 下载代理 URL

    def set_addition_by_dict(self, additon: dict) -> None:
        """
        使用 Python 字典设置 Storage 附加信息
        """
        self.addition = dumps(additon)

    @property
    def addition2dict(self) -> dict:
        """
        获取 Storage 附加信息，返回Python 字典
        """
        return loads(self.addition)

    @model_validator(mode="before")
    def check_status(cls, values: dict) -> dict:
        status = values.get("status")
        disabled = values.get("disabled")
        if (disabled and status == "work") or (not disabled and status == "disabled"):
            raise ValueError(f"存储器状态错误，{status=}, {disabled=}")
        return values


if __name__ == "__main__":
    info = {
        "id": 1,
        "mount_path": "/lll",
        "order": 0,
        "driver": "Local",
        "cache_expiration": 0,
        "status": "work",
        "addition": '{"root_folder_path":"/root/www","thumbnail":false,"thumb_cache_folder":"","show_hidden":true,"mkdir_perm":"777"}',
        "remark": "",
        "modified": "2023-07-19T09:46:38.868739912+08:00",
        "disabled": False,
        "enable_sign": False,
        "order_by": "name",
        "order_direction": "asc",
        "extract_folder": "front",
        "web_proxy": False,
        "webdav_policy": "native_proxy",
        "down_proxy_url": "",
    }
    storage = AlistStorage(**info)
    print(storage)
    print(storage.addition2dict)
    storage.set_addition_by_dict({"test": 1})
    print(storage.addition)
    print(storage.addition2dict)
    storage.addition = '{"test": 2}'
    print(storage.addition)
    print(storage.addition2dict)
