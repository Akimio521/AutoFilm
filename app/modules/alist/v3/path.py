from re import sub
from typing import Any

from pydantic import BaseModel

from app.utils import URLUtils


class AlistPath(BaseModel):
    """
    Alist 文件/目录对象
    """

    server_url: str  # 服务器地址
    base_path: str  # 基础路径（用于计算文件/目录在 Alist 服务器上的绝对地址）
    path: str  # 文件/目录路径
    name: str  # 文件/目录名称
    size: int  # 文件大小
    is_dir: bool  # 是否为目录
    modified: str = ""  # 修改时间
    created: str = ""  # 创建时间
    sign: str = ""  # 签名
    thumb: str = ""  # 缩略图
    type: int = ""  # 类型
    hashinfo: str = "null"  # 哈希信息（字符串）
    hash_info: dict | None = None  # 哈希信息（键值对）
    raw_url: str = ""  # 原始地址
    readme: str = ""  # Readme 地址
    header: str = ""  # 头部信息
    provider: str = ""  # 提供者
    related: Any = None  # 相关信息

    @property
    def abs_path(self):
        """
        文件/目录在 Alist 服务器上的绝对路径
        """
        return self.base_path.rstrip("/") + self.path

    @property
    def download_url(self):
        """
        文件下载地址
        """
        if self.sign:
            url = self.server_url + "/d" + self.abs_path + "?sign=" + self.sign
        else:
            url = self.server_url + "/d" + self.abs_path

        return URLUtils.encode(url)

    @property
    def proxy_download_url(self):
        """
        Alist代理下载地址
        """
        return sub(r"/d/", "/p/", self.download_url, 1)

    @property
    def suffix(self):
        """
        文件后缀
        """
        if self.is_dir:
            return ""
        else:
            return "." + self.name.split(".")[-1]


if __name__ == "__main__":
    result = {
        "code": 200,
        "message": "success",
        "data": {
            "content": [
                {
                    "name": "Alist V3.md",
                    "size": 1592,
                    "is_dir": False,
                    "modified": "2024-05-17T13:47:55.4174917+08:00",
                    "created": "2024-05-17T13:47:47.5725906+08:00",
                    "sign": "",
                    "thumb": "",
                    "type": 4,
                    "hashinfo": "null",
                    "hash_info": None,
                }
            ],
            "total": 1,
            "readme": "",
            "header": "",
            "write": True,
            "provider": "Local",
        },
    }
    for item in result["data"]["content"]:
        path = AlistPath(
            server_url="https://alist.nn.ci",
            base_path="/",
            path="/",
            **item,
        )
        print(path)
