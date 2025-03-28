from os.path import dirname
import asyncio
from sys import path
from typing import Optional

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


async def main() -> None:
    """
    主程序入口，初始化并启动所有服务
    """
    print_logo()
    logger.info(f"AutoFilm {settings.APP_VERSION} 启动中...")
    logger.debug(f"是否开启 DEBUG 模式: {settings.DEBUG}")
    
    # 初始化调度器
    scheduler = AsyncIOScheduler()
    
    # 配置Alist2Strm任务
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
    
    # 配置Ani2Alist任务
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
    
    # 初始化并运行Telegram机器人（如果已配置）
    telegram_bot: Optional[TelegramBot] = None
    if hasattr(settings, 'TelegramBot') and settings.TelegramBot.get('token'):
        logger.info("检测到 Telegram Bot 配置，正在启动")
        telegram_bot = TelegramBot(**settings.TelegramBot)
        # 启动Telegram机器人
        await telegram_bot.start()
    else:
        logger.info("未检测到 Telegram Bot 配置")
    
    # 启动调度器
    scheduler.start()
    logger.info("AutoFilm 启动完成")
    
    try:
        # 保持程序运行
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("AutoFilm 程序退出！")
        if telegram_bot:
            # 停止Telegram机器人
            await telegram_bot.stop()
        # 关闭调度器
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
