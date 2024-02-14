import os
import queue
import threading
import requests
import yaml
import time
import hmac
import hashlib
import base64
from webdav3.client import Client

def sign(secret_key: str, data: str):
    if secret_key == "":
        return ""
    h = hmac.new(secret_key.encode(), digestmod=hashlib.sha256)
    expire_time_stamp = str(0)
    h.update((data + ":" + expire_time_stamp).encode())
    return f"?sign={base64.urlsafe_b64encode(h.digest()).decode()}:0"

def list_files(username: str, password: str, urls_queue: queue.Queue, files_queue: queue.Queue):
    while not urls_queue.empty():
        url = urls_queue.get()
        print(f"{threading.current_thread().name}——正在处理:{url}，剩余{urls_queue.qsize()}个URL待处理")
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
                print(f"{threading.current_thread().name}遇到错误，第{try_number}尝试失败；错误信息：{str(e)}，传入URL：{url}，")
                time.sleep(try_number)
                try_number += 1
            else:
                if try_number > 1:
                    print(f"{url}重连成功")
                break
        for item in items[1:]:
            if item.endswith("/"):
                urls_queue.put(url + item)
            else:
                files_queue.put(url + item)
    print(f"{threading.current_thread().name}处理完毕")

def strm_file(url: str, output_path: str, filename: str, file_absolute_path: str, token: str):
    strm_filename = filename.rsplit(".", 1)[0] + ".strm"
    local_path = os.path.join(output_path, strm_filename)
    if not os.path.exists(local_path):
        try:
            print(f"正在下载：{filename}")
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as file:
                file.write((url.replace("/dav", "/d") + filename + sign(token, file_absolute_path)).encode())
            print(f"{filename}处理成功")
        except Exception as e:
            print(f"{filename}处理失败，错误信息：{str(e)}")
    else:
        print(f"{filename}已存在，跳过处理")

def download_file(url: str, output_path: str, filename: str, file_absolute_path: str, token: str):
    local_path = os.path.join(output_path, filename)
    if not os.path.exists(local_path):
        try:
            print(f"正在下载：{filename}")
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            response = requests.get(url.replace("/dav", "/d") + filename + sign(token, file_absolute_path))
            with open(local_path, "wb") as file:
                file.write(response.content)
        except Exception as e:
            print(f"{filename}下载失败，错误信息：{str(e)}")
    else:
        print(f"{filename}已存在，跳过下载")

def processing_file(output_path: str, url_base: str, files_queue: queue.Queue, subtitle: bool, img: bool, nfo: bool, token: str):
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
            print(f"{threading.current_thread().name}——正在处理:{file_url}，剩余{files_queue.qsize()}个文件待处理")
            filename = file_url.replace(url_base, "")
            if filename.lower().endswith(tuple(video_format)):
                strm_file(url_base, output_path, filename, file_absolute_path, token)
            elif filename.lower().endswith(tuple(subtitle_format)) & subtitle:
                download_file(url_base, output_path, filename, file_absolute_path, token)
            elif filename.lower().endswith(tuple(img_format)) & img:
                download_file(url_base, output_path, filename, file_absolute_path, token)
            elif filename.lower().endswith("nfo") & nfo:
                download_file(url_base, output_path, filename, file_absolute_path, token)
        else:
            waite_number += 1
            print(f"files_queue列表为空，当前尝试次数：{waite_number}，共尝试{waite_max}次，{waite_time}秒后重试")
            time.sleep(waite_time)
    print(f"{threading.current_thread().name}处理完毕")

def main(config_path: str):
    with open(config_path, "r", encoding="utf-8") as file:
        config_data = yaml.safe_load(file)
    output_path = config_data["setting"]["output_path"]
    l_threads = config_data["setting"]["l_threads"]
    p_threads = config_data["setting"]["p_threads"]

    print(f"{'=' * 65}\n输出目录：{output_path}\nlist_files线程数：{l_threads}\nprocessing_file线程数：{p_threads}\n{'=' * 65}")
    subtitle = config_data["setting"]["subtitle"]
    img = config_data["setting"]["img"]
    nfo = config_data["setting"]["nfo"]

    webdav_data = config_data["webdav"]
    print(f"一共读取到{len(webdav_data)}个Webdav配置")

    round = 1
    for key, value in webdav_data.items():
        print(f"开始生成{key}Webdav服务器的Strm文件\n剩余{(len(webdav_data) - round)}个Webdav服务器未进行")
        url = value["url"]
        username = value["username"]
        password = value["password"]
        try:
            token = value["token"]
        except KeyError:
            token = ""

        urls_queue = queue.Queue()
        files_queue = queue.Queue()
        urls_queue.put(url)

        list_files_interval = 10
        lp_interval = 10
        processing_file_interval = 10

        for thread in range(l_threads):
            print(f"list_files线程{thread}启动中")
            t = threading.Thread(target=list_files, args=(username, password, urls_queue, files_queue), name=f"list_files线程{thread}")
            t.start()
            print(f"list_files线程{thread}已启动，{list_files_interval}秒后启动下一个线程")
            time.sleep(list_files_interval)

        time.sleep(lp_interval)

        for thread in range(p_threads):
            print(f"processing_file线程{thread}启动中")
            t = threading.Thread(target=processing_file, args=(output_path, url, files_queue, subtitle, img, nfo, token), name=f"processing_file线程{thread}")
            t.start()
            print(f"processing_file线程{thread}已启动，{processing_file_interval}秒后启动下一个线程")
            time.sleep(processing_file_interval)

        round += 1
