import logging
import hmac
import hashlib
import base64
import asyncio
from urllib.parse import unquote
from requests import Session
from aiohttp import ClientSession as AsyncSession
from pathlib import Path
from typing import Optional

from alist import AlistFileSystem, AlistPath

VIDEO_EXT = ("mp4", "mkv", "flv", "avi", "wmv", "ts", "rmvb", "webm")
SUBTITLE_EXT = ("ass", "srt", "ssa", "sub")
IMG_EXT = ("png", "jpg")
ALL_EXT = (*VIDEO_EXT, *SUBTITLE_EXT, *IMG_EXT, "nfo")


class Alist2Strm:
    def __init__(
        self,
        alist_server_url: str,
        alist_server_username: str,
        alist_server_password: str,
        alist_server_base_dir: Optional[str],
        token: Optional[str],
        output_dir: Path,
        subtitle: bool = False,
        img: bool = False,
        nfo: bool = False,
        library_mode: bool = True,
        async_mode: bool = False,
        overwrite: bool = False,
    ) -> None:
        """
        实例化 Alist2Strm 对象

        :param alist_server_url: Alist 服务器地址
        :param alist_server_username: Alist 用户名
        :param alist_server_username: Alist 密码
        :param alist_server_base_dir: 底层目录，默认为 "/"
        :param token: Alist 签名 Token
        :param output_dir: Strm 文件输出目录
        :param subtitle: 是否下载字幕文件，默认 "False"
        :param img: 是否下载图片文件，默认 "False"
        :param nfo: 是否下载NFO文件，默认 "False"
        :param library_mode: 是否启用媒体库模式，默认 "True"
        :param async_mode: 是否启用异步下载文件，默认 "False"
        :param overwrite: 本地路径存在同名文件时是否重新生成/下载该文件，默认 "False"
        """

        self.alist_server_url = alist_server_url.rstrip("/")
        self.alist_server_username = alist_server_username
        self.alist_server_password = alist_server_password
        if alist_server_base_dir == None or alist_server_base_dir == "":
            self.alist_server_base_dir = "/"
        else:
            self.alist_server_base_dir = "/" + alist_server_base_dir.strip("/") + "/"
        self.token = token if token else None
        self.output_dir = output_dir
        self.subtitle = subtitle
        self.img = img
        self.nfo = nfo
        self.library_mode = library_mode
        self.async_mode = async_mode
        self.overwrite = overwrite

        logging.debug(
            f"Alist2Strm配置".center(50, "=") + "\n"
            f"Alist地址：{self.alist_server_url}\n"
            f"Alist用户名：{self.alist_server_username}\n"
            f"Alist密码：{self.alist_server_password}\n"
            f"Alist基本路径：{self.alist_server_base_dir}\n"
            f"Alist签名Token：{self.token}\n"
            f"输出目录：{self.output_dir}\n"
            f"是否下载字幕：{self.subtitle}\n"
            f"是否下载图片：{self.img}\n"
            f"是否下载NFO：{self.nfo}\n"
            f"是否为库模式：{self.library_mode}\n"
            f"是否为启用异步下载：{self.async_mode}"
        )

    def run(self) -> None:
        """
        异步启动程序
        """

        asyncio.run(self._processer())

    async def _processer(self) -> None:
        """
        程序处理主体
        """
        try:
            fs = AlistFileSystem.login(
                self.alist_server_url,
                self.alist_server_username,
                self.alist_server_password,
            )
        except Exception as e:
            logging.critical(
                "登录失败".center(50, "=") + "\n"
                f"错误信息：{str(e)}\n"
                f"请检查Alist地址：{self.alist_server_url}\n"
                f"用户名：{self.alist_server_username}\n"
                f"密码：{self.alist_server_password}是否正确"
            )
            return

        try:
            fs.chdir(self.alist_server_base_dir)
        except Exception as e:
            logging.critical(
                "切换目录失败".center(50, "=") + "\n"
                f"错误信息：{str(e)}\n"
                f"请检查Alist服务器中是否存在该目录：{self.alist_server_base_dir}"
            )
            return

        if self.async_mode:
            self.session = AsyncSession()
        else:
            self.session = Session()

        async with asyncio.TaskGroup() as tg:
            for alist_path_cls in fs.rglob("*.*"):
                tg.create_task(self._file_processer(alist_path_cls))

        if self.session:
            if self.async_mode:
                await self.session.close()
            else:
                self.session.close()

    async def _file_processer(self, alist_path_cls: AlistPath) -> None:
        """
        保存文件至本地

        :param alist_path_cls: AlistPath 对象
        """

        if not alist_path_cls.name.lower().endswith(ALL_EXT):
            return

        file_output_path: Path = (
            self.output_dir / alist_path_cls.name
            if self.library_mode
            else self.output_dir
            / str(alist_path_cls).replace(self.alist_server_base_dir, "")
        )

        if self.overwrite == False and file_output_path.exists():
            logging.debug(
                f"{file_output_path.name}已存在，跳过下载，文件本地目录：{file_output_path.parent}"
            )
            return

        file_alist_abs_path: str = alist_path_cls.url[
            alist_path_cls.url.index("/d/") + 2 :
        ]

        file_download_url: str = alist_path_cls.url + self._sign(
            secret_key=self.token, data=file_alist_abs_path
        )

        logging.debug(
            f"正在处理:{alist_path_cls.name}\n"
            f"本地文件目录：{file_output_path}\n"
            f"文件远程路径：{file_alist_abs_path}\n"
            f"下载URL：{file_download_url}"
        )

        if alist_path_cls.name.lower().endswith(VIDEO_EXT):
            file_output_path.parent.mkdir(parents=True, exist_ok=True)
            file_output_path = file_output_path.with_suffix(".strm")
            with file_output_path.open(mode="w", encoding="utf-8") as f:
                f.write(file_download_url)
                logging.debug(
                    f"{file_output_path.name}创建成功，文件本地目录：{file_output_path.parent}"
                )
            return

        if alist_path_cls.name.lower().endswith(IMG_EXT) and not self.img:
            return
        elif alist_path_cls.name.lower().endswith(SUBTITLE_EXT) and not self.subtitle:
            return
        elif alist_path_cls.name.lower().endswith("nfo") and not self.nfo:
            return
        else:
            file_output_path.parent.mkdir(parents=True, exist_ok=True)

            if self.async_mode:
                resp = await self.session.get(file_download_url)
            else:
                resp = self.session.get(file_download_url)

            with file_output_path.open(mode="wb") as f:
                if self.async_mode:
                    f.write(await resp.read())
                else:
                    f.write(resp.content)
            logging.debug(
                f"{file_output_path.name}下载成功，文件本地目录：{file_output_path.parent}"
            )

    def _sign(self, secret_key: Optional[str], data: str) -> str:
        """
        Alist 签名 Token 处理

        :param secret_key: Alist 签名 Token
        :param data: 待签名数据 （Alist 文件绝对路径）
        """

        if secret_key == "" or secret_key == None:
            return ""

        data = unquote(data)
        h = hmac.new(secret_key.encode(), digestmod=hashlib.sha256)
        expire_time_stamp = str(0)
        h.update((data + ":" + expire_time_stamp).encode())
        return f"?sign={base64.urlsafe_b64encode(h.digest()).decode()}:0"
