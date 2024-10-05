#!/usr/bin/env python3
# encoding: utf-8

from asyncio import to_thread, Semaphore, TaskGroup
from os import PathLike
from pathlib import Path

from aiofile import async_open
from aiohttp import ClientSession

from app.core import logger
from app.utils import retry
from app.extensions import VIDEO_EXTS, SUBTITLE_EXTS, IMAGE_EXTS, NFO_EXTS
from app.api import AlistClient, AlistPath


class Alist2Strm:

    def __init__(
        self,
        url: str = "http://localhost:5244",
        username: str = "",
        password: str = "",
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
        sync_server: bool = True,
        **_,
    ) -> None:
        """
        Initialize the Alist2Strm object.

        :param url: Alist server URL, default is "http://localhost:5244"
        :param username: Alist username, default is empty
        :param password: Alist password, default is empty
        :param source_dir: Source directory in Alist to synchronize, default is "/"
        :param target_dir: Directory to output .strm files, default is current working directory
        :param flatten_mode: If True, saves all .strm files in a single directory, default is False
        :param subtitle: If True, downloads subtitle files, default is False
        :param image: If True, downloads image files, default is False
        :param nfo: If True, downloads .nfo files, default is False
        :param mode: Strm mode (AlistURL/RawURL/AlistPath)
        :param overwrite: If True, overwrite existing local files, default is False
        :param other_ext: Custom extensions to download, separated by commas, default is empty
        :param max_workers: Maximum number of concurrent workers
        :param max_downloaders: Maximum number of simultaneous downloads
        :param sync_server: If True, synchronizes with the Alist server (deletes obsolete .strm files). Default is True.

        """
        self.url = url
        self.username = username
        self.password = password
        self.mode = mode

        self.source_dir = source_dir
        self.target_dir = Path(target_dir).resolve()

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
            download_exts |= frozenset(
                ext.strip().lower() for ext in other_ext.split(",")
            )

        self.download_exts = download_exts
        self.process_file_exts = VIDEO_EXTS | download_exts

        self.overwrite = overwrite
        self.__max_workers = Semaphore(max_workers)
        self.__max_downloaders = Semaphore(max_downloaders)

        # Initialize processed local paths set
        self.processed_local_paths = set()

        self.sync_server = sync_server  # Store the new parameter

    async def run(self) -> None:
        """
        Main processing function.
        """
        def filter_func(path: AlistPath) -> bool:
            if path.is_dir:
                return False

            if not path.suffix.lower() in self.process_file_exts:
                logger.debug(f"File {path.name} not supported.")
                return False

            return True  # Always True to process all files

        if self.mode not in ["AlistURL", "RawURL", "AlistPath"]:
            logger.warning(
                f"Mode '{self.mode}' not recognized for Alist2Strm. Using default mode 'AlistURL'."
            )
            self.mode = "AlistURL"

        is_detail = self.mode == "RawURL"

        async with self.__max_workers:
            async with ClientSession() as session:
                self.session = session
                async with TaskGroup() as tg:
                    _create_task = tg.create_task
                    async with AlistClient(
                        self.url, self.username, self.password
                    ) as client:
                        async for path in client.iter_path(
                            dir_path=self.source_dir,
                            is_detail=is_detail,
                            filter=filter_func,
                        ):
                            _create_task(self.__file_processor(path))
                logger.info("Alist2Strm processing completed.")

        # If synchronization with the server is enabled
        if self.sync_server:
            # Cleanup step: delete obsolete .strm files and their associated files
            await self.__cleanup_local_files()
            logger.info("Cleanup of obsolete .strm files completed.")

    @retry(Exception, tries=3, delay=3, backoff=2, logger=logger)
    async def __file_processor(self, path: AlistPath) -> None:
        """
        Asynchronously saves the file locally.

        :param path: AlistPath object
        """
        local_path = self.__get_local_path(path)

        # Add the local path to processed paths
        self.processed_local_paths.add(local_path)

        if not self.overwrite and local_path.exists():
            logger.debug(
                f"File {local_path.name} already exists, skipping processing of {path.path}."
            )
            return

        if self.mode == "AlistURL":
            content = path.download_url
        elif self.mode == "RawURL":
            content = path.raw_url
        elif self.mode == "AlistPath":
            content = path.path
        else:
            raise ValueError(f"Unknown mode for AlistStrm: {self.mode}")

        try:
            parent_dir = local_path.parent
            if not parent_dir.exists():
                await to_thread(parent_dir.mkdir, parents=True, exist_ok=True)

            logger.debug(f"Processing {local_path}...")
            if local_path.suffix.lower() == ".strm":
                async with async_open(local_path, mode="w", encoding="utf-8") as file:
                    await file.write(content)
                logger.info(f"{local_path.name} created successfully.")
            else:
                async with self.__max_downloaders:
                    async with async_open(local_path, mode="wb") as file:
                        async with self.session.get(path.download_url) as resp:
                            if resp.status != 200:
                                raise RuntimeError(
                                    f"Failed to download {path.download_url}, status code: {resp.status}"
                                )
                            async for chunk in resp.content.iter_chunked(1024):
                                await file.write(chunk)
                    logger.info(f"{local_path.name} downloaded successfully.")

        except Exception as e:
            raise RuntimeError(f"Failed to process {local_path}, details: {e}")

    def __get_local_path(self, path: AlistPath) -> Path:
        """
        Calculates the local file path based on the AlistPath object and current configuration.

        :param path: AlistPath object
        :return: Local file path
        """
        if self.flatten_mode:
            local_path = self.target_dir / path.name
        else:
            # Ensure that the path is relative to source_dir
            relative_path = path.path
            if relative_path.startswith("/"):
                relative_path = relative_path[1:]
            local_path = self.target_dir / relative_path

        if path.suffix.lower() in VIDEO_EXTS:
            local_path = local_path.with_suffix(".strm")

        return local_path

    async def __cleanup_local_files(self) -> None:
        """
        Deletes local .strm files and their associated files that were not processed in the current run.
        """
        logger.info("Starting cleanup of obsolete .strm files.")

        # Collect all files in target directory
        if self.flatten_mode:
            # Only look in target_dir
            all_local_files = [f for f in self.target_dir.iterdir() if f.is_file()]
        else:
            # Walk through target_dir recursively
            all_local_files = [
                f for f in self.target_dir.rglob("*") if f.is_file()
            ]

        files_to_delete = set(all_local_files) - self.processed_local_paths

        # Delete the files and their associated files
        for file_path in files_to_delete:
            associated_files = self.__get_associated_files(file_path)
            for file in [file_path] + associated_files:
                try:
                    if file.exists():
                        await to_thread(file.unlink)
                        logger.info(f"Obsolete file deleted: {file}")
                except Exception as e:
                    logger.error(f"Failed to delete file {file}: {e}")

    def __get_associated_files(self, file_path: Path) -> list[Path]:
        """
        Retrieves associated files (.nfo, subtitles, etc.) for a given file.

        :param file_path: Path to the file
        :return: List of associated file paths
        """
        associated_files = []

        # Define associated extensions based on configuration
        associated_exts = list(self.download_exts)

        for ext in associated_exts:
            associated_file = file_path.with_suffix(ext)
            associated_files.append(associated_file)

        return associated_files
