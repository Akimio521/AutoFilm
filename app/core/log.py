import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from pathlib import Path

import click

from app.core.config import settings

FMT = "%(prefix)s %(message)s"

# 日志级别颜色映射
LEVEL_WITH_COLOR = {
    logging.DEBUG: lambda level_name: click.style(str(level_name), fg="blue"),
    logging.INFO: lambda level_name: click.style(str(level_name), fg="green"),
    logging.WARNING: lambda level_name: click.style(str(level_name), fg="yellow"),
    logging.ERROR: lambda level_name: click.style(str(level_name), fg="red"),
    logging.CRITICAL: lambda level_name: click.style(
        str(level_name), fg="red", bold=True
    ),
}


class CustomFormatter(logging.Formatter):
    """
    自定义日志输出格式

    对 logging.LogRecord 增加一个属性 prefix，level + time
    """

    def __init__(self, file_formatter: bool = False, fmt: str = None) -> None:
        """
        :param file_formatter: 是否为文件格式化器
        """

        self.__file_formatter = file_formatter
        super().__init__(fmt=fmt)

    def format(self, record: logging.LogRecord) -> str:

        if self.__file_formatter:  # 文件中不需要控制字
            record.prefix = f"【{record.levelname}】"
        else:  # 控制台需要控制字
            record.prefix = LEVEL_WITH_COLOR[record.levelno](f"【{record.levelname}】")

        # 最长的 CRITICAL 为 8 个字符，保留 1 个空格作为分隔符
        separator = " " * (9 - len(record.levelname))
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record.prefix += f"{separator}{dt} |"
        return super().format(record)


class TRFileHandler(TimedRotatingFileHandler):
    """
    日期轮换文件处理器
    """

    def __init__(self, log_dir: Path, encoding: str = "utf-8") -> None:
        self.log_dir = log_dir
        super().__init__(
            self.__get_log_filname(),
            when="midnight",
            interval=1,
            backupCount=0,
            encoding=encoding,
        )

    def doRollover(self) -> None:
        """
        在轮换日志文件时，更新日志文件路径
        """

        self.baseFilename = self.__get_log_filname()
        super().doRollover()

    def __get_log_filname(self) -> str:
        """
        根据当前日期生成日志文件路径
        """

        current_date = datetime.now().strftime("%Y-%m-%d")
        return (self.log_dir / f"{current_date}.log").as_posix()


class LoggerManager:
    """
    日志管理器
    """

    def __init__(self) -> None:
        """
        初始化 LoggerManager 对象
        """

        self.__logger = logging.getLogger(settings.APP_NAME)
        self.__logger.setLevel(logging.DEBUG)

        console_formatter = CustomFormatter(
            file_formatter=False,
            fmt=FMT,
        )
        file_formatter = CustomFormatter(
            file_formatter=True,
            fmt=FMT,
        )

        level = logging.DEBUG if settings.DEBUG else logging.INFO

        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        self.__logger.addHandler(console_handler)

        file_handler = TRFileHandler(log_dir=settings.LOG_DIR, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        self.__logger.addHandler(file_handler)

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
