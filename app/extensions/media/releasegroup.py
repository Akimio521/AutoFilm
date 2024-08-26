from typing import Final

# 电影字幕组
MOVIE_RELEASEGROUP: Final = frozenset()

# 电视剧字幕组
TV_RELEASEGROUP: Final = frozenset()

# 动漫字幕组
ANIEME_RELEASEGROUP: Final = frozenset(
    (
        "ANi",
        "HYSUB",
        "KTXP",
        "LoliHouse",
        "MCE",
        "Nekomoe kissaten",
        "SweetSub",
        "MingY",
        "(?:Lilith|NC)-Raws",
        "织梦字幕组",
        "枫叶字幕组",
        "猎户手抄部",
        "喵萌奶茶屋",
        "漫猫字幕社",
        "霜庭云花Sub",
        "北宇治字幕组",
        "氢气烤肉架",
        "云歌字幕组",
        "萌樱字幕组",
        "极影字幕社",
        "悠哈璃羽字幕社",
        "❀拨雪寻春❀",
        "沸羊羊(?:制作|字幕组)",
        "(?:桜|樱)都字幕组",
    )
)

# 未分类字幕组
OTHER_RELEASEGROUP: Final = frozenset(())

RELEASEGROUP = MOVIE_RELEASEGROUP | TV_RELEASEGROUP | ANIEME_RELEASEGROUP | OTHER_RELEASEGROUP