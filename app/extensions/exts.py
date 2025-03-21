from typing import Final

VIDEO_EXTS: Final = frozenset(
    (".mp4", ".mkv", ".flv", ".avi", ".wmv", ".ts", ".rmvb", ".webm", "wmv", ".mpg")
)  # 视频文件后缀
EXTENDED_VIDEO_EXTS: Final = VIDEO_EXTS.union((".strm",))  # 扩展视频文件后缀

SUBTITLE_EXTS: Final = frozenset((".ass", ".srt", ".ssa", ".sub"))  # 字幕文件后缀

IMAGE_EXTS: Final = frozenset((".png", ".jpg"))

NFO_EXTS: Final = frozenset((".nfo",))
