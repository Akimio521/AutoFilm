import os
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

def sign(secret_key: str, data: str) -> str:
    if secret_key == "":
        return ""
    h = hmac.new(secret_key.encode(), digestmod=hashlib.sha256)
    expire_time_stamp = str(0)
    h.update((data + ":" + expire_time_stamp).encode())
    return f"?sign={base64.urlsafe_b64encode(h.digest()).decode()}:0"

def list_files(username: str, password: str, urls_queue: queue.Queue, files_queue: queue.Queue):
    while not urls_queue.empty():
        url = urls_queue.get()
        logging.debug(f"{threading.current_thread().name}——正在处理:{url}，剩余{urls_queue.qsize()}个URL待处理")
        options = {
            "webdav_hostname": url,
            "webdav_login": username,
            "webdav_password": password
        }
        client = Client(options)

        try_number = 1
        try_max = 15

        while try_number < try_max:
            try:
                items = client.list()
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
                urls_queue.put(url + item)
            else:
                files_queue.put(url + item)
    logging.debug(f"{threading.current_thread().name}处理完毕")

def strm_file(url: str, output_path: str, filename: str, file_absolute_path: str, token: str, url_encode: bool):
    strm_filename = filename.rsplit(".", 1)[0] + ".strm"
    local_path = os.path.join(output_path, strm_filename)
    if not os.path.exists(local_path):
        try:
            logging.debug(f"正在下载：{filename}")
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as file:
                url_string = url.replace("/dav", "/d") + filename + sign(token, file_absolute_path)
                if url_encode:
                    url_string = urllib.parse.quote(url_string, safe='@#$&=:/,;?+\'')
                file.write(url_string.encode())
            logging.debug(f"{filename}处理成功")
        except Exception as e:
            logging.warning(f"{filename}处理失败，错误信息：{str(e)}")
    else:
        logging.debug(f"{filename}已存在，跳过处理")

def download_file(url: str, output_path: str, filename: str, file_absolute_path: str, token: str):
    local_path = os.path.join(output_path, filename)
    if not os.path.exists(local_path):
        try:
            logging.debug(f"正在下载：{filename}")
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            response = requests.get(url.replace("/dav", "/d") + filename + sign(token, file_absolute_path))
            with open(local_path, "wb") as file:
                file.write(response.content)
        except Exception as e:
            logging.warning(f"{filename}下载失败，错误信息：{str(e)}")
    else:
        logging.debug(f"{filename}已存在，跳过下载")

def processing_file(output_path: str, url_base: str, files_queue: queue.Queue, subtitle: bool, img: bool, nfo: bool, token: str, url_encode: bool):
    video_format = ["mp4", "mkv", "flv", "avi", "wmv", "ts", "rmvb", "webm"]
    subtitle_format = ["ass", "srt", "ssa", "sub"]
    img_format = ["png", "jpg"]

    waite_number = 0
    waite_max = 10
    waite_time = 5

    while waite_number < waite_max:
        if not files_queue.empty():
            file_url = files_queue.get()
            file_absolute_path = file_url[file_url.index("/dav") + 4:]
            logging.debug(f"{threading.current_thread().name}——正在处理:{file_url}，剩余{files_queue.qsize()}个文件待处理")
            filename = file_url.replace(url_base, "")
            if filename.lower().endswith(tuple(video_format)):
                strm_file(url_base, output_path, filename, file_absolute_path, token, url_encode)
            elif filename.lower().endswith(tuple(subtitle_format)) & subtitle:
                download_file(url_base, output_path, filename, file_absolute_path, token)
            elif filename.lower().endswith(tuple(img_format)) & img:
                download_file(url_base, output_path, filename, file_absolute_path, token)
            elif filename.lower().endswith("nfo") & nfo:
                download_file(url_base, output_path, filename, file_absolute_path, token)
        else:
            waite_number += 1
            logging.debug(f"files_queue列表为空，当前尝试次数：{waite_number}，共尝试{waite_max}次，{waite_time}秒后重试")
            time.sleep(waite_time)
    logging.debug(f"{threading.current_thread().name}处理完毕")

def get_config_value(*keys: str, config: dict, default_value: Union[str, bool, int], error_message: str) -> Union[str, bool, int]:
    try:
        config_value = config
        for key in keys:
            config_value = config_value[key]
    except Exception as e:
        logging.warning(f"{error_message}，已加载默认配置，错误信息：{str(e)}")
        config_value = default_value
    return config_value

def main(config_path: str):
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config_data = yaml.safe_load(file)
    except Exception as e:
            logging.critical(f"配置文件{config_path}加载失败，程序即将停止，错误信息：{str(e)}")
    else:
        output_path = get_config_value("setting", "output_path", config=config_data, default_value="./media/", error_message="输出路径读取错误")
        l_threads = get_config_value("setting", "l_threads", config=config_data, default_value=1, error_message="list线程数读取错误")
        p_threads = get_config_value("setting", "p_threads", config=config_data, error_message="processing线程数读取错误")
        subtitle = get_config_value("setting", "subtitle", config=config_data, default_value=False, error_message="字幕设置数读取错误")
        img = get_config_value("setting", "img", config=config_data, default_value=False, error_message="海报图片设置数读取错误")
        nfo = get_config_value("setting", "nfo", config=config_data, default_value=False, error_message="视频信息设置读取错误")
        url_encode = get_config_value("setting", "url_encode", config=config_data, default_value=False, error_message="URL编码设置读取错误")

        logging.info(f"输出目录：{output_path}；list_files线程数：{l_threads}；processing_file线程数：{p_threads}")
        try:
            webdav_data = config_data["webdav"]
        except Exception as e:
            logging.critical(f"Webdav服务器配置读取失败，错误信息：{str(e)}")
        else:
            logging.info(f"一共读取到{len(webdav_data)}个Webdav配置")
            round = 1
            for key, value in webdav_data.items():
                logging.info(f"开始生成[{key}]Webdav服务器的Strm文件\；剩余{(len(webdav_data) - round)}个Webdav服务器未进行")
                try:
                    url = value["url"]
                    username = value["username"]
                    password = value["password"]
                except Exception as e:
                    logging.error(f"Webdav服务器账号密码地址读取错误，错误信息：{str(e)}")
                else:
                    try:
                        token = value["token"]
                    except Exception as e:
                        logging.warning(f"Alist令牌token读取错误，请更新config配置文件，错误信息：{str(e)}")
                        token = ""

                    urls_queue = queue.Queue()
                    files_queue = queue.Queue()
                    urls_queue.put(url)

                    list_files_interval = 10
                    lp_interval = 10
                    processing_file_interval = 10

                    for thread in range(l_threads):
                        logging.debug(f"list_files线程{thread}启动中")
                        t = threading.Thread(target=list_files, args=(username, password, urls_queue, files_queue), name=f"list_files线程{thread}")
                        t.start()
                        logging.debug(f"list_files线程{thread}已启动，{list_files_interval}秒后启动下一个线程")
                        time.sleep(list_files_interval)

                    time.sleep(lp_interval)

                    for thread in range(p_threads):
                        logging.debug(f"processing_file线程{thread}启动中")
                        t = threading.Thread(target=processing_file, args=(output_path, url, files_queue, subtitle, img, nfo, token, url_encode), name=f"processing_file线程{thread}")
                        t.start()
                        logging.debug(f"processing_file线程{thread}已启动，{processing_file_interval}秒后启动下一个线程")
                        time.sleep(processing_file_interval)

                    round += 1
