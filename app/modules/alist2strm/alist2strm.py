from asyncio import to_thread, Semaphore, TaskGroup
from os import PathLike
from pathlib import Path
from re import compile as re_compile

from aiofile import async_open

from ...core import logger
from ...utils import RequestUtils
from ...extensions import VIDEO_EXTS, SUBTITLE_EXTS, IMAGE_EXTS, NFO_EXTS
from ..alist import AlistClient, AlistPath


class Alist2Strm:
    def __init__(
        self,
        url: str = "http://localhost:5244",
        username: str = "",
        password: str = "",
        token: str = "",
        source_dir: str = "/",
        target_dir: str | PathLike = "",
        flatten_mode: bool = False,
        subtitle: bool = False,
        image: bool = False,
        nfo: bool = False,
        mode: str = "AlistURL",
        overwrite: bool = False,
        other_ext: str = "",
        max_workers: int = 50,
        max_downloaders: int = 5,
        wait_time: float | int = 0,
        sync_server: bool = False,
        sync_ignore: str | None = None,
        **_,
    ) -> None:
        self.client = AlistClient(url, username, password, token)
        self.mode = mode

        self.source_dir = source_dir
        self.target_dir = Path(target_dir)

        self.flatten_mode = flatten_mode
        if flatten_mode:
            subtitle = image = nfo = False

        download_exts: set[str] = set()
        if subtitle:
            download_exts |= SUBTITLE_EXTS
        if image:
            download_exts |= IMAGE_EXTS
        if nfo:
            download_exts |= NFO_EXTS
        if other_ext:
            download_exts |= frozenset(other_ext.lower().split(","))

        self.download_exts = download_exts
        # VIDEO_EXTS will include .m2ts due to changes in app.extensions.exts.py
        self.process_file_exts = VIDEO_EXTS | download_exts

        self.overwrite = overwrite
        self.__max_workers = Semaphore(max_workers)
        self.__max_downloaders = Semaphore(max_downloaders)
        self.wait_time = wait_time
        self.sync_server = sync_server

        if sync_ignore:
            self.sync_ignore_pattern = re_compile(sync_ignore)
        else:
            self.sync_ignore_pattern = None

    def _should_process_file(self, path: AlistPath) -> bool:
        """
        Helper function to determine if a file should be processed.
        Based on the original filter logic.
        """
        if path.is_dir:
            return False

        if path.suffix.lower() not in self.process_file_exts:
            logger.debug(f"文件 {path.name} (后缀: {path.suffix.lower()}) 路径 {path.path} 不在处理列表中: {self.process_file_exts}")
            return False

        try:
            local_path = self.__get_local_path(path)
        except OSError as e:  # 可能是文件名过长
            logger.warning(f"获取 {path.path} 本地路径失败：{e}")
            return False

        # 添加到已处理本地路径集合，因为此文件正在被考虑处理。
        # 如果最终被处理，它将成为清理集合的一部分。
        # 如果由于 overwrite=False 且文件存在而被跳过，它仍然是有效的本地表示。
        self.processed_local_paths.add(local_path)

        if not self.overwrite and local_path.exists():
            if path.suffix.lower() in self.download_exts: # 检查字幕、图像、nfo（非视频文件）
                local_path_stat = local_path.stat()
                if local_path_stat.st_mtime < path.modified_timestamp:
                    logger.debug(f"文件 {local_path.name} 已过期，需要重新处理 {path.path}")
                    return True
                if local_path_stat.st_size < path.size:
                    logger.debug(f"文件 {local_path.name} 大小不匹配，需要重新处理 {path.path}")
                    return True
            logger.debug(f"文件 {local_path.name} 已存在且不覆盖，跳过 {path.path}")
            return False

        return True

    async def run(self) -> None:
        """
        主处理逻辑。
        包括 BDMV M2TS 处理。
        """
        if self.mode not in ["AlistURL", "RawURL", "AlistPath"]:
            logger.warning(f"Alist2Strm 模式 {self.mode} 无效，默认使用 AlistURL")
            self.mode = "AlistURL"

        # is_detail 必须为 True 以获取 M2TS 比较的文件大小和 RawURL 模式。
        is_detail = True

        self.processed_local_paths = set()  # 每次运行重置
        all_paths_from_alist = []
        logger.info(f"开始扫描源目录: {self.source_dir}")

        try:
            async for path_obj in self.client.iter_path(
                dir_path=self.source_dir,
                wait_time=self.wait_time,
                is_detail=is_detail,
                # 使用默认的 filter 函数 (lambda x: True)，不要传递 None
            ):
                all_paths_from_alist.append(path_obj)
        except Exception as e:
            logger.error(f"扫描 Alist 目录 {self.source_dir} 时出错: {e}")
            return # 如果初始扫描失败则停止

        logger.info(f"扫描完成。找到 {len(all_paths_from_alist)} 个项目。正在识别 BDMV 结构。")

        bdmv_largest_m2ts_map = {}  # BDMV_dir_path -> 最大 M2TS 的 AlistPath
        other_m2ts_in_bdmv_stream = set() # STREAM 中非最大的 M2TS 文件路径

        potential_bdmv_roots = [p for p in all_paths_from_alist if p.is_dir and p.name.upper() == "BDMV"]

        for bdmv_path_obj in potential_bdmv_roots:
            bdmv_dir_path_str = bdmv_path_obj.path
            stream_dir_path_str = f"{bdmv_dir_path_str}/STREAM"
            logger.info(f"处理潜在的 BDMV 目录: {bdmv_dir_path_str}")
            
            m2ts_files_in_stream = []
            for path_obj in all_paths_from_alist:
                if (not path_obj.is_dir and
                   path_obj.path.startswith(stream_dir_path_str + "/") and
                   path_obj.suffix.lower() == ".m2ts"):
                    m2ts_files_in_stream.append(path_obj)
            
            if m2ts_files_in_stream:
                largest_m2ts = max(m2ts_files_in_stream, key=lambda f: f.size)
                bdmv_largest_m2ts_map[bdmv_dir_path_str] = largest_m2ts
                logger.info(f"已识别 {bdmv_dir_path_str} 的 BDMV 中最大的 M2TS: {largest_m2ts.path} (大小: {largest_m2ts.size})")
                for m2ts_file in m2ts_files_in_stream:
                    if m2ts_file.path != largest_m2ts.path:
                        other_m2ts_in_bdmv_stream.add(m2ts_file.path)
            else:
                logger.info(f"{bdmv_dir_path_str} 的 BDMV 中 {stream_dir_path_str} 没有找到 M2TS 文件")

        files_to_process_final_map = {}

        for path_obj in all_paths_from_alist:
            is_main_bdmv_m2ts = any(path_obj.path == main_m2ts.path for main_m2ts in bdmv_largest_m2ts_map.values())

            if is_main_bdmv_m2ts:
                if self._should_process_file(path_obj):
                    logger.info(f"添加主要 BDMV M2TS 到处理列表: {path_obj.path}")
                    files_to_process_final_map[path_obj.path] = path_obj
                continue

            if path_obj.path in other_m2ts_in_bdmv_stream:
                logger.debug(f"跳过 BDMV/STREAM 中非最大的 M2TS: {path_obj.path}")
                continue

            is_inside_processed_bdmv = False
            for bdmv_root_path in bdmv_largest_m2ts_map.keys():
                if path_obj.path.startswith(bdmv_root_path + "/"):
                    # 此文件位于我们已识别主 M2TS 的 BDMV 结构内。
                    # 我们只想要这些结构中的主 M2TS。
                    is_inside_processed_bdmv = True
                    break
            
            if is_inside_processed_bdmv:
                logger.debug(f"跳过已识别 BDMV 结构内的其他文件/目录: {path_obj.path}")
                continue
            
            # 不属于已识别 BDMV 结构的常规文件/目录（或没有 M2TS 的 BDMV 结构）
            if self._should_process_file(path_obj):
                logger.debug(f"添加常规文件到处理列表: {path_obj.path}")
                files_to_process_final_map[path_obj.path] = path_obj

        logger.info(f"已识别 {len(files_to_process_final_map)} 个唯一文件进行处理。")

        async with self.__max_workers, TaskGroup() as tg:
            for path_obj_to_process in files_to_process_final_map.values():
                tg.create_task(self.__file_processer(path_obj_to_process))
        
        logger.info(f"文件处理任务已创建。等待完成。")

        # 清理需要在 TaskGroup 完成后进行，由 'async with' 隐式处理
        if self.sync_server:
            await self.__cleanup_local_files()
            logger.info("清理过期的 .strm 文件完成")
        logger.info("Alist2Strm 处理完成")

    async def __file_processer(self, path: AlistPath) -> None:
        local_path = self.__get_local_path(path)

        if self.mode == "AlistURL":
            content = path.download_url
        elif self.mode == "RawURL":
            content = path.raw_url
        elif self.mode == "AlistPath":
            content = path.path
        else:
            # 这种情况理想情况下应该更早被捕获，但作为安全措施：
            logger.error(f"未知的 Alist2Strm 模式 '{self.mode}' 在处理 {path.path} 时")
            return

        try:
            await to_thread(local_path.parent.mkdir, parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"为 {local_path} 创建父目录失败: {e}")
            return

        logger.debug(f"开始处理 {local_path} 对应 {path.path}")
        if local_path.suffix == ".strm":
            try:
                async with async_open(local_path, mode="w", encoding="utf-8") as file:
                    await file.write(content)
                logger.info(f"{local_path.name} 创建成功")
            except Exception as e:
                logger.error(f"写入 .strm 文件 {local_path} 失败: {e}")
        else:
            # 这个分支用于可下载文件，如字幕、图像、nfo
            async with self.__max_downloaders:
                try:
                    await RequestUtils.download(path.download_url, local_path)
                    logger.info(f"{local_path.name} 下载成功")
                except Exception as e:
                    logger.error(f"下载文件 {path.download_url} 到 {local_path} 失败: {e}")

    def __get_local_path(self, path: AlistPath) -> Path:
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
                    logger.info(f"BDMV m2ts 文件 {path.path} 将被扁平化为 {local_path}")
                    return local_path
            
            # 非 BDMV m2ts 文件或 BDMV 结构不完整，使用原有逻辑
            relative_path_str = path.path.replace(self.source_dir, "", 1)
            if relative_path_str.startswith("/"):
                relative_path_str = relative_path_str[1:]
            
            local_path = self.target_dir / Path(relative_path_str)

        if path.suffix.lower() in VIDEO_EXTS:
            local_path = local_path.with_suffix(".strm")

        return local_path

    async def __cleanup_local_files(self) -> None:
        logger.info("开始基于服务器状态清理本地文件。")

        if not self.target_dir.exists():
            logger.info(f"目标目录 {self.target_dir} 不存在。无需清理。")
            return

        if self.flatten_mode:
            all_local_files = [f for f in self.target_dir.iterdir() if f.is_file()]
        else:
            all_local_files = [f for f in self.target_dir.rglob("*") if f.is_file()]

        # self.processed_local_paths 包含与当前运行中考虑处理的服务器文件对应的本地路径
        # （无论是处理过的还是由于 overwrite=false 而跳过的）
        files_to_delete = set(all_local_files) - self.processed_local_paths

        deleted_count = 0
        for file_path in files_to_delete:
            if self.sync_ignore_pattern and self.sync_ignore_pattern.search(file_path.name):
                logger.debug(f"文件 {file_path.name} 在 sync_ignore 列表中，跳过删除。")
                continue

            try:
                if file_path.exists(): # 在解除链接前再次检查存在性
                    await to_thread(file_path.unlink)
                    logger.info(f"删除过期的本地文件: {file_path}")
                    deleted_count +=1

                    if not self.flatten_mode:
                        parent_dir = file_path.parent
                        while parent_dir != self.target_dir and parent_dir.exists() and not any(parent_dir.iterdir()):
                            try:
                                parent_dir.rmdir()
                                logger.info(f"删除空目录: {parent_dir}")
                            except OSError as e_rmdir:
                                logger.warning(f"删除空目录 {parent_dir} 失败: {e_rmdir}")
                                break # 如果一个失败，停止尝试删除父目录
                            parent_dir = parent_dir.parent
            except Exception as e_delete:
                logger.error(f"删除文件 {file_path} 时出错: {e_delete}")
        logger.info(f"清理完成。删除了 {deleted_count} 个文件。")
