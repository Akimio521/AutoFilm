from asyncio import sleep as async_sleep
from typing import Type, Callable, ParamSpec, TypeVar, Optional, Awaitable
from time import sleep
from functools import wraps

from app.core.log import logger
from app.utils.singleton import Singleton

P = ParamSpec("P")
R = TypeVar("R")


class Retry(metaclass=Singleton):
    """
    重试装饰器
    """

    TRIES: int = 3  # 默认最大重试次数
    DELAY: int = 3  # 默认延迟时间
    BACKOFF: int = 1  # 默认延迟倍数

    WARNING_MSG: str = "{}，{}秒后重试 ..."
    ERROR_MSG: str = "{}，超出最大重试次数！"

    @classmethod
    def sync_retry(
        cls,
        exception: Type[Exception],
        tries: int = TRIES,
        delay: int = DELAY,
        backoff: int = BACKOFF,
    ) -> Callable[[Callable[P, R]], Callable[P, Optional[R]]]:
        """
        同步重试装饰器

        :param exception: 需要捕获的异常
        :param tries: 最大重试次数
        :param delay: 延迟时间
        :param backoff: 延迟倍数
        :param ret: 默认返回
        """

        def inner(func: Callable[P, R]) -> Callable[P, Optional[R]]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Optional[R]:
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
                            return None

            return wrapper

        return inner

    @classmethod
    def async_retry(
        cls,
        exception: Type[Exception],
        tries: int = TRIES,
        delay: int = DELAY,
        backoff: int = BACKOFF,
    ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[Optional[R]]]]:
        """
        异步重试装饰器

        :param exception: 需要捕获的异常
        :param tries: 最大重试次数
        :param delay: 延迟时间
        :param backoff: 延迟倍数
        """

        def inner(
            func: Callable[P, Awaitable[R]],
        ) -> Callable[P, Awaitable[Optional[R]]]:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Optional[R]:
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
                            return None

            return wrapper

        return inner
