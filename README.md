# webvideo-downloader

![](https://img.shields.io/badge/platform-win%20%7C%20linux%20%7C%20osx-brightgreen) ![](https://img.shields.io/badge/python-%3E=%203.5.0-orange)

🚀 视频下载器，用于下载网站中可以在线播放的视频。

---

**主要支持的视频网站：**

- [哔哩哔哩](https://www.bilibili.com/)（单P/多P）
- [爱奇艺](https://www.iqiyi.com/)
- [腾讯视频](https://v.qq.com/)
- [芒果TV](https://www.mgtv.com/)
- [WeTV](https://wetv.vip/)
- [愛奇藝台灣站](https://tw.iqiyi.com//)

此外，可选的 `CommonHlsDownloader` 脚本支持绝大部分基于 HLS 流式视频的网站，如 [LPL官网](https://lpl.qq.com/) 等。

---

**本项目支持1080p蓝光画质、VIP专享、VIP点播、付费视频的下载，前提为你是VIP/用了券/付了费。**

> **What you can watch determined what you can download.**
>
> 你只能下载你或你的账号可以在线观看的视频，本项目没有VIP破解功能。



## 🔨 Usage

本项目分为两部分，**violentmonkey** 脚本用于在浏览器中提取视频链接，**downloader** 程序负责视频文件的下载与合并。

### Violentmonkey

1. Chrome或其他浏览器安装 [Violenmonkey](https://violentmonkey.github.io/) 暴力猴插件，或者 [Tampermonkey](http://www.tampermonkey.net/) 插件

2. 安装 `violentmonkey` 目录中的 [WebVideoDownloader.user.js](https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/WebVideoDownloader.user.js) 脚本。直接点击以下链接即可安装

- [暴力猴（Chrome）](https://chrome.google.com/webstore/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag)
- [WebVideoDownloader 脚本](https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/WebVideoDownloader.user.js)
- [广告拦截器](https://chrome.google.com/webstore/detail/adguard-adblocker/bgnkhhnnamicmpeenaelnjfhikgbkllg)（可选。存在广告时，脚本**可能**会延迟到广告即将结束时才开始解析）
- [CommonHlsDownloader 脚本](https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/CommonHlsDownloader.user.js)（可选。通用 HLS 下载脚本，作用于**所有**使用 HLS 的网站）

3. 打开支持的视频网站，点击某个视频

4. 网页自动弹出下载按钮，点击打开对话框，然后点击链接远程创建下载任务，或复制链接后手动粘贴下载

   ![bilibili](img/bilibili.gif)

### Downloader

> 本下载程序使用 [FFmpeg](https://ffmpeg.org/) 作为视频处理工具，windows 版本已内置到仓库，linux/mac 下需自行安装。

远程调用下载器（支持单视频下载、哔哩哔哩多P下载和 MSE 视频流导出）

```bash
python daemon.py
```

手动复制链接粘贴（支持单视频下载、哔哩哔哩多P下载和本地 m3u8 文件解析下载）

```bash
python common.py
```

可选命令行参数

```
usage: daemon.py / common.py [-h] [-s] [-t:h N] [-t:f N] [-f N]

optional arguments:
  -h, --help  show this help message and exit
  -s          if set, will not delete the temp files
  -t:h N      the thread count of hls download, default 16
  -t:f N      the thread count of fragments download, default 16
  -f N        the fragments count of each file, default 0 using the thread
              count
```


