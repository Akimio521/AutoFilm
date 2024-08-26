from re import compile, findall, I

from app.extensions import RELEASEGROUP


def match_relasegroup(title: str = None) -> str:
    """
    匹配资源发布/字幕/制作组

    :param title: 资源标题或文件名
    :return: 匹配结果
    """
    if not title:
        return ""

    release_groups = "|".join(RELEASEGROUP)
    title = title + " "
    groups_re = compile(r"(?<=[-@\[￡【&])(?:%s)(?=[@.\s\]\[】&])" % release_groups, I)
    recognized_groups = []
    for recognized_group in findall(groups_re, title):
        if recognized_group not in recognized_groups:
            recognized_groups.append(recognized_group)
    return "@".join(recognized_groups)
