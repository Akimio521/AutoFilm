import argparse
import time

import autofilm
from version import APP_VERSION 


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Autofilm参数配置')
    parser.add_argument('--config_path', type=str, help='配置文件路径', default='./config/config.yaml')
    args = parser.parse_args()

    print(f"当前的APP版本是：{APP_VERSION}")
    print(f'配置文件路径：{args.config_path}')

    autofilm.main(args.config_path)

    print("10秒后程序自动退出")
    time.sleep(10)
