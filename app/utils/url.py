from urllib.parse import quote, unquote, urlparse


class URLUtils:
    """
    URL 相关工具
    """

    SAFE_WORD = ";/?:@=&"

    @classmethod
    def encode(cls, url: str) -> str:
        """
        URL 编码
        """
        return quote(url, safe=cls.SAFE_WORD)

    @staticmethod
    def decode(strings: str) -> str:
        """
        URL 解码
        """
        return unquote(strings)

    @staticmethod
    def get_resolve_url(url: str) -> tuple[str, str, int]:
        """
        从 URL 中解析协议、域名和端口号

        未知端口号的情况下，端口号设为 -1
        """
        parsed_result = urlparse(url)

        scheme = parsed_result.scheme
        netloc = parsed_result.netloc

        # 去除用户信息
        if "@" in netloc:
            netloc = netloc.split("@")[-1]

        # 处理域名和端口
        if ":" in netloc:
            domain, port_str = netloc.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                port = -1  # 端口号解析失败，设为 0
        else:
            domain = netloc
            if scheme == "http":
                port = 80
            elif scheme == "https":
                port = 443
            else:
                port = -1  # 未知协议，端口号设为 0

        return scheme, domain, port
