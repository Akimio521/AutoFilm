"""
重试装饰器
"""

from asyncio import sleep as async_sleep
from inspect import iscoroutinefunction
from typing import Any, TypeVar, Callable
from time import sleep
from logging import Logger

from app.core.log import LoggerManager

TRIES = 3
DELAY = 3
BACKOFF = 1

T = TypeVar("T")


def retry(
    ExceptionToCheck: Any,
    tries: int = TRIES,
    delay: int = DELAY,
    backoff: int = BACKOFF,
    logger: LoggerManager | Logger | None = None,
    ret: T = None,
):
    """
    同步/异步重试装饰器

    :param ExceptionToCheck: 需要捕获的异常
    :param tries: 重试次数
    :param delay: 延迟时间
    :param backoff: 延迟倍数
    :param logger: 日志对象（LoggerManager | logger）
    :param ret: 默认返回
    """

    def deco_retry(f: Callable[..., T]) -> Callable[..., T]:
        async def async_wrapper(*args, **kwargs) -> T:
            return await f(*args, **kwargs)

        def sync_wrapper(*args, **kwargs) -> T:
            return f(*args, **kwargs)

        async def retry_logic(wrapper, *args, **kwargs) -> T:
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return await wrapper(*args, **kwargs)
                except ExceptionToCheck as _e:
                    msg = f"{_e}，{mdelay}秒后重试 ..."
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)

                    if iscoroutinefunction(f):
                        await async_sleep(mdelay)
                    else:
                        sleep(mdelay)

                    mtries -= 1
                    mdelay *= backoff
                    e = _e

            if logger:
                logger.warning(f"{_e}超出最大重试次数！返回默认值")
            return ret

        if iscoroutinefunction(f):

            async def f_retry(*args, **kwargs) -> T:
                return await retry_logic(async_wrapper, *args, **kwargs)

        else:

            async def f_retry(*args, **kwargs) -> T:
                return await retry_logic(sync_wrapper, *args, **kwargs)

        return f_retry

    return deco_retry
