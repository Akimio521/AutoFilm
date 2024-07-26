#!/usr/bin/env python3
# encoding: utf-8

from typing import Optional
from urllib.parse import quote

class AlistPath:
    """
    Alist 文件/目录对象
    """
    def __init__(
        self,
        server_url: str,
        base_path: str,
        path: str,
        name: str,
        size: int,
        is_dir: bool,
        modified: Optional[str] = None,
        created: Optional[str] = None,
        sign: str = "",
        thumb: Optional[str] = None,
        type: Optional[int] = None,
        hashinfo: Optional[str] = None,
        hash_info: Optional[str] = None,
        raw_url: Optional[str] = None,
        readme: Optional[str] = None,
        header: Optional[dict] = None,
        provider: Optional[str] = None,
        **_,
    ):
        """
        Alist 文件/目录对象
        :param server_url: Alist 服务器地址
        :param base_path: Alist 服务器基础路径
        :param path: 文件/目录路径
        :param name: 文件/目录名称
        :param size: 文件大小
        :param is_dir: 是否为目录
        :param modified: 最后修改时间
        :param created: 创建时间
        :param sign: 签名
        :param thumb: 缩略图
        :param type: 文件类型
        :param hashinfo: Hash 信息
        :param hash_info: Hash 信息
        :param raw_url: 原始地址
        :param readme: 说明
        :param header: 头信息
        :param provider: 存储器提供者
        """
        self.server_url = server_url
        self.base_path = base_path.rstrip("/") + "/"
        self.path = path.rstrip("/")
        self.name = name
        self.size = size
        self.is_dir = is_dir
        self.modified = modified
        self.created = created
        self.sign = sign
        self.thumb = thumb if thumb else None
        self.type = type
        self.hashinfo = hashinfo if hashinfo else None
        self.hash_info = hash_info
        self.raw_url = raw_url
        self.readme = readme
        self.header = header
        self.provider = provider

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
            url =  self.server_url + "/d" + self.abs_path + "?sign=" + self.sign
        else:
            url = self.server_url + "/d" + self.abs_path
        
        return quote(url, safe = "@#$&=:/,;?+\'")
    
    @property
    def suffix(self):
        """
        文件后缀
        """
        if self.is_dir:
            return ""
        else:
            return "." + self.name.split(".")[-1]
