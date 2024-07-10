#!/usr/bin/env python3
# encoding: utf-8

import asyncio
from sys import path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


from core import settings, logger
path.append(str(settings.BASE_DIR))
from modules import Alist2Strm

if __name__ == "__main__":
    logger.info(f"AutoFilm 启动中，当前的APP版本是：{settings.APP_VERSION}")

    scheduler = AsyncIOScheduler()
    
    if settings.AlistServerList:
        logger.info("检测到 Alist 服务器配置，正在添加至后台任务")
        for server in settings.AlistServerList:
            cron = server.get("cron")
            if cron:
                scheduler.add_job(Alist2Strm(**server).run,trigger=CronTrigger.from_crontab(cron))
                logger.info(f"{server["id"]}已被添加至后台任务")
            else:
                logger.warning(f"{server["id"]}未设置Cron")
    else:
        logger.warning("未检测到 Alist 服务器配置")

    scheduler.start()

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        print("AutoFilm 程序退出！")
