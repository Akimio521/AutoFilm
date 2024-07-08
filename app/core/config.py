#!/usr/bin/env python3
# encoding: utf-8


import logging
from pathlib import Path
from yaml import safe_load

from version import APP_VERSION


class SettingManager:
    """
    系统配置
    """

    # APP 名称
    APP_NAME: str = "Autofilm"
    # APP 版本
    APP_VERSION: int = APP_VERSION
    # 时区
    TZ: str = "Asia/Shanghai"

    def __init__(self) -> None:
        """
        初始化 SettingManager 对象
        """
        self.__mkdir()
        self.__init_logging()

    def __mkdir(self) -> None:
        """
        创建目录
        """
        with self.CONFIG_DIR as dir_path:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)

    def __init_logging(self):
        """
        初始化 loggging 日志模块内容
        """
        with self.CONFIG.open(mode="r", encoding="utf-8") as file:
            log_level = safe_load(file).get("Settings").get("log_level") or "INFO"

        formatter = "[%(levelname)s]%(asctime)s - %(message)s"
        logging.basicConfig(format=formatter, level=getattr(logging, log_level))

    @property
    def BASE_DIR(self) -> Path:
        """
        后端程序基础路径 AutoFilm/app
        """
        return Path(__file__).parents[2]

    @property
    def CONFIG_DIR(self) -> Path:
        """
        配置文件路径
        """
        return self.BASE_DIR / "config"

    @property
    def CONFIG(self) -> Path:
        """
        配置文件
        """
        return self.CONFIG_DIR / "config.yaml"

    @property
    def AlistServerList(self) -> list[dict[str, any]]:
        with self.CONFIG.open(mode="r", encoding="utf-8") as file:
            alist_server_list = safe_load(file).get("Alist2StrmList", [])
        return alist_server_list


settings = SettingManager()
