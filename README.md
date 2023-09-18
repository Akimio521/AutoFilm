# AutoFilm
**一个为Emby服务器提供直链播放的小项目**

## 优点
- [x] 轻量化Emby服务器，降低Emby服务器的性能需求以及硬盘需求
- [x] 运行稳定
- [x] 相比直接访问Webdav，Emby服务器可以提供更好的视频搜索功能以及自带刮削器，以及多设备同步播放进度
- [x] 提高访问速度，播放速度不受Emby服务器带宽限制
- [x] Github Workflows自动下载打包上传至Release

## Todo LIST
- [ ] 增加更多Webdav服务器的支持
- [ ] 对接TMDB实现分类、重命名、刮削等功能
- [ ] 从config文件中读取多个参数

## 使用教程
这里以Windows为例(Linux参考)：

### 安装Python
在微软商店搜索`python`,选择`python3`（小版本任选）

### 安装webdav3.client
打开命令行输入以下命令：
```
pip install webdavclient3
```

## 下载Python文件
下载仓库的`autofil.py`文件，并在本地目录打开

## 查看使用方法
在当前目录打开终端（命令行），输入以下命令以查看使用方法：
```
python3 .\autofilm.py -h
```

### 运行：
```
python3 .\autofilm.py --webdav_url webdav服务器地址 --username webdav账号 --password webdav密码 --output_path 输出文件目录
```
示例：我的Alist地址为`https://alist.example.com:666`，我要下载`/视频/动漫/`里面的视频，下载路径在`D盘电影文件夹中的动漫文件夹`，我的Alist的访问账号的`myAlist`，密码是`listpwd`
```
python3 .\autofilm.py --webdav_url https://alist.example.com:666/dav/视频/动漫/ --username myAlist --password Alistpwd  --output_path D:电影//动漫//
```

### 其他参数
- **subtitle**：是否下载字幕文件，默认`true`
- **nfo**：是否下载NFO文件，默认`false`
- **img**：是否下载JPG和PNG图片文件，默认`false`

## 实现思路
我的NAS上搭建了Alist和Emby两个服务器，我的音乐库在阿里云盘上，最开始是利用Alist挂载阿里云盘然后Rclone到本地挂载到Emby上，但是每次Emby扫库时，NAS的运行压力就会变大，而且观看体验并不好

在浏览博客间偶然发现Emby可以利用`strm`文件代替视频文件，于是有了这个仓库，Emby会访问`strm`文件，其中有视频源文件的播放地址，Emby服务器就会把这个地址发给客户端让客户端让客户端自行尝试播放

整个python程序的结构很简单，打开对应的Webdav服务器，遇到`MP4`,`MKV`,`FLV`,`AVI`视频文件就在对应本地文件夹输出一个同名`strm`文件，其内容为视频的链接，其中Alist需要关闭签名，关闭签名后，直链需要把URL中的`/dav/`改为`/d/`；如果遇到`ASS`,`SRT`,`SSA`字幕文件或`JPG`刮削图像或`NFO`视频信息文件就直接下载到对应文件夹中，方便Emby的视频读取

至此，整个AutoFilm输出文件夹就可以代替原本的Emby视频媒体库了，如果Alist开启了302重定向，Emby客户端会跳转访问阿里云盘的地址，因此访问速度与Alist和Emby服务器完全不相干，如果NAS是采用CloudFlare进行内网穿透的话，播放效果也不再受到影响

## 鸣谢
感谢[七米蓝](https://github.com/ChirmyRam/ChirmyRam-OneDrive-Repository)分享Alist，为本项目的Workflows提供视频源

## 请我喝杯咖啡吧
**如果你认为这个项目有帮到你，欢迎请我喝杯咖啡**
![欢迎请我喝咖啡](https://img.shizu.eu.org/2023/09/1694935115/6506a84bcbaff.webp)
