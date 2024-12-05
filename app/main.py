from asyncio import get_event_loop
import asyncio
from sys import path
from os.path import dirname

path.append(dirname(dirname(__file__)))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core import settings, logger
from app.extensions import LOGO
from app.modules import Alist2Strm, Ani2Alist


def print_logo() -> None:
    """
    打印 Logo
    """

    print(LOGO)
    print(f" {settings.APP_NAME} {settings.APP_VERSION} ".center(65, "="))
    print("")


def add_task(func, trigger, start_now: bool = False) -> None:
    scheduler.add_job(func, trigger=trigger)
    start_now and once_tasks.append(func)


async def run_server():
    for fun in once_tasks:
        await fun()

    scheduler.start()

    while scheduler.running:
        await asyncio.sleep(1)


if __name__ == "__main__":
    once_tasks = [
        # 添加一次性任务
    ]

    print_logo()

    logger.info(f"AutoFilm {settings.APP_VERSION} 启动中...")
    logger.debug(f"是否开启 DEBUG 模式: {settings.DEBUG}")

    scheduler = AsyncIOScheduler()

    if settings.AlistServerList:
        logger.info("检测到 Alist2Strm 模块配置，正在添加至后台任务")
        for server in settings.AlistServerList:
            cron = server.get("cron")
            start_now = server.pop("start_now", False)
            ins = Alist2Strm(**server)
            if cron:
                add_task(ins.run, CronTrigger.from_crontab(cron), start_now)
                logger.info(f'{server["id"]} 已被添加至后台任务')
            else:
                logger.warning(f'{server["id"]} 未设置 cron')
    else:
        logger.warning("未检测到 Alist2Strm 模块配置")

    if settings.Ani2AlistList:
        logger.info("检测到 Ani2Alist 模块配置，正在添加至后台任务")
        for server in settings.Ani2AlistList:
            cron = server.get("cron")
            start_now = server.pop("start_now", False)
            ins = Ani2Alist(**server)
            if cron:
                add_task(ins.run, CronTrigger.from_crontab(cron), start_now)
                logger.info(f'{server["id"]} 已被添加至后台任务')
            else:
                logger.warning(f'{server["id"]} 未设置 cron')
    else:
        logger.warning("未检测到 Ani2Alist 模块配置")

    logger.info("AutoFilm 启动完成")

    try:
        asyncio.run(run_server())
    except (KeyboardInterrupt, SystemExit):
        logger.info("AutoFilm 程序退出！")
