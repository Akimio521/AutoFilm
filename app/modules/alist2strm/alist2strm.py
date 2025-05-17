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
            logger.debug(f"File {path.name} (suffix: {path.suffix.lower()}) with path {path.path} not in process_file_exts: {self.process_file_exts}")
            return False

        try:
            local_path = self.__get_local_path(path)
        except OSError as e:  # May be filename too long
            logger.warning(f"Getting local path for {path.path} failed: {e}")
            return False

        # Add to processed_local_paths here, as this file is being considered for processing.
        # If it's ultimately processed, it will be part of the set for cleanup.
        # If it's skipped due to overwrite=False and exists, it's still a valid local representation.
        self.processed_local_paths.add(local_path)

        if not self.overwrite and local_path.exists():
            if path.suffix.lower() in self.download_exts: # Check for subtitles, images, nfo (non-video files)
                local_path_stat = local_path.stat()
                if local_path_stat.st_mtime < path.modified_timestamp:
                    logger.debug(f"File {local_path.name} is outdated, reprocessing {path.path}")
                    return True
                if local_path_stat.st_size < path.size:
                    logger.debug(f"File {local_path.name} size mismatch, reprocessing {path.path}")
                    return True
            logger.debug(f"File {local_path.name} exists and overwrite is false, skipping {path.path}")
            return False

        return True

    async def run(self) -> None:
        """
        Main processing logic.
        Includes BDMV M2TS handling.
        """
        if self.mode not in ["AlistURL", "RawURL", "AlistPath"]:
            logger.warning(f"Alist2Strm mode {self.mode} is invalid, defaulting to AlistURL")
            self.mode = "AlistURL"

        # is_detail must be True to get file sizes for M2TS comparison and for RawURL mode.
        is_detail = True

        self.processed_local_paths = set()  # Reset for each run
        all_paths_from_alist = []
        logger.info(f"Starting scan of source directory: {self.source_dir}")

        try:
            async for path_obj in self.client.iter_path(
                dir_path=self.source_dir,
                wait_time=self.wait_time,
                is_detail=is_detail,
                # 使用默认的 filter 函数 (lambda x: True)，不要传递 None
            ):
                all_paths_from_alist.append(path_obj)
        except Exception as e:
            logger.error(f"Error during Alist directory iteration for {self.source_dir}: {e}")
            return # Stop if initial scan fails

        logger.info(f"Scan complete. Found {len(all_paths_from_alist)} items. Identifying BDMV structures.")

        bdmv_largest_m2ts_map = {}  # BDMV_dir_path -> AlistPath of largest M2TS
        other_m2ts_in_bdmv_stream = set() # Paths of M2TS files in STREAM, not the largest

        potential_bdmv_roots = [p for p in all_paths_from_alist if p.is_dir and p.name.upper() == "BDMV"]

        for bdmv_path_obj in potential_bdmv_roots:
            bdmv_dir_path_str = bdmv_path_obj.path
            stream_dir_path_str = f"{bdmv_dir_path_str}/STREAM"
            logger.info(f"Processing potential BDMV directory: {bdmv_dir_path_str}")
            
            m2ts_files_in_stream = []
            for path_obj in all_paths_from_alist:
                if (not path_obj.is_dir and
                   path_obj.path.startswith(stream_dir_path_str + "/") and
                   path_obj.suffix.lower() == ".m2ts"):
                    m2ts_files_in_stream.append(path_obj)
            
            if m2ts_files_in_stream:
                largest_m2ts = max(m2ts_files_in_stream, key=lambda f: f.size)
                bdmv_largest_m2ts_map[bdmv_dir_path_str] = largest_m2ts
                logger.info(f"Identified largest M2TS for BDMV at {bdmv_dir_path_str}: {largest_m2ts.path} (Size: {largest_m2ts.size})")
                for m2ts_file in m2ts_files_in_stream:
                    if m2ts_file.path != largest_m2ts.path:
                        other_m2ts_in_bdmv_stream.add(m2ts_file.path)
            else:
                logger.info(f"No M2TS files found in {stream_dir_path_str} for BDMV at {bdmv_dir_path_str}")

        files_to_process_final_map = {}

        for path_obj in all_paths_from_alist:
            is_main_bdmv_m2ts = any(path_obj.path == main_m2ts.path for main_m2ts in bdmv_largest_m2ts_map.values())

            if is_main_bdmv_m2ts:
                if self._should_process_file(path_obj):
                    logger.info(f"Adding main BDMV M2TS to process list: {path_obj.path}")
                    files_to_process_final_map[path_obj.path] = path_obj
                continue

            if path_obj.path in other_m2ts_in_bdmv_stream:
                logger.debug(f"Skipping non-largest M2TS from BDMV/STREAM: {path_obj.path}")
                continue

            is_inside_processed_bdmv = False
            for bdmv_root_path in bdmv_largest_m2ts_map.keys():
                if path_obj.path.startswith(bdmv_root_path + "/"):
                    # This file is inside a BDMV structure that we've identified a main M2TS for.
                    # We only want the main M2TS from such structures.
                    is_inside_processed_bdmv = True
                    break
            
            if is_inside_processed_bdmv:
                logger.debug(f"Skipping other file/dir inside an identified BDMV structure: {path_obj.path}")
                continue
            
            # Regular file/directory not part of an identified BDMV structure (or a BDMV structure that had no M2TS)
            if self._should_process_file(path_obj):
                logger.debug(f"Adding regular file to process list: {path_obj.path}")
                files_to_process_final_map[path_obj.path] = path_obj

        logger.info(f"Identified {len(files_to_process_final_map)} unique files for processing.")

        async with self.__max_workers, TaskGroup() as tg:
            for path_obj_to_process in files_to_process_final_map.values():
                tg.create_task(self.__file_processer(path_obj_to_process))
        
        logger.info(f"File processing tasks created. Waiting for completion.")

        # Cleanup needs to happen after TaskGroup finishes, implicitly handled by 'async with'
        if self.sync_server:
            await self.__cleanup_local_files()
            logger.info("Cleanup of local files complete.")
        logger.info("Alist2Strm processing run finished.")

    async def __file_processer(self, path: AlistPath) -> None:
        local_path = self.__get_local_path(path)

        if self.mode == "AlistURL":
            content = path.download_url
        elif self.mode == "RawURL":
            content = path.raw_url
        elif self.mode == "AlistPath":
            content = path.path
        else:
            # This case should ideally be caught earlier, but as a safeguard:
            logger.error(f"Unknown Alist2Strm mode '{self.mode}' in __file_processer for {path.path}")
            return

        try:
            await to_thread(local_path.parent.mkdir, parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create parent directory for {local_path}: {e}")
            return

        logger.debug(f"Starting to process {local_path} for {path.path}")
        if local_path.suffix == ".strm":
            try:
                async with async_open(local_path, mode="w", encoding="utf-8") as file:
                    await file.write(content)
                logger.info(f".strm file {local_path.name} created successfully for {path.path}")
            except Exception as e:
                logger.error(f"Failed to write .strm file {local_path}: {e}")
        else:
            # This branch is for downloadable files like subtitles, images, nfo
            async with self.__max_downloaders:
                try:
                    await RequestUtils.download(path.download_url, local_path)
                    logger.info(f"File {local_path.name} downloaded successfully for {path.path}")
                except Exception as e:
                    logger.error(f"Failed to download file {path.download_url} to {local_path}: {e}")

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
                    logger.info(f"BDMV m2ts file {path.path} will be flattened to {local_path}")
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
        logger.info("Starting cleanup of local files based on server state.")

        if not self.target_dir.exists():
            logger.info(f"Target directory {self.target_dir} does not exist. No cleanup needed.")
            return

        if self.flatten_mode:
            all_local_files = [f for f in self.target_dir.iterdir() if f.is_file()]
        else:
            all_local_files = [f for f in self.target_dir.rglob("*") if f.is_file()]

        # self.processed_local_paths contains local paths corresponding to server files
        # that *were considered* for processing in the current run (either processed or skipped due to overwrite=false)
        files_to_delete = set(all_local_files) - self.processed_local_paths

        deleted_count = 0
        for file_path in files_to_delete:
            if self.sync_ignore_pattern and self.sync_ignore_pattern.search(file_path.name):
                logger.debug(f"File {file_path.name} is in sync_ignore list, skipping deletion.")
                continue

            try:
                if file_path.exists(): # Double check existence before unlinking
                    await to_thread(file_path.unlink)
                    logger.info(f"Deleted obsolete local file: {file_path}")
                    deleted_count +=1

                    if not self.flatten_mode:
                        parent_dir = file_path.parent
                        while parent_dir != self.target_dir and parent_dir.exists() and not any(parent_dir.iterdir()):
                            try:
                                parent_dir.rmdir()
                                logger.info(f"Deleted empty directory: {parent_dir}")
                            except OSError as e_rmdir:
                                logger.warning(f"Failed to delete empty directory {parent_dir}: {e_rmdir}")
                                break # Stop trying to delete parents if one fails
                            parent_dir = parent_dir.parent
            except Exception as e_delete:
                logger.error(f"Error deleting file {file_path}: {e_delete}")
        logger.info(f"Cleanup complete. Deleted {deleted_count} files.")

