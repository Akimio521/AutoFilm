#! /usr/bin/env python3
# -*- coding:utf-8 -*-

import logging
import hmac
import hashlib
import base64
import asyncio
from aiohttp import ClientSession
from pathlib import Path

import yaml
from alist import AlistFileSystem, AlistPath


class AutoFilm:
    def __init__(
        self,
        config_path: str,
    ):

        self.base_dir: Path = Path(__file__).parent.absolute()
        config_path = Path(config_path)
        self.config_path: Path = (
            Path(config_path)
            if Path(config_path).is_absolute()
            else self.base_dir / config_path
        )

        self.config_data = {}

        self.video_ext = ("mp4", "mkv", "flv", "avi", "wmv", "ts", "rmvb", "webm")
        self.subtitle_ext = ("ass", "srt", "ssa", "sub")
        self.img_ext = ("png", "jpg")

        try:
            with self.config_path.open(mode="r", encoding="utf-8") as f:
                self.config_data = yaml.safe_load(f)
        except Exception as e:
            logging.critical(
                f"配置文件{config_path}加载失败，程序即将停止，错误信息：{str(e)}"
            )
        else:
            try:
                read_output_dir = Path(self.config_data["Settings"]["output_dir"])
                self.output_dir = (
                    read_output_dir
                    if read_output_dir.is_absolute()
                    else self.base_dir / read_output_dir
                )

                self.subtitle: bool = self.config_data["Settings"]["subtitle"]
                self.img: bool = self.config_data["Settings"]["img"]
                self.nfo: bool = self.config_data["Settings"]["nfo"]
                self.library_mode = self.config_data["Settings"]["library_mode"]
            except Exception as e:
                logging.error(f"配置文件{self.config_path}读取错误，错误信息：{str(e)}")

            logging.info(f"输出目录：{self.output_dir}".center(50, "="))

    def run(self) -> None:
        try:
            alist_server_list = self.config_data["AlistServerList"]
        except Exception as e:
            logging.error(f"Alist服务器列表读取失败，错误信息：{str(e)}")
        else:
            logging.debug("Alist服务器加载成功")
            for alist_server in alist_server_list:
                try:
                    alist_server_url: str = alist_server["url"]
                    alist_server_username: str = alist_server["username"]
                    alist_server_password: str = alist_server["password"]
                    alist_server_base_path: str = alist_server["base_path"]
                    alist_server_token: str = str(alist_server.get("token", ""))
                except Exception as e:
                    logging.error(
                        f"Alist服务器{alist_server}配置错误，请检查配置文件：{self.config_path}，错误信息：{str(e)}"
                    )
                else:
                    asyncio.run(
                        self._processer(
                            alist_server_url,
                            alist_server_username,
                            alist_server_password,
                            alist_server_base_path,
                            alist_server_token,
                        )
                    )

    async def _processer(
        self,
        alist_server_url: str,
        alist_server_username: str,
        alist_server_password: str,
        alist_server_base_path: str,
        alist_server_token: str,
    ) -> None:
        fs = AlistFileSystem.login(
            alist_server_url, alist_server_username, alist_server_password
        )
        fs.chdir(alist_server_base_path)
        async with ClientSession() as session:
            tasks = [
                asyncio.create_task(
                    self._file_process(
                        path, session, alist_server_base_path, alist_server_token
                    )
                )
                for path in fs.rglob("*.*")
            ]
            await asyncio.gather(*tasks)

    async def _file_process(
        self,
        alist_path_cls: AlistPath,
        session: ClientSession,
        base_path: Path,
        token: str,
    ) -> None:
        logging.debug(f"正在处理:{alist_path_cls.name}")
        file_output_dir: Path = (
            self.output_dir / alist_path_cls.name
            if self.library_mode
            else self.output_dir / str(alist_path_cls).replace(base_path, "")
        )

        file_output_dir.parent.mkdir(parents=True, exist_ok=True)

        file_alist_abs_path: str = alist_path_cls.url[
            alist_path_cls.url.index("/d/") + 2 :
        ]

        file_download_url: str = alist_path_cls.url + self._sign(
            secret_key=token, data=file_alist_abs_path
        )

        if alist_path_cls.name.lower().endswith(self.video_ext):
            file_output_dir = file_output_dir.with_suffix(".strm")
            with file_output_dir.open(mode="w", encoding="utf-8") as f:
                f.write(file_download_url)

        elif alist_path_cls.name.lower().endswith(self.img_ext) and self.img:
            async with session.get(file_download_url) as resp:
                if resp.status == 200:
                    with file_output_dir.open(mode="wb") as f:
                        f.write(await resp.read())
        elif alist_path_cls.name.lower().endswith(self.subtitle_ext) and self.subtitle:
            async with session.get(file_download_url) as resp:
                if resp.status == 200:
                    with file_output_dir.open(mode="wb") as f:
                        f.write(await resp.read())
        elif alist_path_cls.name.lower().endswith("nfo") and self.nfo:
            async with session.get(file_download_url) as resp:
                if resp.status == 200:
                    with file_output_dir.open(mode="wb") as f:
                        f.write(await resp.read())

    def _sign(self, secret_key: str, data: str) -> str:
        if secret_key == "":
            return ""
        h = hmac.new(secret_key.encode(), digestmod=hashlib.sha256)
        expire_time_stamp = str(0)
        h.update((data + ":" + expire_time_stamp).encode())
        return f"?sign={base64.urlsafe_b64encode(h.digest()).decode()}:0"
