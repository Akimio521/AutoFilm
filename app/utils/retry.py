from asyncio import sleep as async_sleep
from typing import TypeVar, Callable
from time import sleep
from functools import wraps

from app.core.log import logger
from app.utils.singleton import Singleton

T1 = TypeVar("T1")
T2 = TypeVar("T2")


class Retry(metaclass=Singleton):
    """
    重试装饰器
    """

    TRIES = 3  # 默认最大重试次数
    DELAY = 3  # 默认延迟时间
    BACKOFF = 1  # 默认延迟倍数

    WARNING_MSG = "{}，{}秒后重试 ..."
    ERROR_MSG = "{}，超出最大重试次数！"

    @classmethod
    def sync_retry(
        cls,
        exception: Exception,
        tries: int = TRIES,
        delay: int = DELAY,
        backoff: int = BACKOFF,
        ret: T2 = None,
    ) -> Callable[..., Callable[..., T1 | T2]]:
        """
        同步重试装饰器

        :param exception: 需要捕获的异常
        :param tries: 最大重试次数
        :param delay: 延迟时间
        :param backoff: 延迟倍数
        :param ret: 默认返回
        """

        def deco_retry(f: Callable[..., T1]) -> Callable[..., T1 | T2]:

            @wraps
            def f_retry(*args, **kwargs) -> T1 | T2:
                remaining_retries = tries
                while remaining_retries > 0:
                    try:
                        return f(*args, **kwargs)
                    except exception as e:
                        remaining_retries -= 1
                        if remaining_retries >= 0:
                            _delay = (tries - remaining_retries) * backoff * delay
                            logger.warning(cls.WARNING_MSG.format(e, _delay))
                            sleep(_delay)
                        else:
                            logger.error(cls.ERROR_MSG.format(e))
                            return ret

            return f_retry

        return deco_retry

    @classmethod
    def async_retry(
        cls,
        exception: Exception,
        tries: int = TRIES,
        delay: int = DELAY,
        backoff: int = BACKOFF,
        ret: T1 = None,
    ) -> Callable[..., Callable[..., T1 | T2]]:
        """
        异步重试装饰器

        :param exception: 需要捕获的异常
        :param tries: 最大重试次数
        :param delay: 延迟时间
        :param backoff: 延迟倍数
        :param ret: 默认返回
        """

        def deco_retry(f: Callable[..., T1]) -> Callable[..., T1 | T2]:

            @wraps
            async def f_retry(*args, **kwargs) -> T1 | T2:
                remaining_retries = tries
                while remaining_retries > 0:
                    try:
                        return await f(*args, **kwargs)
                    except exception as e:
                        remaining_retries -= 1
                        if remaining_retries >= 0:
                            _delay = (tries - remaining_retries) * backoff * delay
                            logger.warning(cls.WARNING_MSG.format(e, _delay))
                            await async_sleep(_delay)
                        else:
                            logger.error(cls.ERROR_MSG.format(e))
                            return ret

            return f_retry

        return deco_retry
