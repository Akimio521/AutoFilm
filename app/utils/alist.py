from hmac import new as hmac_new
from hashlib import sha256 as hashlib_sha256
from base64 import urlsafe_b64encode

from app.utils.singleton import Singleton


class AlistUtils(metaclass=Singleton):
    """
    Alist 相关工具
    """

    @staticmethod
    def sign(secret_key: str, data: str) -> str:
        """
        计算 Alist 签名
        :param secret_key: Alist 签名 Token
        :param data: Alist 文件绝对路径（未编码）
        """

        if not secret_key:
            return ""
        else:
            h = hmac_new(secret_key.encode(), digestmod=hashlib_sha256)
            expire_time_stamp = str(0)
            h.update((data + ":" + expire_time_stamp).encode())
            return f"?sign={urlsafe_b64encode(h.digest()).decode()}:0"

    @staticmethod
    def structure2dict(text: str) -> dict:
        """
        将能够被 Alist 地址树识别的文本转换为字典，支持键值对中包含两个冒号的情况
        """
        lines = text.strip().split("\n")
        current_folder: str = ""

        def parse_lines(
            start_index: int = 0, indent_level: int = 0
        ) -> tuple[dict, int]:
            result_dict = {}
            i = start_index
            while i < len(lines):
                line = lines[i]
                current_indent = len(line) - len(line.lstrip())

                if current_indent > indent_level:
                    sub_dict, new_index = parse_lines(i, current_indent)
                    result_dict[current_folder] = sub_dict
                    i = new_index
                    continue

                elif current_indent < indent_level:
                    break

                else:
                    parts = line.strip().split(":")
                    if len(parts) == 5:
                        key, value1, value2, value3 = (
                            parts[0].strip(),
                            parts[1].strip(),
                            parts[2].strip(),
                            ":".join(parts[3:]).strip(),
                        )
                        result_dict[key] = [value1, value2, value3]
                    elif len(parts) == 4:
                        key, value1, value2 = (
                            parts[0].strip(),
                            parts[1].strip(),
                            ":".join(parts[2:]).strip(),
                        )
                        result_dict[key] = [value1, value2]
                    elif len(parts) >= 3:
                        key, value = parts[0].strip(), ":".join(parts[1:]).strip()
                        result_dict[key] = value
                    else:
                        current_folder = parts[0]
                        result_dict[current_folder] = {}
                    i += 1

            return result_dict, i

        result_dict, _ = parse_lines()
        return result_dict

    @staticmethod
    def dict2structure(dictionary: dict) -> str:
        """
        将字典转换为能够被 Alist 地址树识别的文本
        """

        def parse_dict(
            sub_dictionary: dict[str, str | list[str] | dict], indent: int = 0
        ):
            result_str = ""
            for key, value in sub_dictionary.items():
                if isinstance(value, str):
                    result_str += " " * indent + f"{key}:{value}\n"
                elif isinstance(value, list):
                    result_str += " " * indent + f"{key}:{':'.join(value)}\n"
                elif isinstance(value, dict):
                    result_str += " " * indent + f"{key}:\n"
                    result_str += parse_dict(value, indent + 2)

                if indent == 0 and result_str.startswith(":"):
                    result_str = result_str.lstrip(":").strip()

            return result_str

        return parse_dict(dictionary)
