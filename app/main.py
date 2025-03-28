from asyncio import get_event_loop
from sys import path
from os.path import dirname
import asyncio
path.append(dirname(dirname(__file__)))

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type:ignore
from apscheduler.triggers.cron import CronTrigger  # type:ignore

from app.core import settings, logger
from app.extensions import LOGO
from app.modules import Alist2Strm, Ani2Alist
from app.modules.telegram_bot import TelegramBot


def print_logo() -> None:
    """
    打印 Logo
    """

    print(LOGO)
    print(f" {settings.APP_NAME} {settings.APP_VERSION} ".center(65, "="))
    print("")


if __name__ == "__main__":
    print_logo()

    logger.info(f"AutoFilm {settings.APP_VERSION} 启动中...")
    logger.debug(f"是否开启 DEBUG 模式: {settings.DEBUG}")

    scheduler = AsyncIOScheduler()

    if settings.AlistServerList:
        logger.info("检测到 Alist2Strm 模块配置，正在添加至后台任务")
        for server in settings.AlistServerList:
            cron = server.get("cron")
            if cron:
                scheduler.add_job(
                    Alist2Strm(**server).run, trigger=CronTrigger.from_crontab(cron)
                )
                logger.info(f"{server['id']} 已被添加至后台任务")
            else:
                logger.warning(f"{server['id']} 未设置 cron")
    else:
        logger.warning("未检测到 Alist2Strm 模块配置")

    if settings.Ani2AlistList:
        logger.info("检测到 Ani2Alist 模块配置，正在添加至后台任务")
        for server in settings.Ani2AlistList:
            cron = server.get("cron")
            if cron:
                scheduler.add_job(
                    Ani2Alist(**server).run, trigger=CronTrigger.from_crontab(cron)
                )
                logger.info(f"{server['id']} 已被添加至后台任务")
            else:
                logger.warning(f"{server['id']} 未设置 cron")
    else:
        logger.warning("未检测到 Ani2Alist 模块配置")

    # Initialize and run Telegram bot if configured
    telegram_bot = None
    if hasattr(settings, 'TelegramBot') and settings.TelegramBot.get('token'):
        logger.info("检测到 Telegram Bot 配置，正在启动")
        telegram_bot = TelegramBot(**settings.TelegramBot)
        # Add Telegram bot to event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(telegram_bot.start())
    else:
        logger.info("未检测到 Telegram Bot 配置")

    scheduler.start()
    logger.info("AutoFilm 启动完成")

    try:
        get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("AutoFilm 程序退出！")
        if telegram_bot:
            # Stop the Telegram bot if it was started
            loop = get_event_loop()
            loop.run_until_complete(telegram_bot.stop())
