#!/usr/bin/env python3
# encoding: utf-8


from pathlib import Path
from yaml import safe_load

from app.version import APP_VERSION


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
    # 开发者模式
    DEBUG: bool = False

    def __init__(self) -> None:
        """
        初始化 SettingManager 对象
        """
        self.__mkdir()
        self.__load_mode()

    def __mkdir(self) -> None:
        """
        创建目录
        """
        with self.CONFIG_DIR as dir_path:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)

        with self.LOG_DIR as dir_path:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)

    def __load_mode(self) -> None:
        """
        加载模式
        """
        with self.CONFIG.open(mode="r", encoding="utf-8") as file:
            is_dev = safe_load(file).get("Settings",{}).get("DEV")
        if is_dev:
            self.DEBUG = is_dev

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
    def LOG_DIR(self) -> Path:
        """
        日志文件路径
        """
        return self.BASE_DIR / "logs"

    @property
    def CONFIG(self) -> Path:
        """
        配置文件
        """
        return self.CONFIG_DIR / "config.yaml"
    
    @property
    def LOG(self) -> Path:
        """
        日志文件
        """
        if self.DEBUG:
            return self.LOG_DIR / "dev.log"
        else:
            return self.LOG_DIR / "AutoFilm.log"
            

    @property
    def AlistServerList(self) -> list[dict[str, any]]:
        with self.CONFIG.open(mode="r", encoding="utf-8") as file:
            alist_server_list = safe_load(file).get("Alist2StrmList", [])
        return alist_server_list
    
    @property
    def Ani2AlistList(self) -> list[dict[str, any]]:
        with self.CONFIG.open(mode="r", encoding="utf-8") as file:
            ani2alist_list = safe_load(file).get("Ani2AlistList", [])
        return ani2alist_list


settings = SettingManager()
