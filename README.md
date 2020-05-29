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

4. 网页会自动弹出视频链接，右键复制链接地址，或直接点击链接远程调用

   ![bilibili](img/bilibili.png)

### Downloader

本项目使用 [FFmpeg](https://ffmpeg.org/) 作为视频处理工具，windows版本已内置，linux下需自行安装。

- 下载单个视频时，运行 `python common.py` ，粘贴上面暴力猴解析到的视频链接，然后输入保存的文件名即可
- 下载B站的多个分P时，运行 `python bilibiliMultiPart.py` ，粘贴暴力猴链接，输入文件名和首、尾P即可
- 远程调用时，先运行 `python daemon.py` 后，直接点击暴力猴弹出的链接即可，脚本自动识别为单个视频或多P

