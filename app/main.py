import asyncio # 确保导入 asyncio
from sys import path, argv # 导入 argv 用于命令行参数
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

async def run_all_alist2strm_tasks() -> None:
    """
    手动运行所有 Alist2Strm 任务
    """
    if settings.AlistServerList:
        logger.info("开始手动执行 Alist2Strm 任务...")
        for server_config in settings.AlistServerList:
            task_id = server_config.get('id', '未命名任务')
            logger.info(f"正在执行 Alist2Strm 任务: {task_id}")
            try:
                # Alist2Strm 的构造函数是 __init__
                alist_task_instance = Alist2Strm(**server_config)
                await alist_task_instance.run()
                logger.info(f"Alist2Strm 任务 {task_id} 执行完成。")
            except Exception as e:
                logger.error(f"执行 Alist2Strm 任务 {task_id} 时发生错误: {e}", exc_info=True)
        logger.info("所有 Alist2Strm 任务已处理完毕。")
    else:
        logger.warning("未检测到 Alist2Strm 模块配置，无任务执行。")

async def run_all_ani2alist_tasks() -> None:
    """
    手动运行所有 Ani2Alist 任务
    """
    if settings.Ani2AlistList:
        logger.info("开始手动执行 Ani2Alist 任务...")
        for server_config in settings.Ani2AlistList:
            task_id = server_config.get('id', '未命名任务') # Ani2Alist 配置中可能没有 'id'，需要确认或调整
            logger.info(f"正在执行 Ani2Alist 任务 (配置 target_dir: {server_config.get('target_dir', '未知')})")
            try:
                # Ani2Alist 的构造函数是 __init__
                ani_task_instance = Ani2Alist(**server_config)
                await ani_task_instance.run()
                logger.info(f"Ani2Alist 任务 (配置 target_dir: {server_config.get('target_dir', '未知')}) 执行完成。")
            except Exception as e:
                logger.error(f"执行 Ani2Alist 任务 (配置 target_dir: {server_config.get('target_dir', '未知')}) 时发生错误: {e}", exc_info=True)
        logger.info("所有 Ani2Alist 任务已处理完毕。")
    else:
        logger.warning("未检测到 Ani2Alist 模块配置，无任务执行。")

if __name__ == "__main__":
    print_logo()
    logger.info(f"AutoFilm {settings.APP_VERSION} 启动中...")
    logger.debug(f"是否开启 DEBUG 模式: {settings.DEBUG}")

    command = "server"  # 默认为 server 模式
    if len(argv) > 1:
        command = argv[1].lower()

    if command == "server":
        logger.info("以服务模式启动...")
        scheduler = AsyncIOScheduler()
        if settings.AlistServerList:
            logger.info("检测到 Alist2Strm 模块配置，正在添加至后台任务")
            for server in settings.AlistServerList:
                cron = server.get("cron")
                if cron:
                    # Alist2Strm 的构造函数是 __init__
                    alist_task_instance = Alist2Strm(**server)
                    scheduler.add_job(
                        alist_task_instance.run, trigger=CronTrigger.from_crontab(cron)
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
                    # Ani2Alist 的构造函数是 __init__
                    ani_task_instance = Ani2Alist(**server)
                    scheduler.add_job(
                        ani_task_instance.run, trigger=CronTrigger.from_crontab(cron)
                    )
                    # Ani2Alist 配置中可能没有 'id'，使用 target_dir 代替或添加 id
                    task_id_log = server.get('id', f"Ani2Alist (target: {server.get('target_dir')})")
                    logger.info(f"{task_id_log} 已被添加至后台任务")
                else:
                    task_id_log = server.get('id', f"Ani2Alist (target: {server.get('target_dir')})")
                    logger.warning(f"{task_id_log} 未设置 cron")
        else:
            logger.warning("未检测到 Ani2Alist 模块配置")

        if scheduler.get_jobs():
            scheduler.start()
            logger.info("AutoFilm 启动完成，后台任务已调度。")
            try:
                asyncio.get_event_loop().run_forever()
            except (KeyboardInterrupt, SystemExit):
                logger.info("AutoFilm 程序退出！")
            finally:
                scheduler.shutdown()
        else:
            logger.info("没有配置任何定时任务，AutoFilm 将退出。")

    elif command == "alist2strm":
        logger.info("手动执行 Alist2Strm 模式...")
        try:
            asyncio.run(run_all_alist2strm_tasks())
        except (KeyboardInterrupt, SystemExit):
            logger.info("手动 Alist2Strm 任务被中断。")
        except Exception as e:
            logger.error(f"手动执行 Alist2Strm 任务时发生未捕获错误: {e}", exc_info=True)
        finally:
            logger.info("Alist2Strm 手动任务执行结束，程序退出。")
            # asyncio.get_event_loop().stop() # 确保事件循环停止

    elif command == "ani2alist":
        logger.info("手动执行 Ani2Alist 模式...")
        try:
            asyncio.run(run_all_ani2alist_tasks())
        except (KeyboardInterrupt, SystemExit):
            logger.info("手动 Ani2Alist 任务被中断。")
        except Exception as e:
            logger.error(f"手动执行 Ani2Alist 任务时发生未捕获错误: {e}", exc_info=True)
        finally:
            logger.info("Ani2Alist 手动任务执行结束，程序退出。")
            # asyncio.get_event_loop().stop() # 确保事件循环停止
    
    else:
        logger.error(f"未知的命令: {command}")
        print(f"用法: python3 app/main.py [server|alist2strm|ani2alist]")
