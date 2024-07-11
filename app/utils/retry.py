"""
重试装饰器
"""

import asyncio
import inspect
from typing import Any, TypeVar
from time import sleep
from logging import Logger

from app.core.log import LoggerManager

TRIES = 3
DELAY = 3
BACKOFF = 1


def retry(
    ExceptionToCheck: Any,
    tries: int = TRIES,
    delay: int = DELAY,
    backoff: int = BACKOFF,
    logger: LoggerManager | Logger | None = None,
    ret: Any = None,
):
    """
    同步步重试装饰器

    :param ExceptionToCheck: 需要捕获的异常
    :param tries: 重试次数
    :param delay: 延迟时间
    :param backoff: 延迟倍数
    :param logger: 日志对象（LoggerManager | logger）
    :param ret: 默认返回
    """

    def deco_retry(f):
        def f_retry(*args, **kwargs) -> Any:
            mtries, mdelay = tries, delay
            while mtries > 0:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    msg = f"出现错误，错误信息{e}，{mdelay}秒后重试 ..."
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            if logger:
                logger.warning("超出最大重试次数！返回默认值")
            return ret

        return f_retry

    return deco_retry


T = TypeVar("T")


def async_retry(
    ExceptionToCheck: Any,
    tries: int = TRIES,
    delay: int = DELAY,
    backoff: int = BACKOFF,
    logger: LoggerManager | Logger | None = None,
    ret: Any = None,
):
    """
    异步重试装饰器

    :param ExceptionToCheck: 需要捕获的异常
    :param tries: 重试次数
    :param delay: 延迟时间
    :param backoff: 延迟倍数
    :param logger: 日志对象（LoggerManager | logger）
    :param ret: 默认返回
    """

    def deco_retry(f):
        async def f_retry(*args, **kwargs) -> T:
            mtries, mdelay = tries, delay
            while mtries > 0:
                try:
                    return await f(*args, **kwargs)
                except ExceptionToCheck as e:
                    msg = f"出现错误，错误信息{e}，{mdelay}秒后重试 ..."
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    await asyncio.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            if logger:
                logger.warning("超出最大重试次数！返回默认值")
            return ret

        return f_retry

    return deco_retry
