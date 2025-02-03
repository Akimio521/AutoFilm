from typing import Final
from datetime import datetime

from feedparser import parse  # type:ignore

from app.core import logger
from app.utils import RequestUtils, URLUtils
from app.utils import AlistUrlTreeUtils
from app.modules.alist import AlistClient

VIDEO_MINETYPE: Final = frozenset(("video/mp4", "video/x-matroska"))
SUBTITLE_MINETYPE: Final = frozenset(("application/octet-stream",))
ZIP_MINETYPE: Final = frozenset(("application/zip",))
FILE_MINETYPE: Final = VIDEO_MINETYPE | SUBTITLE_MINETYPE | ZIP_MINETYPE

ANI_SEASION: Final = frozenset((1, 4, 7, 10))


class Ani2Alist:
    """
    将 ANI Open 项目的视频通过地址树的方式挂载在 Alist服务器上
    """

    def __init__(
        self,
        url: str = "http://localhost:5244",
        username: str = "",
        password: str = "",
        token: str = "",
        target_dir: str = "/Anime",
        rss_update: bool = True,
        year: int | None = None,
        month: int | None = None,
        src_domain: str = "aniopen.an-i.workers.dev",
        rss_domain: str = "api.ani.rip",
        key_word: str | None = None,
        **_,
    ) -> None:
        """
        实例化 Ani2Alist 对象

        :param origin: Alist 服务器地址，默认为 "http://localhost:5244"
        :param username: Alist 用户名，默认为空
        :param password: Alist 密码，默认为空
        :param token: Alist Token，默认为空
        :param target_dir: 挂载到 Alist 服务器上目录，默认为 "/Anime"
        :param rss_update: 使用 RSS 追更最新番剧，默认为 True
        :param year: 动画年份，默认为空
        :param month: 动画季度，默认为空
        :param src_domain: ANI Open 项目地址，默认为 "aniopen.an-i.workers.dev"，可自行反代
        :param rss_domain ANI Open 项目 RSS 地址，默认为 "api.ani.rip"，可自行反代
        :param key_word: 自定义关键字，默认为空
        """

        def is_time_valid(year: int, month: int) -> tuple[bool, str]:
            """
            判断时间是否合理
            :return: (是否合理, 错误信息)
            """
            current_date = datetime.now()
            if (year, month) == (2019, 4):
                return False, "2019-4 季度暂无数据"
            elif (year, month) < (2019, 1):
                return False, "ANI Open 项目仅支持2019年1月及其之后的数据"
            elif (year, month) > (current_date.year, current_date.month):
                return False, "传入的年月晚于当前时间"
            else:
                return True, ""

        self.__url = url
        self.__username = username
        self.__password = password
        self.__token = token
        self.__target_dir = "/" + target_dir.strip("/")

        self.__year = None
        self.__month = None
        self.__key_word = None
        self.__rss_update = rss_update

        if rss_update:
            logger.debug("使用 RSS 追更最新番剧")
        elif key_word:
            logger.debug(f"使用自定义关键字：{key_word}")
            self.__key_word = key_word
        elif year and month:
            is_valid, msg = is_time_valid(year, month)
            if is_valid:
                logger.debug(f"传入季度：{year}-{month}")
                self.__year = year
                self.__month = month
            else:
                logger.error(f"时间验证出错，默认使用当前季度：{msg}")
        elif year or month:
            logger.warning("未传入完整时间参数，默认使用当前季度")
        else:
            logger.debug("未传入时间参数，默认使用当前季度")

        self.__src_domain = src_domain.strip()
        self.__rss_domain = rss_domain.strip()

    async def run(self) -> None:
        def merge_dicts(target_dict: dict, source_dict: dict) -> dict:
            for key, value in source_dict.items():
                if key not in target_dict:
                    target_dict[key] = value
                elif isinstance(target_dict[key], dict) and isinstance(value, dict):
                    merge_dicts(target_dict[key], value)
                else:
                    target_dict[key] = value
            return target_dict

        folder = self.__get_folder
        logger.info(f"开始更新 ANI Open {folder} 番剧")

        if self.__rss_update:
            anime_dict = await self.get_rss_anime_dict
        else:
            anime_dict = await self.get_season_anime_list

        client = AlistClient(self.__url, self.__username, self.__password, self.__token)
        storage = await client.get_storage_by_mount_path(
            mount_path=self.__target_dir,
            create=True,
            driver="UrlTree",
        )
        if storage is None:
            logger.error(f"未找到挂载路径：{self.__target_dir}，并且无法创建")
            return

        addition_dict = storage.addition2dict
        url_dict = AlistUrlTreeUtils.structure2dict(
            addition_dict.get("url_structure", "")
        )

        if url_dict.get(folder) is None:
            url_dict[folder] = {}

        url_dict[folder] = merge_dicts(url_dict[folder], anime_dict)

        addition_dict["url_structure"] = AlistUrlTreeUtils.dict2structure(url_dict)
        storage.set_addition_by_dict(addition_dict)

        await client.sync_api_admin_storage_update(storage)
        logger.info(f"ANI Open {folder} 更新完成")

    @property
    def __get_folder(self) -> str:
        """
        根据 self.__year 和 self.__month 以及关键字 self.__key_word 返回文件夹名
        """
        if self.__key_word:
            return self.__key_word

        current_date = datetime.now()
        if self.__year and self.__month:
            year = self.__year
            month = self.__month
        else:
            year = current_date.year
            month = current_date.month

        for _month in range(month, 0, -1):
            if _month in ANI_SEASION:
                return f"{year}-{_month}"

    @property
    async def get_season_anime_list(self) -> dict:
        """
        获取指定季度的动画列表
        """
        folder = self.__get_folder
        logger.debug(f"开始获取 ANI Open {folder} 动画列表")
        url = URLUtils.encode(f"https://{self.__src_domain}/{folder}/")

        async def parse_data(_url: str = url) -> dict:
            logger.debug(f"请求地址：{_url}")
            _resp = await RequestUtils.post(_url)
            if _resp.status_code != 200:
                raise Exception(f"请求发送失败，状态码：{_resp.status_code}")

            _result = _resp.json()

            _anime_dict = {}
            for file in _result["files"]:
                mimeType: str = file["mimeType"]
                name: str = file["name"]
                quoted_name = URLUtils.encode(name)

                if mimeType in FILE_MINETYPE:
                    size: int = file["size"]
                    __url = _url + quoted_name + "?d=true"
                    logger.debug(
                        f"获取文件：{name}，文件大小：{int(size) / 1024 / 1024:.2f}MB，播放地址：{__url}"
                    )
                    _anime_dict[name] = [
                        size,
                        __url,
                    ]
                elif mimeType == "application/vnd.google-apps.folder":
                    logger.debug(f"获取目录：{name}")
                    __url = _url + quoted_name + "/"
                    _anime_dict[name] = await parse_data(__url)
                else:
                    raise RuntimeError(f"无法识别类型：{mimeType}，文件详情：\n{file}")
            return _anime_dict

        logger.debug(f"获取 ANI Open {folder} 动画列表成功")
        return await parse_data()

    @property
    async def get_rss_anime_dict(self) -> dict:
        """
        获取 RSS 动画列表
        """

        def convert_size_to_bytes(size_str: str) -> int:
            """
            将带单位的大小转换为字节
            """
            units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
            number, unit = [string.strip() for string in size_str.split()]
            return int(float(number) * units[unit])

        logger.debug(f"开始获取 ANI Open RSS 动画列表")
        url = f"https://{self.__rss_domain}/ani-download.xml"

        resp = await RequestUtils.get(url)
        if resp.status_code != 200:
            raise Exception(f"请求发送失败，状态码：{resp.status_code}")
        # print(type(resp.text()), "\n", resp.text())
        feeds = parse(resp.text)

        rss_anime_dict = {}
        for entry in feeds.entries:
            """
            print(type(entry))
            print(entry)

            type: <class 'feedparser.util.FeedParserDict'>
            {
                "title": "[ANi] FAIRY TAIL 魔導少年 百年任務 - 18 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4",
                "title_detail": {
                    "type": "text/plain",
                    "language": None,
                    "base": "",
                    "value": "[ANi] FAIRY TAIL 魔導少年 百年任務 - 18 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4",
                },
                "links": [
                    {
                        "rel": "alternate",
                        "type": "text/html",
                        "href": "https://resources.ani.rip/2024-7/%5BANi%5D%20FAIRY%20TAIL%20%E9%AD%94%E5%B0%8E%E5%B0%91%E5%B9%B4%20%E7%99%BE%E5%B9%B4%E4%BB%BB%E5%8B%99%20-%2018%20%5B1080P%5D%5BBaha%5D%5BWEB-DL%5D%5BAAC%20AVC%5D%5BCHT%5D.mp4?d=true",
                    }
                ],
                "link": "https://resources.ani.rip/2024-7/%5BANi%5D%20FAIRY%20TAIL%20%E9%AD%94%E5%B0%8E%E5%B0%91%E5%B9%B4%20%E7%99%BE%E5%B9%B4%E4%BB%BB%E5%8B%99%20-%2018%20%5B1080P%5D%5BBaha%5D%5BWEB-DL%5D%5BAAC%20AVC%5D%5BCHT%5D.mp4?d=true",
                "id": "https://resources.ani.rip/2024-7/%5BANi%5D%20FAIRY%20TAIL%20%E9%AD%94%E5%B0%8E%E5%B0%91%E5%B9%B4%20%E7%99%BE%E5%B9%B4%E4%BB%BB%E5%8B%99%20-%2018%20%5B1080P%5D%5BBaha%5D%5BWEB-DL%5D%5BAAC%20AVC%5D%5BCHT%5D.mp4?d=true",
                "guidislink": False,
                "published": "Sun, 10 Nov 2024 09:01:47 GMT",
                "published_parsed": time.struct_time(
                    tm_year=2024,
                    tm_mon=11,
                    tm_mday=10,
                    tm_hour=9,
                    tm_min=1,
                    tm_sec=47,
                    tm_wday=6,
                    tm_yday=315,
                    tm_isdst=0,
                ),
                "anime_size": "473.0 MB",
            }
            """
            rss_anime_dict[entry.title] = [
                convert_size_to_bytes(entry.anime_size),
                entry.link,
            ]

        logger.debug(f"获取 RSS 动画列表成功")
        return rss_anime_dict
