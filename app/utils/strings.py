from pypinyin import pinyin, Style


class StringsUtils:
    """
    字符串工具类
    """

    @staticmethod
    def get_pinyin(text: str) -> str:
        """
        获取中文字符串的拼音
        :param text: 中文字符串
        :return: 拼音字符串
        """
        return "".join([item[0] for item in pinyin(text, style=Style.NORMAL)])

    @staticmethod
    def get_initials(text: str) -> str:
        """
        获取中文字符串的首字母
        :param text: 中文字符串
        :return: 首字母字符串
        """
        return "".join([item[0] for item in pinyin(text, style=Style.FIRST_LETTER)])

    @staticmethod
    def get_cn_ascii(text: str) -> str:
        """
        获取中文字符串的 ASCCII 字符串
        :param text: 中文字符串
        :return: ASCCII 字符串
        """
        return "".join(hex(ord(char))[2:] for char in text)  # 移除 hex 前缀 0x
