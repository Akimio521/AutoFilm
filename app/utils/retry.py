"""
重试装饰器
"""

from typing import Any
from time import sleep
from logging import Logger

from app.core.log import LoggerManager

def retry(
    ExceptionToCheck: Any,
    tries: int = 3,
    delay: int = 3,
    backoff: int = 1,
    logger: LoggerManager | Logger | None= None,
    ret: Any = None,
):
    """
    :param ExceptionToCheck: 需要捕获的异常
    :param tries: 重试次数
    :param delay: 延迟时间
    :param backoff: 延迟倍数
    :param logger: 日志对象（LoggerManager | logger）
    :param ret: 默认返回
    """
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 0:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    msg = f"出现错误，{mdelay}秒后重试 ..."
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
