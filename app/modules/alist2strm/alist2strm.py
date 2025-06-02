from asyncio import to_thread, Semaphore, TaskGroup
from os import PathLike
from pathlib import Path
from re import compile as re_compile
from aiofile import async_open

from app.core import logger
from app.utils import RequestUtils
from app.extensions import VIDEO_EXTS, SUBTITLE_EXTS, IMAGE_EXTS, NFO_EXTS
from app.modules.alist import AlistClient, AlistPath

class Alist2Strm:
    # __init__ 方法保持不变
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
        id: str | None = None, # 添加 id 参数以接收配置中的 id，虽然这里没直接用，但保持一致性
        cron: str | None = None, # 添加 cron 参数，同上
        **_,
    ) -> None:
        """
        实例化 Alist2Strm 对象
        :param url: Alist 服务器地址，默认为 "http://localhost:5244"
        :param username: Alist 用户名，默认为空
        :param password: Alist 密码，默认为空
        :param source_dir: 需要同步的 Alist 的目录，默认为 "/"
        :param target_dir: strm 文件输出目录，默认为当前工作目录
        :param flatten_mode: 平铺模式，将所有 Strm 文件保存至同一级目录，默认为 False
        :param subtitle: 是否下载字幕文件，默认为 False
        :param image: 是否下载图片文件，默认为 False
        :param nfo: 是否下载 .nfo 文件，默认为 False
        :param mode: Strm模式(AlistURL/RawURL/AlistPath)
        :param overwrite: 本地路径存在同名文件时是否重新生成/下载该文件，默认为 False
        :param sync_server: 是否同步服务器，启用后若服务器中删除了文件，也会将本地文件删除，默认为 True
        :param other_ext: 自定义下载后缀，使用西文半角逗号进行分割，默认为空
        :param max_workers: 最大并发数
        :param max_downloaders: 最大同时下载
        :param wait_time: 遍历请求间隔时间，单位为秒，默认为 0
        :param sync_ignore: 同步时忽略的文件正则表达式
        """
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
            # 确保 other_ext 中的后缀是小写且包含点，例如 ".mkv"
            # path.suffix 本身会返回带点的后缀
            processed_other_exts = {
                ext.strip().lower() if ext.strip().startswith('.') else '.' + ext.strip().lower()
                for ext in other_ext.split(",") if ext.strip()
            }
            download_exts |= frozenset(processed_other_exts)
            
        self.download_exts = download_exts
        # process_file_exts 决定了哪些文件会被初步筛选出来进行处理
        self.process_file_exts = VIDEO_EXTS | self.download_exts

        self.overwrite = overwrite
        self.__max_workers = Semaphore(max_workers)
        self.__max_downloaders = Semaphore(max_downloaders)
        self.wait_time = wait_time
        self.sync_server = sync_server
        if sync_ignore:
            self.sync_ignore_pattern = re_compile(sync_ignore)
        else:
            self.sync_ignore_pattern = None
        
        self.id = id # 保存id，用于日志等
        logger.info(f"Alist2Strm 实例 ({self.id or '未命名'}) 初始化: source_dir='{self.source_dir}', target_dir='{self.target_dir}', download_exts={self.download_exts}")


    # run 方法保持不变
    async def run(self) -> None:
        """
        处理主体
        """
        def filter(path: AlistPath) -> bool:
            """
            过滤器
            根据 Alist2Strm 配置判断是否需要处理该文件
            将云盘上上的文件对应的本地文件路径保存至 self.processed_local_paths
            :param path: AlistPath 对象
            """
            if path.is_dir:
                return False
            
            # 使用 self.process_file_exts 进行过滤
            if path.suffix.lower() not in self.process_file_exts:
                logger.debug(f"文件 {path.name} (后缀: {path.suffix.lower()}) 不在处理列表 {self.process_file_exts} 中，跳过")
                return False

            try:
                local_path = self.__get_local_path(path)
            except OSError as e:  # 可能是文件名过长
                logger.warning(f"获取 {path.full_path} 本地路径失败：{e}")
                return False

            self.processed_local_paths.add(local_path) # 记录所有应该生成的本地文件路径

            if not self.overwrite and local_path.exists():
                # 对于非 .strm 文件（即下载的文件），检查修改时间和大小
                if local_path.suffix != ".strm": # 或者直接检查 path.suffix.lower() in self.download_exts
                    local_path_stat = local_path.stat()
                    if local_path_stat.st_mtime < path.modified_timestamp:
                        logger.debug(
                            f"文件 {local_path.name} 已过期，需要重新处理 {path.full_path}"
                        )
                        return True
                    if local_path_stat.st_size != path.size: # 对于下载文件，大小应该一致
                        logger.debug(
                            f"文件 {local_path.name} 大小不一致 (本地: {local_path_stat.st_size}, Alist: {path.size})，可能是本地文件损坏，需要重新处理 {path.full_path}"
                        )
                        return True
                
                logger.debug(
                    f"文件 {local_path.name} 已存在且无需更新，跳过处理 {path.full_path}"
                )
                return False
            return True

        if self.mode not in ["AlistURL", "RawURL", "AlistPath"] and not any(ext in VIDEO_EXTS for ext in self.download_exts) :
            logger.warning(
                f"Alist2Strm 的模式 {self.mode} 不存在，已设置为默认模式 AlistURL"
            )
            self.mode = "AlistURL"
        
        # if self.mode == "RawURL": # is_detail 应该由 AlistClient 内部根据需要获取的属性决定，这里不强制
        #     is_detail = True
        # else:
        #     is_detail = False
        # 无论哪种模式，raw_url 和 download_url 都可能需要，所以 is_detail=True 通常更好
        is_detail = True


        self.processed_local_paths = set()  # 云盘文件对应的本地文件路径
        logger.info(f"开始处理 Alist 目录: {self.source_dir} -> 本地目录: {self.target_dir}")
        async with self.__max_workers: # 移除外层 TaskGroup 的 with self.__max_workers
            async with TaskGroup() as tg:
                async for path_obj in self.client.iter_path( # 修改变量名以防与内置 path 冲突
                    dir_path=self.source_dir,
                    wait_time=self.wait_time,
                    is_detail=is_detail, # 确保获取详细信息
                    filter_func=filter, # 传递 filter 函数
                ):
                    # 在这里应用信号量以限制并发任务创建
                    await self.__max_workers.acquire() 
                    task = tg.create_task(self.__file_processer(path_obj))
                    task.add_done_callback(lambda _: self.__max_workers.release())


        if self.sync_server:
            await self.__cleanup_local_files()
            logger.info(f"清理过期的本地文件完成 (任务: {self.id or '未命名'})")

        logger.info(f"Alist2Strm 处理完成 (任务: {self.id or '未命名'})")


    # __file_processer 方法保持不变
    async def __file_processer(self, path: AlistPath) -> None:
        """
        异步保存文件至本地
        :param path: AlistPath 对象
        """
        local_path = self.__get_local_path(path)

        content_for_strm = ""
        if self.mode == "AlistURL":
            content_for_strm = path.download_url
        elif self.mode == "RawURL":
            content_for_strm = path.raw_url
        elif self.mode == "AlistPath":
            content_for_strm = path.full_path
        # else: # 如果模式不匹配且不是下载，则不应到这里，由 __get_local_path 决定后缀

        await to_thread(local_path.parent.mkdir, parents=True, exist_ok=True)
        logger.debug(f"开始处理 {path.full_path} -> {local_path}")

        if local_path.suffix == ".strm":
            if not content_for_strm: # 确保有内容写入 .strm
                 logger.warning(f"为 {local_path.name} 生成 .strm 文件，但 Strm 模式 ({self.mode}) 未提供有效内容来源，将写入空内容或默认下载链接。")
                 content_for_strm = path.download_url # 默认回退
            async with async_open(local_path, mode="w", encoding="utf-8") as file:
                await file.write(content_for_strm)
            logger.info(f"{local_path.name} 创建成功")
        else: # 后缀不是 .strm，意味着需要下载
            async with self.__max_downloaders:
                logger.info(f"开始下载 {path.name} 至 {local_path}")
                await RequestUtils.download(path.download_url, local_path) # 确保使用 path.download_url 进行下载
                # 设置本地文件的修改时间与服务器一致
                if path.modified_timestamp:
                    await to_thread(Path(local_path).touch, mtime=path.modified_timestamp)

                logger.info(f"{local_path.name} 下载成功")


    def __get_local_path(self, path: AlistPath) -> Path:
        """
        根据给定的 AlistPath 对象和当前的配置，计算出本地文件路径。
        如果文件后缀是视频后缀且不在 download_exts (包含 other_exts) 中，则目标后缀为 .strm。
        否则，保持原后缀。
        :param path: AlistPath 对象
        :return: 本地文件路径
        """
        if self.flatten_mode:
            local_path_base_name = path.name
            local_path = self.target_dir / local_path_base_name
        else:
            relative_path_str = path.full_path.replace(self.source_dir, "", 1)
            if relative_path_str.startswith("/"):
                relative_path_str = relative_path_str[1:]
            local_path = self.target_dir / relative_path_str

        file_ext_lower = path.suffix.lower() # e.g. ".mp4"

        # 核心逻辑：
        # 1. 如果文件是视频类型 (在 VIDEO_EXTS 中)
        # 2. 并且，该视频后缀不在 self.download_exts (即用户没有通过 other_ext 指定要下载它)
        # 3. 那么，将其后缀改为 .strm
        # 否则 (不是视频，或者是视频但用户指定要下载)，保持原始后缀
        if file_ext_lower in VIDEO_EXTS and file_ext_lower not in self.download_exts:
            local_path = local_path.with_suffix(".strm")
        # else: 保持 local_path 当前的后缀 (即原始文件后缀)

        return local_path

    # __cleanup_local_files 方法保持不变
    async def __cleanup_local_files(self) -> None:
        """
        删除服务器中已删除的本地的 .strm 文件及其关联文件
        如果文件后缀在 sync_ignore 中，则不会被删除
        """
        logger.info(f"开始清理本地文件 (目录: {self.target_dir})")

        all_local_files_on_disk = set()
        if self.target_dir.exists(): # 确保目标目录存在
            if self.flatten_mode:
                all_local_files_on_disk.update(f for f in self.target_dir.iterdir() if f.is_file())
            else:
                all_local_files_on_disk.update(f for f in self.target_dir.rglob("*") if f.is_file())
        
        # self.processed_local_paths 包含了本次运行应该存在的所有本地文件路径
        # (无论是 .strm 还是直接下载的文件)
        files_to_delete = all_local_files_on_disk - self.processed_local_paths

        deleted_count = 0
        for file_path in files_to_delete:
            if self.sync_ignore_pattern and self.sync_ignore_pattern.search(
                file_path.name # sync_ignore 只作用于文件名
            ):
                logger.debug(f"文件 {file_path} 在忽略列表中，跳过删除")
                continue
            
            # 额外检查：如果flatten_mode为False，且文件的父目录与target_dir不同，
            # 并且该父目录的相对路径前缀不在任何source_dir的处理范围内，则可能不应删除。
            # 这个逻辑比较复杂，暂时按原样处理：只要不在 processed_local_paths 且不被 ignore 就删除。

            try:
                if file_path.exists(): # 再次确认，虽然 iterdir/rglob 通常能保证
                    await to_thread(file_path.unlink)
                    logger.info(f"删除文件：{file_path}")
                    deleted_count +=1
                    
                    # 检查并删除空目录 (仅在非平铺模式下有意义)
                    if not self.flatten_mode:
                        parent_dir = file_path.parent
                        # 循环向上删除空目录，直到 self.target_dir 或遇到非空目录
                        while parent_dir != self.target_dir and parent_dir.exists() and not any(parent_dir.iterdir()):
                            try:
                                parent_dir.rmdir()
                                logger.info(f"删除空目录：{parent_dir}")
                            except OSError as e_rmdir: # 可能因为权限或其他原因删除失败
                                logger.warning(f"尝试删除空目录 {parent_dir} 失败: {e_rmdir}")
                                break # 删除失败则停止向上删除
                            parent_dir = parent_dir.parent
            except Exception as e:
                logger.error(f"删除文件 {file_path} 失败：{e}")
        if deleted_count > 0:
            logger.info(f"共删除了 {deleted_count} 个过期本地文件。")
        else:
            logger.info("没有需要删除的过期本地文件。")
