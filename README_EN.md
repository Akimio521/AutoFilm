[license]: /LICENSE
[license-badge]: https://img.shields.io/github/license/Akimio521/AutoFilm?style=flat-square&a=1
[prs]: https://github.com/Akimio521/AutoFilm
[prs-badge]: https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square
[issues]: https://github.com/Akimio521/AutoFilm/issues/new
[issues-badge]: https://img.shields.io/badge/Issues-welcome-brightgreen.svg?style=flat-square
[release]: https://github.com/Akimio521/AutoFilm/releases/latest
[release-badge]: https://img.shields.io/github/v/release/Akimio521/AutoFilm?style=flat-square
[docker]: https://hub.docker.com/r/akimio/autofilm
[docker-badge]: https://img.shields.io/docker/pulls/akimio/autofilm?color=%2348BB78&logo=docker&label=pulls

<div align="center">

# AutoFilm

English | [中文](README.md)

**A small project that provides direct link playback for Emby and Jellyfin servers**

[![license][license-badge]][license]
[![prs][prs-badge]][prs]
[![issues][issues-badge]][issues]
[![release][release-badge]][release]
[![docker][docker-badge]][docker]

[Documentation](#documentation) •
[Deployment Methods](#deployment-methods) •
[Benefits of Strm Files](#benefits-of-strm-files) •
[TODO LIST](#todo-list) •
[Changelog](#changelog) •
[Star History](#star-history)

</div>

# Documentation
For more details, see [AutoFilm Documentation](https://blog.akimio.top/posts/1031/)

# Deployment Methods
1. Run with Docker
    ```bash
    docker run -d --name autofilm  -v ./config:/config -v ./media:/media -v ./logs:/logs akimio/autofilm
    ```
2. Run in Python environment (Python 3.12)
    ```bash
    python app/main.py
    ```

# Benefits of Strm Files
- [x] Lightweight Emby server, reducing performance and storage requirements for the Emby server
- [x] Stable operation
- [x] Compared to direct WebDAV access, Emby and Jellyfin servers provide better video search functionality, built-in scrapers, and synchronized playback across multiple devices
- [x] Improved access speed, playback speed not limited by Emby/Jellyfin server bandwidth (requires [MediaWarp](https://github.com/Akimio521/MediaWarp))

# TODO LIST
- [x] Read multiple parameters from config file
- [x] Optimize program efficiency (asynchronous processing)
- [x] Add Docker image
- [x] Strm mode/library mode
- [ ] Integrate TMDB for categorization, renaming, and scraping features

# Changelog
- 2024.8.26: v1.2.4, fixed URL Chinese character encoding issue, added compatibility for Python 3.11, Alist2Strm mode option
- 2024.7.17: v1.2.2, added Ani2Strm module
- 2024.7.8: v1.2.0, modified program logic, used AsyncIOScheduler for background scheduled tasks
- 2024.6.3: v1.1.0, replaced WebDAV with Alist official API for library scanning, adopted asynchronous concurrency to improve efficiency, configuration file changes, supported non-basic path Alist users and users without WebDAV permissions
- 2024.5.29: v1.0.2, optimized running logic, Docker deployment, automatic Docker image packaging
- 2024.2.1: v1.0.0, completely refactored AutoFilm, no longer compatible with v0.1, implemented multithreading, significantly improved task processing speed
- 2024.1.28: v0.1.1, initial version iteration

# Star History
<a href="https://github.com/Akimio521/AutoFilm/stargazers">
    <img width="500" alt="Star History Chart" src="https://api.star-history.com/svg?repos=Akimio521/AutoFilm&type=Date">
</a>
