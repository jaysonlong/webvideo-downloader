# webvideo-downloader

网站视频下载器，用于下载一些网站中可以在线播放的视频，当前支持bilibili（单P/多P），爱奇艺，腾讯视频，芒果TV的视频下载。

> **What you can watch determined what you can download.**
>
> 你只能下载你或你的账号可以在线观看的视频，本项目没有VIP破解功能。

## 🔨 Usage

本项目分为两部分，violentmonkey脚本用于在浏览器中提取视频链接，downloader程序负责视频文件的下载与合并。

### ViolentMonkey

1. Chrome浏览器安装 [Violenmonkey](https://violentmonkey.github.io/) 暴力猴插件或者其他浏览器类似插件，都差不多

2. 导入 `violentmonkey` 目录中的 [WebVideoDownloader.user.js](https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/WebVideoDownloader.user.js) 脚本。直接点击链接即可导入

- [暴力猴（Chrome）](https://chrome.google.com/webstore/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag)
- [WebVideoDownloader 脚本](https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/WebVideoDownloader.user.js)
- [AdGuard 广告拦截器（推荐安装）](https://chrome.google.com/webstore/detail/adguard-adblocker/bgnkhhnnamicmpeenaelnjfhikgbkllg)

3. 打开支持的视频网站，点击某个视频

4. 网页会自动弹出视频链接，点击链接远程调用下载器，或右键复制链接手动下载

   ![bilibili](img/bilibili.png)

### Downloader

本项目使用 [FFmpeg](https://ffmpeg.org/) 作为视频处理工具，windows版本已内置，linux下需自行安装。

- 远程调用下载时，先运行 `python daemon.py` 后，直接点击暴力猴弹出的链接即可，支持单视频下载、bilibili 多P下载和MSE视频流导出
- 手动复制链接下载时，先运行 `python common.py` ，再粘贴上面暴力猴解析到的视频链接即可，支持单视频下载、bilibili 多P下载和本地 m3u8 文件解析

