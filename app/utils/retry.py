from asyncio import sleep as async_sleep
from typing import TypeVar, Callable, Type, Any
from time import sleep
from functools import wraps
from collections.abc import Coroutine

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
        exception: Type[Exception],
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

        def inner(func: Callable[..., T1]) -> Callable[..., T1 | T2]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T1 | T2:
                remaining_retries = tries
                while remaining_retries > 0:
                    try:
                        return func(*args, **kwargs)
                    except exception as e:
                        remaining_retries -= 1
                        if remaining_retries >= 0:
                            _delay = (tries - remaining_retries) * backoff * delay
                            logger.warning(cls.WARNING_MSG.format(e, _delay))
                            sleep(_delay)
                        else:
                            logger.error(cls.ERROR_MSG.format(e))
                            return ret

            return wrapper

        return inner

    @classmethod
    def async_retry(
        cls,
        exception: Type[Exception],
        tries: int = TRIES,
        delay: int = DELAY,
        backoff: int = BACKOFF,
        ret: T1 = None,
    ) -> Callable[..., Callable[..., Coroutine[Any, Any, T1 | T2]]]:
        """
        异步重试装饰器

        :param exception: 需要捕获的异常
        :param tries: 最大重试次数
        :param delay: 延迟时间
        :param backoff: 延迟倍数
        :param ret: 默认返回
        """

        def inner(
            func: Callable[..., T1],
        ) -> Callable[..., Coroutine[Any, Any, T1 | T2]]:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> T1 | T2:
                remaining_retries = tries
                while remaining_retries > 0:
                    try:
                        return await func(*args, **kwargs)
                    except exception as e:
                        remaining_retries -= 1
                        if remaining_retries >= 0:
                            _delay = (tries - remaining_retries) * backoff * delay
                            logger.warning(cls.WARNING_MSG.format(e, _delay))
                            await async_sleep(_delay)
                        else:
                            logger.error(cls.ERROR_MSG.format(e))
                            return ret

            return wrapper

        return inner
