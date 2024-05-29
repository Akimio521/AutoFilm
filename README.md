# Akimio521/AutoFilm
**一个为Emby、Jellyfin服务器提供直链播放的小项目**

# 说明文档
详情见[AutoFilm说明文档](https://blog.akimio.top/posts/1031/)

# 部署方式
1. Python环境运行
    ```bash
    python main.py
    ```
2. Docker运行
    ```bash
    docker run --name autofilm -d -v ./config:/app/config -v ./media:/app/media -e INTERVAL=3600 akimio/autofilm
    ```

# 优点
- [x] 轻量化Emby服务器，降低Emby服务器的性能需求以及硬盘需求
- [x] 运行稳定
- [x] 相比直接访问Webdav，Emby、Jellyfin服务器可以提供更好的视频搜索功能以及自带刮削器，以及多设备同步播放进度
- [x] ~~提高访问速度，播放速度不受Jellyfin服务器带宽限制~~(新版Jellyfin对Strm文件的播放策略有所改变，似乎已经不再不受限制，有待确认)

# TODO LIST
- [x] 从config文件中读取多个参数
- [x] 优化程序运行效率（多线程处理）
- [x] 增加Docker镜像
- [x] Strm模式/媒体库模式
- [ ] 监控模式
- [ ] 对接TMDB实现分类、重命名、刮削等功能

# 更新日志
- 2024.5.29：v1.0.2，优化运行逻辑，Docker部署，自动打包Docker镜像
- 2024.2.1：v1.0.0，完全重构AutoFilm，不再兼容v0.1，实现多线程，大幅度提升任务处理速度
- 2024.1.28：v0.1.1，初始版本持续迭代

# 开源许可证
**本项目采用 GNU Affero General Public License（GNU AGPL）开源许可证。**

## 关于GNU AGPL
GNU Affero General Public License（GNU AGPL）是 GNU General Public License（GNU GPL）的一个变体，专门用于网络服务器软件。它要求任何对基于 AGPL 许可的软件进行修改的人都需要公开源代码，包括对该软件的网络访问。这意味着如果您对本项目进行了修改并将其部署在网络服务器上，您需要公开您的修改并提供对源代码的访问。

## 主要条款
修改后的代码必须以相同的许可证发布： 任何基于本项目进行的修改必须以 GNU AGPL 许可证发布。
网络交互要求源代码访问： 如果用户通过网络与本项目进行交互，他们必须能够获取到项目的源代码。
商业使用
请注意，GNU AGPL 在商业使用方面有一些限制。在商业环境中使用本项目可能需要您深入了解 GNU AGPL 许可证的条款，并可能需要与您的法律顾问进行进一步沟通

## 附加说明
本项目的目的是鼓励开放的合作和知识共享。我们欢迎并鼓励社区的参与和贡献。如果您有任何疑问或希望参与本项目，请阅读我们的贡献指南

# Star History
<a href="https://github.com/Akimio521/AutoFilm/stargazers">
    <img width="500" alt="Star History Chart" src="https://api.star-history.com/svg?repos=Akimio521/AutoFilm&type=Date">
</a> 

# 请我喝杯咖啡吧
**如果你认为这个项目有帮到你，欢迎请我喝杯咖啡**
![欢迎请我喝咖啡](https://img.akimio.top/reward/coffee.png)
