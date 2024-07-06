import requests
import logging
from typing import Optional


class TheMovieDateBase:
    """
    调用 TMDB  官方 APIv3 获取影视作品信息
    官方 API 文档：https://developers.themoviedb.org/3/
    """

    def __init__(
        self, api_key: str, domain: str = "api.themoviedb.org", language: str = "zh-CN"
    ) -> None:
        """
        实例化 TheMovieDateBase 对象

        :param api_key: TMDB API Key(v3)
        :param domain: TMDB API 域名，默认 "api.themoviedb.org"
        :param language: 语言，默认 "zh-CN"
        """

        self.api_key = api_key
        self.api_url = f"https://{domain}/3"
        self.language = language

        self.timeout = 5

    def search(
        self,
        query_keyword: str,
        page: int = 1,
        media_type: Optional[str] = "multi",
    ) -> Optional[dict]:
        """
        根据关键字匹配剧集，获取相关信息

        :param query_keyword: 查询关键字
        :param page: 查询页数，默认 1
        :param media_type: 查询类型，可选 "multi", "movie", "tv"，默认 "multi"
        :return: 返回查询结果
        """

        if media_type not in ("multi", "movie", "tv"):
            logging.error(f"media_type 参数错误，仅支持 multi, movie, tv 三种类型！")
            return

        url = f"{self.api_url}/search/{media_type}"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "query": query_keyword,
            "page": page,
        }

        return requests.get(url=url, params=params).json()

    def movie_details(self, movie_id: int) -> Optional[dict]:
        """
        根据 movie_id 查询详细电影信息

        :param movie_id: 电影 ID
        :return: 返回查询结果
        """

        url = f"{self.api_url}/movie/{movie_id}"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "movie_id": movie_id,
        }

        return requests.get(url=url, params=params).json()

    def tv_details(self, tv_id: int, season: int = 1) -> Optional[dict]:
        """
        根据 tv_id 查询详细电视剧信息

        :param tv_id: 电视剧 ID
        :param season: 季数，默认 1
        :return: 返回查询结果
        """

        url = f"{self.api_url}/tv/{tv_id}/season/{season}"
        params = {
            "api_key": self.api_key,
            "language": self.language,
        }

        return requests.get(url=url, params=params).json()
