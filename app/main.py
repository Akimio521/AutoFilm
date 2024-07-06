# -*- coding:utf-8 -*-
import argparse
import logging

import autofilm
from version import APP_VERSION

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autofilm参数配置")
    parser.add_argument(
        "--config_path", type=str, help="配置文件路径", default="../config/config.yaml"
    )
    parser.add_argument(
        "--log_level",
        type=str,
        help="日志级别",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    args = parser.parse_args()

    formatter = "[%(asctime)s][%(levelname)s]%(funcName)s:%(message)s"
    logging.basicConfig(format=formatter, level=getattr(logging, args.log_level))

    logging.info(f"当前的APP版本是：{APP_VERSION}")
    logging.info(f"配置文件路径：{args.config_path}")

    my_autofilm = autofilm.AutoFilm(config_path=args.config_path)
    my_autofilm.run_Alist2Strm()
