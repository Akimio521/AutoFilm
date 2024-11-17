#!/usr/bin/env python3
# encoding: utf-8

from json import loads, dumps


class AlistStorage:
    """
    Alist 存储器模型
    """

    def __init__(
        self,
        id: int = 0,
        status: str = "",
        remark: str = "",
        modified: str = "",
        disabled: bool = False,
        mount_path: str = "",
        order: int = 0,
        driver: str = "Local",
        cache_expiration: int = 30,
        addition: str = "{}",
        enable_sign: bool = False,
        order_by: str = "name",
        order_direction: str = "asc",
        extract_folder: str = "front",
        web_proxy: bool = False,
        webdav_policy: str = "native_proxy",
        down_proxy_url: str = "",
        **_,
    ) -> None:
        """
        :param id: 存储器 ID
        :param status: 状态
        :param remark: 备注
        :param modified: 修改时间
        :param disabled: 是否禁用
        :param mount_path: 挂载路径
        :param order: 排序
        :param driver: 驱动
        :param cache_expiration: 缓存过期时间
        :param addition: 附加信息
        :param enable_sign: 是否启用
        :param order_by: 排序方式
        :param order_direction: 排序方向
        :param extract_folder: 提取文件夹
        :param web_proxy: 是否启用 Web 代理
        :param webdav_policy: WebDAV 策略
        :param down_proxy_url: 下载代理 URL
        """
        self.id = id
        self.mount_path = mount_path
        self.order = order
        self.driver = driver
        self.cache_expiration = cache_expiration
        self.status = status
        self.__addition = addition
        self.remark = remark
        self.modified = modified
        self.disabled = disabled
        self.enable_sign = enable_sign
        self.order_by = order_by
        self.order_direction = order_direction
        self.extract_folder = extract_folder
        self.web_proxy = web_proxy
        self.webdav_policy = webdav_policy
        self.down_proxy_url = down_proxy_url

    @property
    def addition(self) -> dict:
        """
        将原本的 JSON 字符串转换为 Python 字典
        """
        return loads(self.__addition)
    
    @property
    def raw_addition(self) -> str:
        """
        返回原始的 JSON 字符串
        """
        return self.__addition
    
    def change_addition(self, dictionary: dict) -> None:
        """
        修改 Storage 附加信息
        """
        self.__addition = dumps(dictionary)
