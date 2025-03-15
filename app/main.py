import argparse
from asyncio import get_event_loop
from sys import path
from os.path import dirname

path.append(dirname(dirname(__file__)))

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type:ignore
from apscheduler.triggers.cron import CronTrigger  # type:ignore

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


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="AutoFilm 自动化工具")

    # 添加手动运行 Ani2Alist 的选项
    parser.add_argument(
        "-ani2alist",
        action="store_true",
        help="手动运行 Ani2Alist 任务"
    )
    # 添加手动运行 Alist2Strm 的选项
    parser.add_argument(
        "-alist2strm",
        action="store_true",
        help="手动运行 Alist2Strm 任务"
    )

    args = parser.parse_args()

    print_logo()

    logger.info(f"AutoFilm {settings.APP_VERSION} 启动中...")
    logger.debug(f"是否开启 DEBUG 模式: {settings.DEBUG}")

    # 如果命令行参数中包含手动运行 Ani2Alist
    if args.ani2alist:
        # 手动运行 Ani2Alist
        logger.info("手动运行 Ani2Alist 模块...")
        if settings.Ani2AlistList:
            for server in settings.Ani2AlistList:
                ani2alist = Ani2Alist(**server)
                ani2alist.run_manual()  # 手动触发任务
        else:
            logger.warning("未检测到 Ani2Alist 模块配置")
        return  # 手动运行后退出程序

    # 如果命令行参数中包含手动运行 Alist2Strm
    if args.alist2strm:
        logger.info("手动运行 Alist2Strm 模块...")
        if settings.AlistServerList:
            for server in settings.AlistServerList:
                alist2strm = Alist2Strm(**server)
                alist2strm.run_manual()  # 手动触发任务
        else:
            logger.warning("未检测到 Alist2Strm 模块配置")
        return  # 手动运行后退出程序

    # 定时任务部分
    scheduler = AsyncIOScheduler()

    if settings.AlistServerList:
        logger.info("检测到 Alist2Strm 模块配置，正在添加至后台任务")
        for server in settings.AlistServerList:
            cron = server.get("cron")
            if cron:
                scheduler.add_job(
                    Alist2Strm(**server).run, trigger=CronTrigger.from_crontab(cron)
                )
                logger.info(f'{server["id"]} 已被添加至后台任务')
            else:
                logger.warning(f'{server["id"]} 未设置 cron')
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
                logger.info(f'{server["id"]} 已被添加至后台任务')
            else:
                logger.warning(f'{server["id"]} 未设置 cron')
    else:
        logger.warning("未检测到 Ani2Alist 模块配置")

    scheduler.start()
    logger.info("AutoFilm 启动完成")

    try:
        get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("AutoFilm 程序退出！")


if __name__ == "__main__":
    main()
