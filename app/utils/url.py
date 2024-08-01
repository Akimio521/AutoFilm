from urllib.parse import quote


from app.extensions import SAFE_WORD


class UrlUtils:
    """
    URL相关工具
    """

    @staticmethod
    def encode(url: str) -> str:
        """
        URL编码
        """
        return quote(url, safe=SAFE_WORD)
