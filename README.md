# webvideo-downloader

网站视频下载器，用于下载一些网站中可以在线播放的视频，当前支持bilibili（单P/多P），爱奇艺，腾讯视频，芒果TV的视频下载。

> **What you can watch determined what you can download.**
>
> 你只能下载你或你的账号可以在线观看的视频，本项目没有VIP破解功能。

## 🔨 Usage

本项目分为两部分，violentmonkey脚本用于在浏览器中提取视频链接，downloader程序负责视频文件的下载与合并。

### ViolentMonkey

1. Chrome浏览器安装 `ViolentMonkey` 插件或者其他浏览器类似插件，都一样

2. 导入 `violentmonkey` 目录中的 `WebVideoDownloader.user.js` 脚本。直接点击以下链接即可导入
- [网站视频下载器](https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/WebVideoDownloader.user.js)

3. 打开相对应的视频网站，点击某一个视频

4. 网页会自动弹出视频链接的窗口，右键复制链接地址即可

   ![bilibili](img/bilibili.png)

### Downloader

- 下载单个视频时，运行 `python common.py` ，粘贴上面暴力猴解析到的视频链接，然后输入保存的文件名即可

- 下载B站的多个分P时，运行 `python bilibiliMultiPart.py` ，粘贴暴力猴链接，输入文件名和首、尾P即可

