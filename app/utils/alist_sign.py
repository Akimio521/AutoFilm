from typing import Optional
from hmac import new as hmac_new
from hashlib import sha256 as hashlib_sha256
from base64 import urlsafe_b64encode

def sign(secret_key: Optional[str], data: str) -> str:
    """
    Alist 签名 Token 处理
    需设置签名为永不过期

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