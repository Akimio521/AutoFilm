from asyncio import sleep as async_sleep
from typing import Any, TypeVar, Callable
from time import sleep

from app.core.log import logger
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
        exception: Exception,
        tries: int = TRIES,
        delay: int = DELAY,
        backoff: int = BACKOFF,
        ret: T = None,
    ) -> Callable[..., T]:
        """
        同步重试装饰器

        :param exception: 需要捕获的异常
        :param tries: 重试次数
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
                        msg = f"{_e}，{mdelay}秒后重试 ..."
                        logger.warning(msg)
                        sleep(mdelay)
                        mtries -= 1
                        mdelay *= backoff
                        e = _e
                logger.error(f"{e}，超出最大重试次数！")
                return ret

            return f_retry

        return deco_retry

    @staticmethod
    def async_retry(
        exception: Exception,
        tries: int = TRIES,
        delay: int = DELAY,
        backoff: int = BACKOFF,
        ret: T = None,
    ) -> Callable[..., T]:
        """
        异步重试装饰器

        :param exception: 需要捕获的异常
        :param tries: 重试次数
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
                        msg = f"{_e}，{mdelay}秒后重试 ..."
                        logger.warning(msg)
                        await async_sleep(mdelay)
                        mtries -= 1
                        mdelay *= backoff
                        e = _e
                logger.error(f"{e}，超出最大重试次数！")

                return ret

            return f_retry

        return deco_retry
