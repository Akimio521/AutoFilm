from enum import Enum

class Alist2StrmMode(Enum):
    """
    模块 alist2strm 的运行模式
    """
    AlistURL = "AlistURL"
    RawURL = "RawURL"
    AlistPath = "AlistPath"

    @classmethod
    def from_str(cls, mode_str: str) -> "Alist2StrmMode":
        """
        从字符串转换为 AList2StrmMode 枚举
        如果字符串不匹配任何枚举值，则返回 AlistURL 模式
        :param mode_str: 模式字符串
        :return: Alist2StrmMode 枚举值
        例如，"alisturl" 将返回 Alist2StrmMode.AlistURL
        """
        return cls[mode_str.upper()] if mode_str.upper() in cls.__members__ else cls.AlistURL