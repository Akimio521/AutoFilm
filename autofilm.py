#! /usr/bin/env python3
# -*- coding:utf-8 -*-
from pathlib import Path
import queue
import threading
import requests
import yaml
import time
import hmac
import hashlib
import base64
import urllib.parse
import logging
from webdav3.client import Client
from typing import Union


class AutoFilm:
    def __init__(self, config_path: str, ):
        self.config_data = {}

        self.urls_queue = queue.Queue()

        self.list_files_thread_interval = 10

        self.try_max = 15

        self.library_mode = True
        self.video_format = ("mp4", "mkv", "flv", "avi", "wmv", "ts", "rmvb", "webm")
        self.subtitle_format = ("ass", "srt", "ssa", "sub")
        self.img_format = ("png", "jpg")

        self.waite_max = 10
        self.waite_time = 5

        try:
            with Path(config_path).open(mode="r", encoding="utf-8") as file:
                self.config_data = yaml.safe_load(file)
        except Exception as e:
            logging.critical(f"配置文件{config_path}加载失败，程序即将停止，错误信息：{str(e)}")
        else:
            self.output_path = self.get_config_value("setting", "output_path", default_value="./media/", error_message="输出路径读取错误，默认设置为'./media/'")
            self.l_threads = self.get_config_value("setting", "l_threads", default_value=1, error_message="list线程数读取错误，默认单线程")
            self.subtitle = self.get_config_value("setting", "subtitle", default_value=False, error_message="字幕设置数读取错误，默认不下载")
            self.img = self.get_config_value("setting", "img", default_value=False, error_message="海报图片设置数读取错误，默认不下载")
            self.nfo = self.get_config_value("setting", "nfo", default_value=False, error_message="视频信息设置读取错误，默认不下载")
            self.url_encode = self.get_config_value("setting", "url_encode", default_value=True, error_message="URL编码设置读取错误，请更新config.yaml")
            logging.info(f"输出目录：{self.output_path}；list_files线程数：{self.l_threads}")

    def run(self) -> None:
        webdav_datas = self.get_config_value("webdav", default_value={}, error_message="Webdav服务器列表读取失败")
        if webdav_datas:
            logging.debug("webdav列表加载成功")
            round = 1
            for key, value in webdav_datas.items():
                logging.info(f"开始生成[{key}]Webdav服务器的Strm文件；剩余{(len(webdav_datas) - round)}个Webdav服务器未进行")
                try:
                    url = value["url"]
                    username = value["username"]
                    password = value["password"]
                    try:
                        token = value["token"]
                    except:
                        logging.warning("Alist令牌token读取错误，默认关闭")
                        token = ""
                except Exception as e:
                    logging.error(f"Webdav服务器账号密码地址读取错误，错误信息：{str(e)}")
                else:
                    self.urls_queue.put(url)

                    threads = []
                    for thread_num in range(self.l_threads):
                        logging.debug(f"list_files线程{thread_num+1}启动中")
                        list_files_thread = threading.Thread(target=self.list_files, args=(username, password, url, token), name=f"list_files线程{thread_num+1}")
                        threads.append(list_files_thread)
                        list_files_thread.start()
                        logging.debug(f"list_files线程{thread_num+1}已启动，{self.list_files_thread_interval}秒后启动下一个线程")
                        time.sleep(self.list_files_thread_interval)

                    for thread in threads:
                        thread.join()

                    round += 1
        else:
            logging.error("webdav列表加载失败")

    def get_config_value(self,*keys: str, default_value: Union[str, bool, int, dict], error_message: str) -> Union[str, bool, int, dict]:
        try:
            config_value = self.config_data
            for key in keys:
                config_value = config_value[key]
        except Exception as e:
            logging.warning(f"{error_message}，错误信息：{str(e)}")
            config_value = default_value
        return config_value
    
    def list_files(self, username, password, base_url, token) -> None:
        while not self.urls_queue.empty():
            url = self.urls_queue.get()
            logging.debug(f"{threading.current_thread().name}——正在处理:{url}，剩余{self.urls_queue.qsize()}个URL待处理")
            client = Client(options={"webdav_hostname": url,"webdav_login": username,"webdav_password": password})
            
            try_number = 1
            while try_number <= self.try_max:
                try:
                    items = client.list()
                    logging.debug(f"{url}目录：{items}")
                except Exception as e:
                    logging.warning(f"{threading.current_thread().name}遇到错误，第{try_number}尝试失败；错误信息：{str(e)}，传入URL：{url}")
                    time.sleep(try_number)
                    try_number += 1
                else:
                    if try_number > 1:
                        logging.warning(f"{url}重连成功")
                    break
            for item in items[1:]:
                if item.endswith("/"):
                    self.urls_queue.put(url + item)
                else:
                    self.processing_file(url + item, base_url, token)
            logging.debug(f"{threading.current_thread().name}处理完毕")

    def get_file_relative_path(self, file_url: str, base_url: str, filename:str) -> str:
        relative_path = file_url.replace(base_url, '').replace(filename, '')
        # 添加斜杠作为路径的结尾
        if not relative_path.endswith("/"):
            relative_path += "/"
        return relative_path
    
    def sign(self, secret_key: str, data: str) -> str:
        if secret_key == "":
            return ""
        h = hmac.new(secret_key.encode(), digestmod=hashlib.sha256)
        expire_time_stamp = str(0)
        h.update((data + ":" + expire_time_stamp).encode())
        return f"?sign={base64.urlsafe_b64encode(h.digest()).decode()}:0"

    def strm_file(self, file_url: str, filename: str, file_absolute_path: str, token: str) -> None:
        strm_filename = filename.rsplit(".", 1)[0] + ".strm"
        local_file_path = Path(self.output_path) / strm_filename

        if not local_file_path.exists():
            try:
                logging.debug(f"正在下载：{filename}")
                local_file_path.parent.mkdir(parents=True, exist_ok=True)
                with local_file_path.open(mode="wb") as file:
                    url_string = file_url.replace("/dav", "/d") + self.sign(secret_key=token, data=file_absolute_path)
                    if self.url_encode:
                        url_string = urllib.parse.quote(url_string, safe='@#$&=:/,;?+\'')
                    file.write(url_string.encode())
                logging.debug(f"{filename}处理成功")
            except Exception as e:
                if local_file_path.exists():
                    local_file_path.unlink()
                logging.warning(f"{filename}处理失败，错误信息：{str(e)}")
        else:
            logging.debug(f"{filename}已存在，跳过处理")

    def download_file(self, file_url: str, filename: str, file_absolute_path: str, token: str) -> None:
        local_file_path = Path(self.output_path) / filename
        if not local_file_path.exists():
            try:
                logging.debug(f"正在下载：{filename}")
                local_file_path.parent.mkdir(parents=True, exist_ok=True) # 创建递归目录
                response = requests.get(file_url.replace("/dav", "/d") + self.sign(secret_key=token, data=file_absolute_path))
                with local_file_path.open(mode="wb") as file:
                    file.write(response.content)
            except Exception as e:
                if local_file_path.exists():
                    local_file_path.unlink()
                logging.warning(f"{filename}下载失败，错误信息：{str(e)}")
        else:
            logging.debug(f"{filename}已存在，跳过下载")

    def processing_file(self,file_url, base_url:str, token: str) -> None:
            logging.debug(f"正在处理:{file_url}")

            file_absolute_path = file_url[file_url.index("/dav") + 4:] # 文件在Webdav服务器上的绝对路径
            filename = Path(file_url).name # 文件名 + 拓展名
            if self.library_mode:
                file_relative_path = self.get_file_relative_path(file_url=file_url, base_url=base_url, filename=filename)
                
                if filename.lower().endswith(self.video_format):
                    self.strm_file(file_url=file_url, filename=file_relative_path + filename, file_absolute_path=file_absolute_path, token=token)
                elif filename.lower().endswith(self.subtitle_format) and self.subtitle:
                    self.download_file(file_url=file_url, filename=file_relative_path + filename, file_absolute_path=file_absolute_path, token=token)
                elif filename.lower().endswith(self.img_format) and self.img:
                    self.download_file(file_url=file_url, filename=file_relative_path + filename, file_absolute_path=file_absolute_path, token=token)
                elif filename.lower().endswith("nfo") and self.nfo:
                    self.download_file(file_url=file_url, filename=file_relative_path + filename, file_absolute_path=file_absolute_path, token=token)
            else:
                if filename.lower().endswith(self.video_format):
                    self.strm_file(file_url=file_url, filename=filename, file_absolute_path=file_absolute_path, token=token)
