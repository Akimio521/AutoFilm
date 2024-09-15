#!/usr/bin/env python3
# encoding: utf-8

from asyncio import to_thread, Semaphore, TaskGroup
from os import PathLike
from pathlib import Path

from aiofile import async_open
from aiohttp import ClientSession

from app.core import logger
from app.utils import retry
from app.extensions import VIDEO_EXTS, SUBTITLE_EXTS, IMAGE_EXTS, NFO_EXTS
from app.api import AlistClient, AlistPath


class Alist2Strm:

    def __init__(
        self,
        url: str = "http://localhost:5244",
        username: str = "",
        password: str = "",
        source_dir: str = "/",
        target_dir: str | PathLike = "",
        flatten_mode: bool = False,
        subtitle: bool = False,
        image: bool = False,
        nfo: bool = False,
        mode: str = "AlistURL",
        overwrite: bool = False,
        other_ext: str = "",
        max_workers: int = 50,
        max_downloaders: int = 5,
        **_,
    ) -> None:
        """
        实例化 Alist2Strm 对象

        :param url: Alist 服务器地址，默认为 "http://localhost:5244"
        :param username: Alist 用户名，默认为空
        :param password: Alist 密码，默认为空
        :param source_dir: 需要同步的 Alist 的目录，默认为 "/"
        :param target_dir: strm 文件输出目录，默认为当前工作目录
        :param flatten_mode: 平铺模式，将所有 Strm 文件保存至同一级目录，默认为 False
        :param subtitle: 是否下载字幕文件，默认为 False
        :param image: 是否下载图片文件，默认为 False
        :param nfo: 是否下载 .nfo 文件，默认为 False
        :param mode: Strm模式(AlistURL/RawURL/AlistPath)
        :param overwrite: 本地路径存在同名文件时是否重新生成/下载该文件，默认为 False
        :param other_ext: 自定义下载后缀，使用西文半角逗号进行分割，默认为空
        :param max_worders: 最大并发数
        :param max_downloaders: 最大同时下载
        """
        self.url = url
        self.username = username
        self.password = password
        self.mode = mode

        self.source_dir = source_dir
        self.target_dir = Path(target_dir)

        self.flatten_mode = flatten_mode
        if flatten_mode:
            subtitle = image = nfo = False

        download_exts: set[str] = set()
        if subtitle:
            download_exts |= SUBTITLE_EXTS
        if image:
            download_exts |= IMAGE_EXTS
        if nfo:
            download_exts |= NFO_EXTS
        if other_ext:
            download_exts |= frozenset(other_ext.lower().split(","))

        self.download_exts = download_exts
        self.process_file_exts = VIDEO_EXTS | download_exts

        self.overwrite = overwrite
        self.__max_workers = Semaphore(max_workers)
        self.__max_downloaders = Semaphore(max_downloaders)

    async def run(self) -> None:
        """
        处理主体
        """

        def filter(path: AlistPath) -> bool:
            if path.is_dir:
                return False

            if not path.suffix.lower() in self.process_file_exts:
                logger.debug(f"文件{path.name}不在处理列表中")
                return False

            if self.overwrite:
                return True

            local_path = self.__get_local_path(path)

            if local_path.exists():
                logger.debug(f"文件{local_path.name}已存在，跳过处理{path.path}")
                return False

            return True

        if not self.mode in ["AlistURL", "RawURL", "AlistPath"]:
            logger.warning(
                f"Alist2Strm的模式{self.mode}不存在，已设置为默认模式AlistURL"
            )
            self.mode = "AlistURL"

        async with self.__max_workers:
            async with ClientSession() as session:
                self.session = session
                async with TaskGroup() as tg:
                    _create_task = tg.create_task
                    async with AlistClient(
                        self.url, self.username, self.password
                    ) as client:
                        async for path in client.iter_path(
                            dir_path=self.source_dir, filter=filter
                        ):
                            _create_task(self.__file_processer(path))
            logger.info("Alist2Strm处理完成")

    @retry(Exception, tries=3, delay=3, backoff=2, logger=logger)
    async def __file_processer(self, path: AlistPath) -> None:
        """
        异步保存文件至本地

        :param path: AlistPath 对象
        """
        local_path = self.__get_local_path(path)

        if self.mode == "AlistURL":
            content = path.download_url
        elif self.mode == "RawURL":
            content = path.raw_url
        elif self.mode == "AlistPath":
            content = path.path
        else:
            raise ValueError(f"AlistStrm未知的模式{self.mode}")

        try:
            _parent = local_path.parent
            if not _parent.exists():
                await to_thread(_parent.mkdir, parents=True, exist_ok=True)

            logger.debug(f"开始处理{local_path}")
            if local_path.suffix == ".strm":
                async with async_open(local_path, mode="w", encoding="utf-8") as file:
                    await file.write(content)
                logger.info(f"{local_path.name}创建成功")
            else:
                async with self.__max_downloaders:
                    async with async_open(local_path, mode="wb") as file:
                        _write = file.write
                        async with self.session.get(path.download_url) as resp:
                            async for chunk in resp.content.iter_chunked(1024):
                                await _write(chunk)
                    logger.info(f"{local_path.name}下载成功")
        except Exception as e:
            raise RuntimeError(f"{local_path}处理失败，详细信息：{e}")

    def __get_local_path(self, path: AlistPath) -> Path:
        """
        根据给定的 AlistPath 对象和当前的配置，计算出本地文件路径。
        """
        if self.flatten_mode:
            local_path = self.target_dir / path.name
        else:
            local_path = self.target_dir / path.path.replace(
                self.source_dir, "", 1
            ).lstrip("/")

        if path.suffix.lower() in VIDEO_EXTS:
            local_path = local_path.with_suffix(".strm")

        return local_path
