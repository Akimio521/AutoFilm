from typing import Any

from aiohttp import ClientSession, ClientResponse


class RequestUtils:
    """
    HTTP 异步请求工具类
    """

    __timeout: int = 20  # 请求超时时间

    def __init__(
        self,
        headers: dict = None,
        ua: str = None,
        cookies: str | dict | None = None,
        session: ClientSession = None,
        referer: str = None,
        content_type: str = "application/json; charset=UTF-8",
        accept_type: str = None,
    ):
        """
        初始化请求工具类

        :param headers: 请求头
        :param ua: User-Agent
        :param cookies: 请求 cookies
        :param session: 请求会话
        :param referer: 请求来源
        :param content_type: 请求内容类型
        :param accept_type: 请求接受类型
        """

        if headers:
            self.__headers = headers
        else:
            self.__headers = {}
            if ua is not None:
                self.__headers["User-Agent"] = ua
            if content_type is not None:
                self.__headers["Content-Type"] = content_type
            if accept_type is not None:
                self.__headers["Accept"] = accept_type
            if referer is not None:
                self.__headers["Referer"] = referer

        if isinstance(cookies, str):
            self.__cookies = self.parse_cookie(cookies)
        else:
            self.__cookies = cookies

        if session:
            self.__session = session
        else:
            self.__session = None

    async def request(self, method: str, url: str, **kwargs) -> ClientResponse:
        """
        发起 HTTP 请求

        :param method: HTTP 方法，如 get, post, put 等
        :param url: 请求的 URL
        :param kwargs: 其他请求参数，如 headers, cookies 等
        :return: HTTP 响应对象
        """

        kwargs.setdefault("headers", self.__headers)
        kwargs.setdefault("cookies", self.__cookies)
        kwargs.setdefault("timeout", self.__timeout)

        if not self.__session:
            async with ClientSession() as __session:
                return await __session.request(method=method, url=url, **kwargs)
        return await self.__session.request(method=method, url=url, **kwargs)

    async def get(self, url: str, params: dict = {}, **kwargs) -> ClientResponse:
        """
        发送 GET 请求

        :param url: 请求的URL
        :param params: 请求的参数
        :param kwargs: 其他请求参数，如headers, cookies 等
        :return: HTTP 响应对象
        """
        return await self.request(method="get", url=url, params=params, **kwargs)

    async def post(
        self, url: str, data: Any = None, json: dict = {}, **kwargs
    ) -> ClientResponse:
        """
        发送 POST 请求

        :param url: 请求的URL
        :param data: 请求的数据
        :param json: 请求的JSON数据
        :param kwargs: 其他请求参数，如 headers, cookies 等
        :return: HTTP 响应对象
        """
        return await self.request(
            method="post", url=url, data=data, json=json, **kwargs
        )

    async def put(self, url: str, data: Any = None, **kwargs) -> ClientResponse:
        """
        发送 PUT 请求

        :param url: 请求的 URL
        :param data: 请求的数据
        :param kwargs: 其他请求参数，如h eaders, cookies, proxies 等
        :return: HTTP响应对象
        """
        return self.request(method="put", url=url, data=data, **kwargs)

    @staticmethod
    def parse_cookie(cookies_str: str) -> dict[str, str]:
        """
        解析 cookie，转化为字典

        :param cookies_str: cookie 字符串
        :return: 解析为字典的 cookie
        """
        if not cookies_str:
            return {}
        cookie_dict = {}
        for cookie_str in cookies_str.split(";"):
            cookie_kv = cookie_str.split("=")
            if len(cookie_kv) > 1:
                cookie_dict[cookie_kv[0].strip()] = cookie_kv[1].strip()
        return cookie_dict
