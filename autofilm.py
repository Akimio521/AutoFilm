import logging
from pathlib import Path

import yaml

from modules import Alist2Strm


class AutoFilm:
    def __init__(
        self,
        config_path: str,
    ):
        """
        实例化 AutoFilm 对象

        :param config_path: 配置文件路径
        """

        self.base_dir: Path = Path(__file__).parent.absolute()

        config_path = Path(config_path)
        self.config_path: Path = (
            Path(config_path)
            if Path(config_path).is_absolute()
            else self.base_dir / config_path
        )

        self.config_data = {}

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

                self.library_mode = self.config_data["Settings"]["library_mode"]
                if self.library_mode:
                    self.subtitle: bool = False
                    self.img: bool = False
                    self.nfo: bool = False
                else:
                    self.subtitle: bool = self.config_data["Settings"]["subtitle"]
                    self.img: bool = self.config_data["Settings"]["img"]
                    self.nfo: bool = self.config_data["Settings"]["nfo"]

            except Exception as e:
                logging.error(f"配置文件{self.config_path}读取错误，错误信息：{str(e)}")

            logging.info(f"输出目录：{self.output_dir}".center(50, "="))

    def run_Alist2Strm(self) -> None:
        """
        运行 Alist2Strm 模块
        """

        try:
            alist_server_list: list[dict] = self.config_data["AlistServerList"]
        except Exception as e:
            logging.error(f"Alist服务器列表读取失败，错误信息：{str(e)}")
        else:
            logging.debug("Alist服务器加载成功")
            for alist_server in alist_server_list:
                alist2strm = Alist2Strm(
                    alist_server.get("url"),
                    alist_server.get("username"),
                    alist_server.get("password"),
                    alist_server.get("base_path"),
                    alist_server.get("token"),
                    self.output_dir,
                    self.subtitle,
                    self.img,
                    self.nfo,
                    self.library_mode,
                    alist_server.get("async_mode"),
                )
                alist2strm.run()
