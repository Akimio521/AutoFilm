from asyncio import TaskGroup
from pathlib import Path
from typing import List, Set, Dict, Any, Callable, Optional
from re import compile as re_compile

from aiofile import async_open

from ...core import logger
from ...utils import RequestUtils
from ...extensions import VIDEO_EXTS, SUBTITLE_EXTS, IMAGE_EXTS, NFO_EXTS
from ..alist import AlistClient, AlistPath


class Alist2Strm:
    """
    将 Alist 中的视频文件转换为 .strm 文件
    """

    def __init__(
        self,
        client: AlistClient,
        source_dir: str,
        target_dir: str,
        max_workers: int = 10,
        flatten_mode: bool = False,
        sync_server: bool = False,
        sync_ignore: str | None = None,
        **_,
    ):
        """
        初始化 Alist2Strm 对象

        :param client: AlistClient 对象
        :param source_dir: Alist 中的源目录
        :param target_dir: 本地目标目录
        :param max_workers: 最大并发数
        :param flatten_mode: 是否扁平化目录结构
        :param sync_server: 是否同步服务器文件
        :param sync_ignore: 同步忽略的文件后缀，使用 | 分隔
        """
        self.client = client
        self.source_dir = source_dir
        self.target_dir = Path(target_dir)
        self.max_workers = max_workers
        self.flatten_mode = flatten_mode
        self.sync_server = sync_server
        self.sync_ignore = sync_ignore
        self.wait_time = 0.5

        self.__max_workers = RequestUtils.Semaphore(max_workers)
        self.processed_local_paths: Set[Path] = set()

    async def process(self, filter: Callable[[AlistPath], bool] | None = None) -> None:
        """
        处理 Alist 中的视频文件

        :param filter: 过滤函数，返回 True 表示处理该文件，返回 False 表示跳过该文件
        """
        if filter is None:
            filter = lambda x: True

        # 确保目标目录存在
        self.target_dir.mkdir(parents=True, exist_ok=True)

        # 获取 Alist 中的所有文件
        all_paths_from_alist: List[AlistPath] = []
        try:
            is_detail = False
            if self.sync_server:
                is_detail = True

            self.processed_local_paths = set()  # 云盘文件对应的本地文件路径

            async with self.__max_workers, TaskGroup() as tg:
                async for path in self.client.iter_path(
                    dir_path=self.source_dir,
                    wait_time=self.wait_time,
                    is_detail=is_detail,
                    # 使用默认的 filter 函数 (lambda x: True)，不要传递 None
                ):
                    tg.create_task(self.__file_processer(path))

        except Exception as e:
            logger.error(f"Failed to get all paths from Alist: {e}")

        if self.sync_server:
            await self.__cleanup_local_files()

    async def __file_processer(self, path: AlistPath) -> None:
        """
        处理单个文件

        :param path: AlistPath 对象
        """
        try:
            # 如果是目录，则跳过
            if path.is_dir:
                return

            # 如果不是视频文件，则跳过
            if path.suffix.lower() not in VIDEO_EXTS:
                return

            # 获取本地文件路径
            local_path = self.__get_local_path(path)

            # 确保父目录存在
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # 记录处理过的本地文件路径
            self.processed_local_paths.add(local_path)

            # 如果本地文件已存在，则跳过
            if local_path.exists():
                return

            # 写入 .strm 文件
            async with async_open(local_path, "w") as f:
                await f.write(path.download_url)
                logger.info(f"Created .strm file: {local_path}")
        except Exception as e:
            logger.error(f"Failed to process file {path.path}: {e}")

    async def download_file(self, path: AlistPath, local_path: Path | None = None) -> None:
        """
        下载文件

        :param path: AlistPath 对象
        :param local_path: 本地文件路径，如果为 None，则使用默认路径
        """
        if local_path is None:
            local_path = self.__get_local_path(path)

        # 确保父目录存在
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # 如果本地文件已存在，则跳过
        if local_path.exists():
            return

        # 下载文件
        try:
            async with self.client.session.get(path.download_url) as resp:
                if resp.status == 200:
                    async with async_open(local_path, "wb") as f:
                        await f.write(await resp.read())
                    logger.info(f"Downloaded file: {local_path}")
                else:
                    logger.error(f"Failed to download file {path.download_url} to {local_path}: {resp.status}")
        except Exception as e:
            logger.error(f"Failed to download file {path.download_url} to {local_path}: {e}")

    def __get_local_path(self, path: AlistPath) -> Path:
        """
        根据给定的 AlistPath 对象和当前的配置，计算出本地文件路径。

        :param path: AlistPath 对象
        :return: 本地文件路径
        """
        # 检查是否是 BDMV 结构中的 m2ts 文件
        is_bdmv_m2ts = False
        if path.suffix.lower() == ".m2ts" and "/BDMV/STREAM/" in path.path:
            is_bdmv_m2ts = True
            
        if self.flatten_mode:
            # 扁平模式下，所有文件都直接放在目标目录下
            local_path_name = path.name
            local_path = self.target_dir / local_path_name
        else:
            # 非扁平模式下，需要特殊处理 BDMV 中的主 m2ts 文件
            if is_bdmv_m2ts:
                # 对于 BDMV 中的 m2ts 文件，提取电影目录名称
                # 例如：/movies/海边的异邦人 (2020)/BDMV/STREAM/00002.m2ts
                # 我们需要提取 "海边的异邦人 (2020)" 作为文件名
                
                # 先获取相对路径
                relative_path_str = path.path.replace(self.source_dir, "", 1)
                if relative_path_str.startswith("/"):
                    relative_path_str = relative_path_str[1:]
                
                # 分割路径，获取电影目录名称
                path_parts = relative_path_str.split("/")
                if len(path_parts) >= 4:  # 至少应该有 [电影名, BDMV, STREAM, 文件名]
                    movie_dir_name = path_parts[0]
                    # 使用电影目录名称作为文件名
                    local_path = self.target_dir / movie_dir_name / f"{movie_dir_name}.strm"
                    logger.info(f"BDMV m2ts file {path.path} will be flattened to {local_path}")
                    return local_path
            
            # 非 BDMV m2ts 文件或 BDMV 结构不完整，使用原有逻辑
            relative_path = path.path.replace(self.source_dir, "", 1)
            if relative_path.startswith("/"):
                relative_path = relative_path[1:]
            local_path = self.target_dir / relative_path

        if path.suffix.lower() in VIDEO_EXTS:
            local_path = local_path.with_suffix(".strm")

        return local_path

    async def __cleanup_local_files(self) -> None:
        """
        删除服务器中已删除的本地的 .strm 文件及其关联文件
        如果文件后缀在 sync_ignore 中，则不会被删除
        """
        # 获取本地所有的 .strm 文件
        local_strm_files = set()
        for strm_file in self.target_dir.glob("**/*.strm"):
            local_strm_files.add(strm_file)

        # 计算需要删除的文件
        files_to_delete = local_strm_files - self.processed_local_paths

        # 如果有 sync_ignore，则过滤掉不需要删除的文件
        if self.sync_ignore:
            ignore_pattern = re_compile(self.sync_ignore)
            files_to_delete = {
                file_path
                for file_path in files_to_delete
                if not ignore_pattern.search(str(file_path))
            }

        # 删除文件
        for file_path in files_to_delete:
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"删除文件：{file_path}")

                    # 检查并删除空目录
                    parent_dir = file_path.parent
                    while parent_dir != self.target_dir:
                        if any(parent_dir.iterdir()):
                            break  # 目录不为空，跳出循环
                        else:
                            parent_dir.rmdir()
                            logger.info(f"删除空目录：{parent_dir}")
                        parent_dir = parent_dir.parent
            except Exception as e:
                logger.error(f"删除文件 {file_path} 失败：{e}")
