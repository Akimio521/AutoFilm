#!/usr/bin/env python3
# encoding: utf-8

import logging
from asyncio import run, to_thread, Semaphore, TaskGroup
from contextlib import aclosing
from os import fsdecode, makedirs, PathLike
from os.path import dirname, exists, join as joinpath, normpath, splitext
from typing import Final

from aiofile import async_open
from alist import AlistClient, AlistPath


VIDEO_EXTS: Final = frozenset((".mp4", ".mkv", ".flv", ".avi", ".wmv", ".ts", ".rmvb", ".webm"))
SUBTITLE_EXTS: Final = frozenset((".ass", ".srt", ".ssa", ".sub"))
IMAGE_EXTS: Final = frozenset((".png", ".jpg"))
NFO_EXTS: Final = frozenset((".nfo",))


class Alist2Strm:

    def __init__(
        self, 
        origin: str = "http://localhost:5244", 
        username: str = "", 
        password: str = "", 
        token: str = "", 
        base_dir: str = "/", 
        output_dir: bytes | str | PathLike = "", 
        library_mode: bool = False, 
        subtitle: bool = False, 
        image: bool = False, 
        nfo: bool = False, 
        overwrite: bool = False, 
        max_workers: int = 5, 
    ) -> None:
        """实例化 Alist2Strm 对象

        :param origin: Alist 服务器地址，默认为 "http://localhost:5244"
        :param username: Alist 用户名，默认为空
        :param password: Alist 密码，默认为空
        :param token: Alist 签名 token，默认为空
        :param base_dir: 需要同步的 Alist 的目录，默认为 "/"
        :param output_dir: strm 文件输出目录，默认为当前工作目录
        :param library_mode: 是否启用媒体库模式，所有文件下载到同一个目录，默认为 False
        :param subtitle: 是否下载字幕文件，默认为 False
        :param image: 是否下载图片文件，默认为 False
        :param nfo: 是否下载 .nfo 文件，默认为 False
        :param overwrite: 本地路径存在同名文件时是否重新生成/下载该文件，默认为 False
        :param max_worders: 最大并发数
        """
        client = self.client = AlistClient(
            origin=origin, 
            username=username, 
            password=password, 
        )
        self.token = token
        self.base_dir = client.fs.abspath(base_dir)
        self.output_dir = fsdecode(output_dir)
        self.library_mode = library_mode
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

        logging.debug("Alist2Strm配置".center(50, "=") + f"""\
Alist 地址：  {origin!r}
Alist 用户名：{username!r}
Alist 密码：  {password!r}
Alist token： {token!r}
Alist 目录：  {base_dir!r}
输出目录：    {output_dir!r}
媒体库模式：  {library_mode}
下载字幕：    {subtitle}
下载图片：    {image}
下载 NFO：    {nfo}
覆盖：        {overwrite}
最大并发数：  {max_workers}""")

    def run(self) -> None:
        """
        异步启动程序
        """
        run(self._processer_async())

    async def _processer_async(self, /):
        """
        程序处理主体（异步）
        """
        async with TaskGroup() as tg:
            create_task = tg.create_task
            async for path in self.client.fs.iter(
                self.base_dir, 
                max_depth=-1, 
                predicate=lambda path: path.is_file(), 
                async_=True, 
            ):
                create_task(self._file_processer(path))

    async def _file_processer(self, /, path: AlistPath):
        """
        异步保存文件至本地

        :param path: AlistPath 对象
        """
        suffix = path.suffix.lower()
        if not (suffix in VIDEO_EXTS or suffix in self.download_exts):
            return

        if self.library_mode:
            local_path = joinpath(self.output_dir, path.name)
        else:
            local_path = joinpath(self.output_dir, normpath(path.relative_to(self.base_dir)))

        async with self._async_semaphore:
            try:
                if exists(local_path) and not self.overwrite:
                    logging.debug(f"跳过文件：{local_path!r}")
                    return

                url = path.get_url(token=self.token)
                if dir_ := dirname(local_path):
                    await to_thread(makedirs, dir_, exist_ok=True)

                if suffix in VIDEO_EXTS:
                    local_path = splitext(local_path)[0] + ".strm"
                    async with async_open(local_path, mode="w", encoding="utf-8") as file:
                        await file.write(url)
                    logging.debug(f"创建文件：{local_path!r}")
                else:
                    async with (
                        aclosing(await self.client.request(url, "GET", parse=None, async_=True)) as resp, 
                        async_open(local_path, mode="wb") as file, 
                    ):
                        write = file.write
                        async for chunk in resp.aiter_bytes(1 << 16):
                            await write(chunk)
                    logging.debug(f"下载文件：{local_path!r}")
            except:
                logging.exception(f"下载失败: {local_path!r}")
                raise

