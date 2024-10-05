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
        sync_server: bool = True,  # Nouveau paramètre
        **_,
    ) -> None:
        """
        Initialise l'objet Alist2Strm.

        :param sync_server: Si True, synchronise avec le serveur Alist (supprime les fichiers .strm obsolètes). Par défaut True.
        Autres paramètres décrits précédemment...
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

        self.sync_server = sync_server  # Enregistrer le nouveau paramètre

    async def run(self) -> None:
        """
        Fonction principale de traitement.
        """
        def filter_func(path: AlistPath) -> bool:
            if path.is_dir:
                return False

            if not path.suffix.lower() in self.process_file_exts:
                logger.debug(f"Fichier {path.name} non pris en charge.")
                return False

            return True  # Toujours True pour traiter tous les fichiers

        if self.mode not in ["AlistURL", "RawURL", "AlistPath"]:
            logger.warning(
                f"Mode '{self.mode}' non reconnu pour Alist2Strm. Utilisation du mode 'AlistURL' par défaut."
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
                logger.info("Traitement Alist2Strm terminé.")

        # Si la synchronisation avec le serveur est activée
        if self.sync_server:
            # Étape de nettoyage : suppression des fichiers .strm obsolètes et de leurs fichiers associés
            await self.__cleanup_local_files()
            logger.info("Nettoyage des fichiers .strm obsolètes terminé.")

    @retry(Exception, tries=3, delay=3, backoff=2, logger=logger)
    async def __file_processor(self, path: AlistPath) -> None:
        """
        Enregistre le fichier localement de manière asynchrone.

        :param path: Objet AlistPath
        """
        local_path = self.__get_local_path(path)

        # Ajouter le chemin local aux chemins traités
        self.processed_local_paths.add(local_path)

        if not self.overwrite and local_path.exists():
            logger.debug(
                f"Fichier {local_path.name} déjà existant, saut du traitement de {path.path}."
            )
            return

        if self.mode == "AlistURL":
            content = path.download_url
        elif self.mode == "RawURL":
            content = path.raw_url
        elif self.mode == "AlistPath":
            content = path.path
        else:
            raise ValueError(f"Mode inconnu pour AlistStrm : {self.mode}")

        try:
            parent_dir = local_path.parent
            if not parent_dir.exists():
                await to_thread(parent_dir.mkdir, parents=True, exist_ok=True)

            logger.debug(f"Traitement de {local_path}...")
            if local_path.suffix.lower() == ".strm":
                async with async_open(local_path, mode="w", encoding="utf-8") as file:
                    await file.write(content)
                logger.info(f"{local_path.name} créé avec succès.")
            else:
                async with self.__max_downloaders:
                    async with async_open(local_path, mode="wb") as file:
                        async with self.session.get(path.download_url) as resp:
                            if resp.status != 200:
                                raise RuntimeError(
                                    f"Échec du téléchargement de {path.download_url}, code d'état : {resp.status}"
                                )
                            async for chunk in resp.content.iter_chunked(1024):
                                await file.write(chunk)
                    logger.info(f"{local_path.name} téléchargé avec succès.")

        except Exception as e:
            raise RuntimeError(f"Échec du traitement de {local_path}, détails : {e}")

    def __get_local_path(self, path: AlistPath) -> Path:
        """
        Calcule le chemin du fichier local en fonction de l'objet AlistPath et de la configuration actuelle.

        :param path: Objet AlistPath
        :return: Chemin du fichier local
        """
        if self.flatten_mode:
            local_path = self.target_dir / path.name
        else:
            # S'assurer que le chemin est relatif à source_dir
            relative_path = path.path
            if relative_path.startswith("/"):
                relative_path = relative_path[1:]
            local_path = self.target_dir / relative_path

        if path.suffix.lower() in VIDEO_EXTS:
            local_path = local_path.with_suffix(".strm")

        return local_path

    async def __cleanup_local_files(self) -> None:
        """
        Supprime les fichiers .strm locaux et leurs fichiers associés qui n'ont pas été traités lors de l'exécution actuelle.
        """
        logger.info("Début du nettoyage des fichiers .strm obsolètes.")

        # Collecter tous les fichiers dans le répertoire cible
        if self.flatten_mode:
            # Ne regarder que dans target_dir
            all_local_files = [f for f in self.target_dir.iterdir() if f.is_file()]
        else:
            # Parcourir target_dir récursivement
            all_local_files = [
                f for f in self.target_dir.rglob("*") if f.is_file()
            ]

        files_to_delete = set(all_local_files) - self.processed_local_paths

        # Supprimer les fichiers et leurs fichiers associés
        for file_path in files_to_delete:
            associated_files = self.__get_associated_files(file_path)
            for file in [file_path] + associated_files:
                try:
                    if file.exists():
                        await to_thread(file.unlink)
                        logger.info(f"Fichier obsolète supprimé : {file}")
                except Exception as e:
                    logger.error(f"Échec de la suppression du fichier {file} : {e}")

    def __get_associated_files(self, file_path: Path) -> list[Path]:
        """
        Récupère les fichiers associés (.nfo, sous-titres, etc.) pour un fichier donné.

        :param file_path: Chemin du fichier
        :return: Liste des chemins des fichiers associés
        """
        associated_files = []

        # Définir les extensions associées en fonction de la configuration
        associated_exts = list(self.download_exts)

        for ext in associated_exts:
            associated_file = file_path.with_suffix(ext)
            associated_files.append(associated_file)

        return associated_files
