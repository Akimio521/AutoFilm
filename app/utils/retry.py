from asyncio import sleep as async_sleep
from typing import TypeVar, Callable
from time import sleep

from app.core.log import logger
from app.utils.singleton import Singleton

T = TypeVar("T")


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
        ret: T = None,
    ) -> Callable[..., T]:
        """
        同步重试装饰器

        :param exception: 需要捕获的异常
        :param tries: 最大重试次数
        :param delay: 延迟时间
        :param backoff: 延迟倍数
        :param ret: 默认返回
        """

        def deco_retry(f: Callable[..., T]) -> Callable[..., T]:
            def f_retry(*args, **kwargs) -> T:
                mtries, mdelay = tries, delay
                while mtries > 1:
                    try:
                        return f(*args, **kwargs)
                    except exception as _e:
                        logger.warning(cls.WARNING_MSG.format(_e, mdelay))
                        sleep(mdelay)
                        mtries -= 1
                        mdelay *= backoff
                        e = _e
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
        ret: T = None,
    ) -> Callable[..., T]:
        """
        异步重试装饰器

        :param exception: 需要捕获的异常
        :param tries: 最大重试次数
        :param delay: 延迟时间
        :param backoff: 延迟倍数
        :param ret: 默认返回
        """

        def deco_retry(f: Callable[..., T]) -> Callable[..., T]:
            async def f_retry(*args, **kwargs) -> T:
                mtries, mdelay = tries, delay
                while mtries > 1:
                    try:
                        return await f(*args, **kwargs)
                    except exception as _e:
                        logger.warning(cls.WARNING_MSG.format(_e, mdelay))
                        await async_sleep(mdelay)
                        mtries -= 1
                        mdelay *= backoff
                        e = _e
                logger.error(cls.ERROR_MSG.format(e))

                return ret

            return f_retry

        return deco_retry
