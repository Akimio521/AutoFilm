from typing import Final

VIDEO_EXTS: Final = frozenset(("mp4", "mkv", "flv", "avi", "wmv", "ts", "rmvb", "webm"))
EXTENDED_VIDEO_EXTS: Final = VIDEO_EXTS.union(("strm",))

SUBTITLE_EXTS: Final = frozenset(("ass", "srt", "ssa", "sub"))

IMAGE_EXTS: Final = frozenset(("png", "jpg"))

NFO_EXTS: Final = frozenset(("nfo",))