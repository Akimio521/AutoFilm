#!/usr/bin/env python3
# encoding: utf-8

from asyncio import to_thread, Semaphore, TaskGroup
from contextlib import aclosing
from os import PathLike
from pathlib import Path
from typing import Final

from aiofile import async_open
from alist.component import AlistClient, AlistPath

from app.core import logger


VIDEO_EXTS: Final = frozenset(
    (".mp4", ".mkv", ".flv", ".avi", ".wmv", ".ts", ".rmvb", ".webm")
)
SUBTITLE_EXTS: Final = frozenset((".ass", ".srt", ".ssa", ".sub"))
IMAGE_EXTS: Final = frozenset((".png", ".jpg"))
NFO_EXTS: Final = frozenset((".nfo",))


class Alist2Strm:
    """
    将挂载到 Alist 服务器上的视频生成本地 Strm 文件
    """

    def __init__(
        self,
        url: str = "http://localhost:5244",
        username: str = "",
        password: str = "",
        token: str = "",
        source_dir: str = "/",
        target_dir: str | PathLike = "",
        flatten_mode: bool = False,
        subtitle: bool = False,
        image: bool = False,
        nfo: bool = False,
        overwrite: bool = False,
        max_workers: int = 5,
        **_,
    ) -> None:
        """
        实例化 Alist2Strm 对象

        :param url: Alist 服务器地址，默认为 "http://localhost:5244"
        :param username: Alist 用户名，默认为空
        :param password: Alist 密码，默认为空
        :param token: Alist 签名 token，默认为空
        :param source_dir: 需要同步的 Alist 的目录，默认为 "/"
        :param target_dir: strm 文件输出目录，默认为当前工作目录
        :param flatten_mode: 平铺模式，将所有 Strm 文件保存至同一级目录，默认为 False
        :param subtitle: 是否下载字幕文件，默认为 False
        :param image: 是否下载图片文件，默认为 False
        :param nfo: 是否下载 .nfo 文件，默认为 False
        :param overwrite: 本地路径存在同名文件时是否重新生成/下载该文件，默认为 False
        :param max_worders: 最大并发数
        """
        self.url = url
        self.username = username
        self.password = password
        self.token = token
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

        self.overwrite = overwrite
        self._async_semaphore = Semaphore(max_workers)

    async def run(self, /):
        """
        处理主体
        """
        self.client = AlistClient(
            origin=self.url,
            username=self.username,
            password=self.password,
        )
        async with TaskGroup() as tg:
            create_task = tg.create_task
            async for path in self.client.fs.iter(
                self.client.fs.abspath(self.source_dir),
                max_depth=-1,
                predicate=lambda path: path.is_file(),
                async_=True,
            ):
                create_task(self.__file_processer(path))

    async def __file_processer(self, /, path: AlistPath):
        """
        异步保存文件至本地

        :param path: AlistPath 对象
        """
        suffix = path.suffix.lower()
        if not (suffix in VIDEO_EXTS or suffix in self.download_exts):
            return

        if self.flatten_mode:
            local_path = self.target_dir / path.name
        else:
            local_path = self.target_dir / path.path.replace(
                self.source_dir, "", 1
            ).lstrip("/")

        async with self._async_semaphore:
            try:
                if local_path.exists() and not self.overwrite:
                    logger.debug(f"跳过文件：{local_path.name!r}")
                    return

                download_url = path.get_url(token=self.token)

                _parent = local_path.parent
                if not _parent.exists():
                    await to_thread(_parent.mkdir, parents=True, exist_ok=True)

                if suffix in VIDEO_EXTS:
                    local_path = local_path.with_suffix(".strm")
                    async with async_open(
                        local_path.as_posix(), mode="w", encoding="utf-8"
                    ) as file:
                        await file.write(download_url)
                    logger.debug(f"创建文件：{local_path!r}")
                else:
                    async with (
                        aclosing(
                            await self.client.request(
                                download_url, "GET", parse=None, async_=True
                            )
                        ) as resp,
                        async_open(local_path.as_posix(), mode="wb") as file,
                    ):
                        _write = file.write
                        async for chunk in resp.aiter_bytes(1 << 16):
                            await _write(chunk)
                    logger.debug(f"下载文件：{local_path!r}")
            except:
                logger.warning(f"下载失败: {local_path!r}")
                raise
