# AutoFilm
**一个为Emby、Jellyfin服务器提供直链播放的小项目**

## 优点
- [x] 轻量化Emby服务器，降低Emby服务器的性能需求以及硬盘需求
- [x] 运行稳定
- [x] 相比直接访问Webdav，Emby、Jellyfin服务器可以提供更好的视频搜索功能以及自带刮削器，以及多设备同步播放进度
- [x] 提高访问速度，播放速度不受Jellyfin服务器带宽限制
## TODO LIST
- [x] Github Workflows自动下载打包上传至Release
- [x] 从config文件中读取多个参数
- [ ] 优化程序运行效率
- [ ] 对接TMDB实现分类、重命名、刮削等功能


## 关于开发
本项目采用`main`分支为稳定版、`Dev`分支为开发版，建议Fork`Dev`分支，提交Pr也建议提交到`Dev`分支，`main`分支不定期同步`Dev`分支进度，如果`Dev`分支中有`TEST`字样的Commit，则代表在测试中，二次开发时建议reset回上一个分支中

## 使用教程
详情见[Akimio的博客](https://blog.akimio.top/post/1031/#使用教程)
## 鸣谢
感谢[七米蓝](https://github.com/ChirmyRam/ChirmyRam-OneDrive-Repository)分享Alist，为本项目的Workflows提供视频源

## Star History
<a href="https://github.com/Akimio521/AutoFilm/stargazers">
    <img width="500" alt="Star History Chart" src="https://api.star-history.com/svg?repos=Akimio521/AutoFilm&type=Date">
</a> 

## 请我喝杯咖啡吧
**如果你认为这个项目有帮到你，欢迎请我喝杯咖啡**
![欢迎请我喝咖啡](https://img.akimio.top/reward/coffee.png/)
