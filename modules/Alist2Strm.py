import logging
import hmac
import hashlib
import base64
import asyncio
from aiohttp import ClientSession
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
    ) -> None:
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
            f"是否为库模式：{self.library_mode}"
        )

    def run(self) -> None:
        asyncio.run(self._processer())

    async def _processer(self):
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

        async with ClientSession() as session:
            tasks = [
                asyncio.create_task(self._file_processer(alist_path_cls, session))
                for alist_path_cls in fs.rglob("*.*")
            ]
            await asyncio.gather(*tasks)

    async def _file_processer(
        self, alist_path_cls: AlistPath, session: ClientSession
    ) -> None:
        if not alist_path_cls.name.lower().endswith(ALL_EXT):
            return

        file_output_path: Path = (
            self.output_dir / alist_path_cls.name
            if self.library_mode
            else self.output_dir
            / str(alist_path_cls).replace(self.alist_server_base_dir, "")
        )

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
            async with session.get(file_download_url) as resp:
                if resp.status == 200:
                    with file_output_path.open(mode="wb") as f:
                        f.write(await resp.read())
                    logging.debug(
                        f"{file_output_path.name}下载成功，文件本地目录：{file_output_path.parent}"
                    )

    def _sign(self, secret_key: Optional[str], data: str) -> str:
        if secret_key == "" or secret_key == None:
            return ""

        h = hmac.new(secret_key.encode(), digestmod=hashlib.sha256)
        expire_time_stamp = str(0)
        h.update((data + ":" + expire_time_stamp).encode())
        return f"?sign={base64.urlsafe_b64encode(h.digest()).decode()}:0"
