#!/usr/bin/env python3
# encoding: utf-8

from json import dumps
from typing import Callable, AsyncGenerator
import asyncio

from aiohttp import ClientSession

from app.core import logger
from app.utils import retry
from app.modules.alist.v3.alist_path import AlistPath
from app.modules.alist.v3.alist_storage import AlistStorage


class AlistClient:
    """
    Alist 客户端 API
    """

    def __init__(self, url: str, username: str, password: str) -> None:
        """
        AlistClient 类初始化

        :param url: Alist 服务器地址
        :param username: Alist 用户名
        :param password: Alist 密码
        """
        self.__HEADERS = {
            "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
            "Content-Type": "application/json",
        }

        if not url.startswith("http"):
            url = "https://" + url
        self.url = url.rstrip("/")

        self.username = username
        self.__password = password
        self.__dir = "/"

    @retry(RuntimeError, tries=3, delay=3, backoff=1, logger=logger, ret=None)
    async def async_api_auth_login(self) -> None:
        """
        登录 Alist 服务器认证账户信息
        将登录令牌保存在 session 中
        """
        data = dumps({"username": self.username, "password": self.__password})
        api_url = self.url + "/api/auth/login"
        async with self.__session.post(api_url, data=data) as resp:

            if resp.status != 200:
                raise RuntimeError(f"登录请求发送失败，状态码：{resp.status}")

            result = await resp.json()

        if result["code"] != 200:
            raise RuntimeError(f'登录失败，错误信息：{result["message"]}')

        logger.debug(f"{self.username}登录成功")
        self.__HEADERS.update({"Authorization": result["data"]["token"]})

        if self.__session:
            await self.__session.close()
        self.__session = ClientSession(headers=self.__HEADERS)

    @retry(RuntimeError, tries=3, delay=3, backoff=1, logger=logger, ret=None)
    async def async_api_me(self) -> None:
        """
        获取用户信息
        获取当前用户 base_path 和 id 并分别保存在 self.base_path 和 self.id 中
        """
        api_url = self.url + "/api/me"
        async with self.__session.get(api_url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"获取用户信息请求发送失败，状态码：{resp.status}")

            result = await resp.json()

        if result["code"] != 200:
            raise RuntimeError(f'获取用户信息失败，错误信息：{result["message"]}')

        try:
            self.base_path: str = result["data"]["base_path"]
            self.id: int = result["data"]["id"]
        except:
            raise RuntimeError("获取用户信息失败")

    @retry(RuntimeError, tries=3, delay=3, backoff=1, logger=logger, ret=[])
    async def async_api_fs_list(
        self, path: AlistPath | str | None = None
    ) -> list[AlistPath]:
        """
        获取文件列表

        :param dir_path: 文件路径（默认为当前目录 self.pwd）
        :return: AlistPath 对象列表
        """
        if isinstance(path, AlistPath):
            if path.is_dir:
                dir_path_str = path.path
            else:
                dir_path_str = self.pwd
        elif isinstance(path, str):
            dir_path_str = path.rstrip("/") + "/"
        else:
            dir_path_str = self.pwd
        logger.debug(f"获取目录{dir_path_str}下的文件列表")

        api_url = self.url + "/api/fs/list"
        payload = dumps(
            {
                "path": dir_path_str,
                "password": "",
                "page": 1,
                "per_page": 0,
                "refresh": False,
            }
        )

        try:
            async with self.__session.post(api_url, data=payload) as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        f"获取目录{dir_path_str}的文件列表请求发送失败，状态码：{resp.status}"
                    )

                result = await resp.json()
        except asyncio.TimeoutError:
            raise RuntimeError("获取目录{dir_path_str}的文件列表的请求超时")

        if result["code"] != 200:
            raise RuntimeError(
                f'获取目录{dir_path_str}的文件列表失败，错误信息：{result["message"]}'
            )

        logger.debug(f"获取目录{dir_path_str}的文件列表成功")
        try:
            return [
                AlistPath(
                    server_url=self.url,
                    base_path=self.base_path,
                    path=dir_path_str + path["name"],
                    **path,
                )
                for path in result["data"]["content"]
            ]
        except Exception as e:
            raise RuntimeError(
                f"返回目录{dir_path_str}的AlistPath对象列表失败，错误信息：{e}"
            )

    @retry(RuntimeError, tries=3, delay=3, backoff=1, logger=logger, ret=None)
    async def async_api_fs_get(
        self, path: AlistPath | str | None = None
    ) -> AlistPath | None:
        """
        获取文件/目录详细信息

        :param path: 文件/目录路径/AlistPath 对象
        :return: AlistPath 对象
        """
        if isinstance(path, AlistPath):
            path_str = path.path
        elif isinstance(path, str):
            path_str = path.rstrip("/") + "/"
        elif path is None:
            path_str = self.pwd
        else:
            logger.warning(
                f"传入参数 path({type(path_str)}) 类型错误，使用当前目录 {self.__dir} 作为路径"
            )
            path_str = self.pwd

        api_url = self.url + "/api/fs/get"
        payload = dumps(
            {
                "path": path_str,
                "password": "",
                "page": 1,
                "per_page": 0,
                "refresh": False,
            }
        )

        try:
            async with self.__session.post(api_url, data=payload) as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        f"获取路径{path_str}详细信息请求发送失败，状态码：{resp.status}"
                    )
                result = await resp.json()
        except asyncio.TimeoutError:
            raise RuntimeError("获取路径{path_str}详细信息的请求超时")

        if result["code"] != 200:
            raise RuntimeError(
                f'获取路径{path_str}详细信息失败，详细信息：{result["message"]}'
            )

        logger.debug(f"获取路径{path_str}详细信息成功")
        try:
            return AlistPath(
                server_url=self.url,
                base_path=self.base_path,
                path=path_str,
                **result["data"],
            )
        except Exception as e:
            raise RuntimeError(f"返回路径{path_str}的AlistPath对象失败，错误信息：{e}")

    @retry(RuntimeError, tries=3, delay=3, backoff=1, logger=logger, ret=[])
    async def async_api_admin_storage_list(self) -> list[AlistStorage]:
        """
        列出存储列表 需要管理员用户权限

        :return: AlistStorage 对象列表
        """
        api_url = self.url + "/api/admin/storage/list"

        async with self.__session.get(api_url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"获取存储器列表请求发送失败，状态码：{resp.status}")

            result = await resp.json()

        if result["code"] != 200:
            raise RuntimeError(f'获取存储器列表失败，详细信息：{result["message"]}')

        logger.debug("获取存储器列表成功")
        try:
            return [AlistStorage(**storage) for storage in result["data"]["content"]]
        except Exception as e:
            raise RuntimeError(f"返回AlistStorage对象列表失败，错误信息：{e}")

    @retry(RuntimeError, tries=3, delay=3, backoff=1, logger=logger, ret=None)
    async def async_api_admin_storage_create(self, storage: AlistStorage) -> None:
        """
        创建存储 需要管理员用户权限

        :param storage: AlistStorage 对象
        """
        api_url = self.url + "/api/admin/storage/create"
        payload = dumps(
            {
                "mount_path": storage.mount_path,
                "order": storage.order,
                "remark": storage.remark,
                "cache_expiration": storage.cache_expiration,
                "web_proxy": storage.web_proxy,
                "webdav_policy": storage.webdav_policy,
                "down_proxy_url": storage.down_proxy_url,
                "enable_sign": storage.enable_sign,
                "driver": storage.driver,
                "order_by": storage.order_by,
                "order_direction": storage.order_direction,
                "addition": storage.raw_addition,
            }
        )
        async with self.__session.post(api_url, data=payload) as resp:
            if resp.status != 200:
                raise RuntimeError(f"创建存储请求发送失败，状态码：{resp.status}")
            result = await resp.json()

        if result["code"] != 200:
            raise RuntimeError(f'创建存储失败，详细信息：{result["message"]}')

        logger.debug("创建存储成功")
        return

    @retry(RuntimeError, tries=3, delay=3, backoff=1, logger=logger, ret=None)
    async def sync_api_admin_storage_update(self, storage: AlistStorage) -> None:
        """
        更新存储，需要管理员用户权限

        :param storage: AlistStorage 对象
        """
        api_url = self.url + "/api/admin/storage/update"
        payload = dumps(
            {
                "id": storage.id,
                "mount_path": storage.mount_path,
                "order": storage.order,
                "driver": storage.driver,
                "cache_expiration": storage.cache_expiration,
                "status": storage.status,
                "addition": storage.raw_addition,
                "remark": storage.remark,
                "modified": storage.modified,
                "disabled": storage.disabled,
                "enable_sign": storage.enable_sign,
                "order_by": storage.order_by,
                "order_direction": storage.order_direction,
                "extract_folder": storage.extract_folder,
                "web_proxy": storage.web_proxy,
                "webdav_policy": storage.webdav_policy,
                "down_proxy_url": storage.down_proxy_url,
            }
        )
        async with self.__session.post(api_url, data=payload) as resp:
            if resp.status != 200:
                raise RuntimeError(f"更新存储请求发送失败，状态码：{resp.status}")

            result = await resp.json()

        if result["code"] != 200:
            raise RuntimeError(f'更新存储器失败，详细信息：{result["message"]}')

        logger.debug(
            f"更新存储器成功，存储器ID：{storage.id}，挂载路径：{storage.mount_path}"
        )
        return

    async def iter_path(
        self,
        dir_path: str | None = None,
        filter: Callable[[AlistPath], bool] = lambda x: True,
    ) -> AsyncGenerator[AlistPath, None]:
        """
        异步路径列表生成器
        返回目录及其子目录的所有文件和目录的 AlistPath 对象

        :param dir_path: 目录路径（默认为 self.pwd）
        :param filter: 匿名函数过滤器（默认不启用）
        :return: AlistPath 对象生成器
        """
        if isinstance(dir_path, str):
            dir_path = dir_path.rstrip("/")
        elif dir_path is None:
            dir_path = self.__dir
        else:
            logger.warning(
                f"传入参数 dir_path({type(dir_path)}) 类型错误，使用当前目录 {self.__dir} 作为路径"
            )
            dir_path = self.__dir

        for path in await self.async_api_fs_list(dir_path):
            if path.is_dir:
                async for child_path in self.iter_path(
                    dir_path=path.path, filter=filter
                ):
                    yield child_path

            if filter(path):
                yield await self.async_api_fs_get(path)

    def chdir(self, dir_path: str) -> None:
        """
        安全切换目录

        :param dir: 目录
        """
        if dir_path == "/":
            self.__dir = "/"
        else:
            self.__dir = "/" + dir_path.strip("/") + "/"

    @property
    def pwd(self) -> str:
        """
        获取当前目录
        """
        return self.__dir

    async def __aenter__(self):
        self.__session = ClientSession(headers=self.__HEADERS)
        await self.async_api_auth_login()
        await self.async_api_me()
        return self

    async def __aexit__(self, *_):
        await self.__session.close()
