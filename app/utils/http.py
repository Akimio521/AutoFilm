from typing import Any
from pathlib import Path
from os import makedirs
from asyncio import TaskGroup, to_thread
from tempfile import TemporaryDirectory
from shutil import copy

from httpx import AsyncClient, Response, TimeoutException
from aiofile import async_open

from app.core import logger
from app.utils.url import URLUtils
from app.utils.retry import Retry


class HTTPClient:
    """
    HTTP 客户端类
    """

    __mini_stream_size: int = 128 * 1024 * 1024  # 最小流式下载文件大小，128MB

    def __init__(self):
        """
        初始化 HTTP 客户端
        """

        self.__new_async_client()

    def __new_async_client(self):
        self.__client = AsyncClient(http2=True, follow_redirects=True, timeout=10)

    async def close(self):
        """
        关闭 HTTP 客户端
        """
        if self.__client:
            await self.__client.aclose()

    @Retry.async_retry(TimeoutException, tries=3, delay=1, backoff=2)
    async def request(self, method: str, url: str, **kwargs) -> Response:
        """
        发起 HTTP 请求

        :param method: HTTP 方法，如 get, post, put 等
        :param url: 请求的 URL
        :param kwargs: 其他请求参数，如 headers, cookies 等
        :return: HTTP 响应对象
        """

        try:
            return await self.__client.request(method, url, **kwargs)
        except TimeoutException:
            await self.__client.aclose()
            self.__new_async_client()
            raise TimeoutException

    async def head(self, url: str, params: dict = {}, **kwargs) -> Response:
        """
        发送 HEAD 请求

        :param url: 请求的 URL
        :param kwargs: 其他请求参数，如 headers, cookies 等
        :return: HTTP 响应对象
        """
        return await self.request("head", url, params=params, **kwargs)

    async def get(self, url: str, params: dict = {}, **kwargs) -> Response:
        """
        发送 GET 请求

        :param url: 请求的 URL
        :param params: 请求的参数
        :param kwargs: 其他请求参数，如 headers, cookies 等
        :return: HTTP 响应对象
        """
        return await self.request("get", url, params=params, **kwargs)

    async def post(
        self, url: str, data: Any = None, json: dict = {}, **kwargs
    ) -> Response:
        """
        发送 POST 请求

        :param url: 请求的 URL
        :param data: 请求的数据
        :param json: 请求的 JSON 数据
        :param kwargs: 其他请求参数，如 headers, cookies 等
        :return: HTTP 响应对象
        """
        return await self.request("post", url, data=data, json=json, **kwargs)

    async def put(self, url: str, data: Any = None, **kwargs) -> Response:
        """
        发送 PUT 请求

        :param url: 请求的 URL
        :param data: 请求的数据
        :param kwargs: 其他请求参数，如 headers, cookies 等
        :return: HTTP 响应对象
        """
        return await self.request("put", url, data=data, **kwargs)

    async def download(
        self,
        url: str,
        file_path: Path,
        params: dict = {},
        chunk_num: int = 5,
        **kwargs,
    ) -> None:
        """
        下载文件

        :param url: 文件的 URL
        :param file_path: 文件保存路径
        :param params: 请求参数
        :param kwargs: 其他请求参数，如 headers, cookies 等
        """
        resp = await self.head(url, params=params, **kwargs)

        file_size = int(resp.headers.get("Content-Length", -1))

        with TemporaryDirectory(prefix="AutoFilm_") as temp_dir:  # 创建临时目录
            temp_file = Path(temp_dir) / file_path.name

            if file_size == -1:
                logger.debug(f"{file_path.name} 文件大小未知，直接下载")
                await self.__download_chunk(url, temp_file, 0, 0, **kwargs)
            else:
                async with TaskGroup() as tg:
                    logger.debug(
                        f"开始分片下载文件：{file_path.name}，分片数:{chunk_num}"
                    )
                    for start, end in self.caculate_divisional_range(
                        file_size, chunk_num=chunk_num
                    ):
                        tg.create_task(
                            self.__download_chunk(url, temp_file, start, end, **kwargs)
                        )
            copy(temp_file, file_path)

    async def __download_chunk(
        self,
        url: str,
        file_path: Path,
        start: int,
        end: int,
        iter_chunked_size: int = 64 * 1024,
        **kwargs,
    ):
        """
        下载文件的分片

        :param url: 文件的 URL
        :param file_path: 文件保存路径
        :param start: 分片的开始位置
        :param end: 分片的结束位置
        :param iter_chunked_size: 下载的块大小（下载完成后再写入硬盘），默认为 64KB
        :param kwargs: 其他请求参数，如 headers, cookies, proxies 等
        """

        await to_thread(makedirs, file_path.parent, exist_ok=True)

        if start != 0 and end != 0:
            headers = kwargs.get("headers", {})
            headers["Range"] = f"bytes={start}-{end}"
            kwargs["headers"] = headers

        resp = await self.get(url, **kwargs)
        async with async_open(file_path, "ab") as file:
            file.seek(start)
            async for chunk in resp.aiter_bytes(iter_chunked_size):
                await file.write(chunk)

    @staticmethod
    def caculate_divisional_range(
        file_size: int,
        chunk_num: int,
    ) -> list[tuple[int, int]]:
        """
        计算文件的分片范围

        :param file_size: 文件大小
        :param chunk_num: 分片数
        :return: 分片范围
        """
        if file_size < HTTPClient.__mini_stream_size or chunk_num <= 1:
            return [(0, file_size - 1)]

        step = file_size // chunk_num  # 计算每个分片的基本大小
        remainder = file_size % chunk_num  # 计算剩余的字节数

        chunks = []
        start = 0

        for i in range(chunk_num):
            # 如果有剩余字节，分配一个给当前分片
            end = start + step + (1 if i < remainder else 0) - 1
            chunks.append((start, end))
            start = end + 1

        return chunks


