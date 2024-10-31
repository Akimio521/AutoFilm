from asyncio import sleep as async_sleep
from typing import Any, TypeVar, Callable
from time import sleep
from logging import Logger

from app.core.log import LoggerManager
from app.utils.singleton import Singleton

TRIES = 3
DELAY = 3
BACKOFF = 1
T = TypeVar("T")


class Retry(metaclass=Singleton):
    """
    重试装饰器
    """

    @staticmethod
    def sync_retry(
        ExceptionToCheck: Any,
        tries: int = TRIES,
        delay: int = DELAY,
        backoff: int = BACKOFF,
        logger: LoggerManager | Logger | None = None,
        ret: T = None,
    ) -> Callable[..., T]:
        """
        同步重试装饰器

        :param ExceptionToCheck: 需要捕获的异常
        :param tries: 重试次数
        :param delay: 延迟时间
        :param backoff: 延迟倍数
        :param logger: 日志对象（Logger）
        :param ret: 默认返回
        """

        def deco_retry(f: Callable[..., T]) -> Callable[..., T]:
            def f_retry(*args, **kwargs) -> T:
                mtries, mdelay = tries, delay
                while mtries > 1:
                    try:
                        return f(*args, **kwargs)
                    except ExceptionToCheck as _e:
                        msg = f"{_e}，{mdelay}秒后重试 ..."
                        if logger:
                            logger.warning(msg)
                        else:
                            print(msg)
                        sleep(mdelay)
                        mtries -= 1
                        mdelay *= backoff
                        e = _e
                if logger:
                    logger.warning(f"{e}，超出最大重试次数！")
                return ret

            return f_retry

        return deco_retry

    @staticmethod
    def async_retry(
        ExceptionToCheck: Any,
        tries: int = TRIES,
        delay: int = DELAY,
        backoff: int = BACKOFF,
        logger: LoggerManager | Logger | None = None,
        ret: T = None,
    ) -> Callable[..., T]:
        """
        异步重试装饰器

        :param ExceptionToCheck: 需要捕获的异常
        :param tries: 重试次数
        :param delay: 延迟时间
        :param backoff: 延迟倍数
        :param logger: 日志对象（Logger）
        :param ret: 默认返回
        """

        def deco_retry(f: Callable[..., T]) -> Callable[..., T]:
            async def f_retry(*args, **kwargs) -> T:
                mtries, mdelay = tries, delay
                while mtries > 1:
                    try:
                        return await f(*args, **kwargs)
                    except ExceptionToCheck as _e:
                        msg = f"{_e}，{mdelay}秒后重试 ..."
                        if logger:
                            logger.warning(msg)
                        else:
                            print(msg)
                        await async_sleep(mdelay)
                        mtries -= 1
                        mdelay *= backoff
                        e = _e
                if logger:
                    logger.warning(f"{e}，超出最大重试次数！")
                return ret

            return f_retry

        return deco_retry
