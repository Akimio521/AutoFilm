#!/usr/bin/env python3
# encoding: utf-8

import logging
from logging.handlers import RotatingFileHandler

from app.core.config import settings


class LoggerManager:
    """
    日志管理器
    """

    def __init__(self) -> None:
        """
        初始化 LoggerManager 对象
        """
        self.__logger = logging.getLogger(__name__)
        self.__logger.setLevel(logging.DEBUG)
        __formatter = logging.Formatter(fmt="[%(levelname)s]%(asctime)s - %(message)s")

        if settings.DEBUG:
            ch_level = logging.DEBUG
            fh_mode = "w"
        else:
            ch_level = logging.INFO
            fh_mode = "a"

        __console_handler = logging.StreamHandler()
        __console_handler.setLevel(ch_level)
        self.__logger.addHandler(__console_handler)
        __console_handler.setFormatter(__formatter)

        __file_handler = RotatingFileHandler(
            filename=settings.LOG,
            mode=fh_mode,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        __file_handler.setLevel(logging.INFO)
        self.__logger.addHandler(__file_handler)
        __file_handler.setFormatter(__formatter)

    def __log(self, method: str, msg: str, *args, **kwargs) -> None:
        """
        获取模块的logger
        :param method: 日志方法
        :param msg: 日志信息
        """
        if hasattr(self.__logger, method):
            getattr(self.__logger, method)(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        """
        重载info方法
        """
        self.__log("info", msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs) -> None:
        """
        重载debug方法
        """
        self.__log("debug", msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """
        重载warning方法
        """
        self.__log("warning", msg, *args, **kwargs)

    def warn(self, msg: str, *args, **kwargs) -> None:
        """
        重载warn方法
        """
        self.__log("warning", msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """
        重载error方法
        """
        self.__log("error", msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        """
        重载critical方法
        """
        self.__log("critical", msg, *args, **kwargs)


# 初始化公共日志
logger = LoggerManager()