class RequestUtils:
    """
    HTTP 异步请求工具类
    """

    __clients: dict[str, HTTPClient] = {}

    @classmethod
    def close(cls):
        """
        关闭所有 HTTP 客户端
        """
        for client in cls.__clients.values():
            client.close()

    @classmethod
    def __get_client(cls, url: str) -> HTTPClient:
        """
        获取 HTTP 客户端

        :param url: 请求的 URL
        :return: HTTP 客户端
        """

        _, domain, port = URLUtils.get_resolve_url(url)
        key = f"{domain}:{port}"
        if key not in cls.__clients:
            cls.__clients[key] = HTTPClient()
        return cls.__clients[key]

    @classmethod
    async def request(cls, method: str, url: str, **kwargs) -> Response:
        """
        发起 HTTP 请求
        """
        client = cls.__get_client(url)
        return await client.request(method, url, **kwargs)

    @classmethod
    async def head(cls, url: str, params: dict = {}, **kwargs) -> Response:
        """
        发送 HEAD 请求

        :param url: 请求的 URL
        :param kwargs: 其他请求参数，如 headers, cookies 等
        :return: HTTP 响应对象
        """
        return await cls.request("head", url, params=params, **kwargs)

    @classmethod
    async def get(cls, url: str, params: dict = {}, **kwargs) -> Response:
        """
        发送 GET 请求

        :param url: 请求的 URL
        :param params: 请求的参数
        :param kwargs: 其他请求参数，如 headers, cookies 等
        :return: HTTP 响应对象
        """
        return await cls.request("get", url, params=params, **kwargs)

    @classmethod
    async def post(
        cls,
        url: str,
        data: Any = None,
        json: dict = {},
        **kwargs,
    ) -> Response:
        """
        发送 POST 请求

        :param url: 请求的 URL
        :param data: 请求的数据
        :param json: 请求的 JSON 数据
        :param kwargs: 其他请求参数，如 headers, cookies 等
        :return: HTTP 响应对象
        """
        return await cls.request("post", url, data=data, json=json, **kwargs)

    @classmethod
    async def put(cls, url: str, data: Any = None, **kwargs) -> Response:
        """
        发送 PUT 请求

        :param key: 客户端的键
        :param url: 请求的 URL
        :param data: 请求的数据
        :param kwargs: 其他请求参数，如 headers, cookies 等
        :return: HTTP 响应对象
        """
        return await cls.request("put", url, data=data, **kwargs)

    @classmethod
    async def download(
        cls,
        url: str,
        file_path: Path,
        params: dict = {},
        **kwargs,
    ) -> None:
        """
        下载文件

        :param url: 文件的 URL
        :param file_path: 文件保存路径
        :param params: 请求参数
        :param kwargs: 其他请求参数，如 headers, cookies 等
        """
        client = cls.__get_client(url)
        await client.download(url, file_path, params=params, **kwargs)
