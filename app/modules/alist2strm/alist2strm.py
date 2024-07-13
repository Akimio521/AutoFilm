#!/usr/bin/env python3
# encoding: utf-8

from asyncio import to_thread, Semaphore, TaskGroup
from os import PathLike
from pathlib import Path
from typing import Final

from aiofile import async_open
from aiohttp import ClientSession

from app.core import logger
from app.utils import retry
from app.modules.alist import AlistClient, AlistPath


VIDEO_EXTS: Final = frozenset(("mp4", "mkv", "flv", "avi", "wmv", "ts", "rmvb", "webm"))
SUBTITLE_EXTS: Final = frozenset(("ass", "srt", "ssa", "sub"))
IMAGE_EXTS: Final = frozenset(("png", "jpg"))
NFO_EXTS: Final = frozenset(("nfo",))


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
        raw_url: bool = False,
        overwrite: bool = False,
        other_ext: str | None = None,
        max_workers: int = 5,
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
        :param raw_url: 是否使用原始地址，默认为 False
        :param overwrite: 本地路径存在同名文件时是否重新生成/下载该文件，默认为 False
        :param other_ext: 自定义下载后缀，使用西文半角逗号进行分割，默认为空
        :param max_worders: 最大并发数
        """
        self.url = url
        self.username = username
        self.password = password
        self.raw_url = raw_url

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
        self.download_exts = download_exts

        if other_ext:
            download_exts |= frozenset(other_ext.split(","))

        self.overwrite = overwrite
        self._async_semaphore = Semaphore(max_workers)

    async def run(self, /):
        """
        处理主体
        """
        async with ClientSession() as session:
            self.session = session
            async with TaskGroup() as tg:
                _create_task = tg.create_task
                async with AlistClient(
                    self.url, self.username, self.password
                ) as client:
                    async for path in client.iter_path(
                        dir_path=self.source_dir,
                        filter=lambda path: path.suffix
                        in VIDEO_EXTS | self.download_exts,
                    ):
                        _create_task(self.__file_processer(path))

    @retry(Exception, tries=3, delay=3, backoff=2, logger=logger)
    async def __file_processer(self, /, path: AlistPath):
        """
        异步保存文件至本地

        :param path: AlistPath 对象
        """
        if self.flatten_mode:
            local_path = self.target_dir / path.name
        else:
            local_path = self.target_dir / path.path.replace(
                self.source_dir, "", 1
            ).lstrip("/")

        url = path.raw_url if self.raw_url else path.download_url

        async with self._async_semaphore:
            try:
                if local_path.exists() and not self.overwrite:
                    logger.debug(f"跳过文件：{local_path.name}")
                    return

                _parent = local_path.parent
                if not _parent.exists():
                    await to_thread(_parent.mkdir, parents=True, exist_ok=True)

                if path.suffix in VIDEO_EXTS:
                    local_path = local_path.with_suffix(".strm")
                    async with async_open(
                        local_path, mode="w", encoding="utf-8"
                    ) as file:
                        await file.write(url)
                    logger.debug(f"创建文件：{local_path}")
                else:
                    async with async_open(local_path, mode="wb") as file:
                        _write = file.write
                        async with self.session.get(url) as resp:
                            async for chunk in resp.content.iter_chunked(1024):
                                await _write(chunk)
                    logger.debug(f"下载文件：{local_path.name}")
            except:
                raise RuntimeError(f"下载失败: {local_path.name}")
