# webvideo-downloader

![](https://img.shields.io/badge/platform-win%20%7C%20linux%20%7C%20osx-brightgreen) ![](https://img.shields.io/badge/python-%3E=%203.5.0-orange)

🚀 视频下载器，用于下载网站中可以在线播放的视频。

---

## 支持的网站

| 站点                                | URL                                                    | 普通画质 | VIP专属 |
| ------------------------------------- | ------------------------------------------------------ | -------- | ------- |
| 哔哩哔哩（单P/多P）                   | [https://www.bilibili.com/](https://www.bilibili.com/) | ✓        | ✓       |
| 爱奇艺     | [https://www.iqiyi.com/](https://www.iqiyi.com/)                       | ✓        | ✓       |
| 腾讯视频         | [https://v.qq.com/](https://v.qq.com/)                          | ✓        | ✓       |
| 芒果TV       | [https://www.mgtv.com/](https://www.mgtv.com/)                        | ✓        | ✓       |
| WeTV             | [https://wetv.vip/](https://wetv.vip/)                              | ✓        | ✓ |
| 愛奇藝台灣站 | [https://tw.iqiyi.com/](https://tw.iqiyi.com/)                  | ✓        | ✓       |
| 爱奇艺国际站   | [https://www.iq.com/](https://www.iq.com/)                    | ✓        | untested |

此外，可选的 [CommonHlsDownloader](https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/CommonHlsDownloader.user.js) 脚本支持绝大部分基于 HLS 流式视频的网站，如 [LPL官网](https://lpl.qq.com/) 等。



## 下载特性

### 基本特性

- 跨平台支持（Windows /Linux/Mac）
- 多线程下载（单文件分段/多文件并行）
- 字幕下载和集成（集成字幕的视频需使用支持字幕的播放器播放，如 `PotPlayer`，`VLC Player` 等）

### 关于VIP

本项目支持**1080p蓝光画质、VIP专享、VIP点播、付费视频**的下载，前提是你是VIP/用了券/付了费。

> **What you can watch determined what you can download.**
>
> 你只能下载你或你的账号可以在线观看的视频，本项目没有VIP破解功能。



## 🔨 快速开始

本项目分为两部分，**violentmonkey** 脚本用于在浏览器中提取视频链接，**downloader** 程序负责视频文件的下载与合并。

### Violentmonkey

1. 浏览器安装 [Violenmonkey](https://violentmonkey.github.io/) 暴力猴插件或 [Tampermonkey](http://www.tampermonkey.net/) 插件

- [暴力猴（Chrome）](https://chrome.google.com/webstore/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag)

2. 安装 `violentmonkey` 目录中的 [WebVideoDownloader.user.js](https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/WebVideoDownloader.user.js) 脚本

- [WebVideoDownloader 脚本](https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/WebVideoDownloader.user.js)
- [CommonHlsDownloader 脚本](https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/CommonHlsDownloader.user.js)（可选。通用 HLS 下载脚本，作用于**所有**使用 HLS 的网站）
- [广告拦截器](https://chrome.google.com/webstore/detail/adguard-adblocker/bgnkhhnnamicmpeenaelnjfhikgbkllg)（可选。存在广告时，脚本**可能**会延迟到广告即将结束时才开始解析）

3. 打开支持的视频网站，点击某个视频

4. 网页自动弹出下载按钮，点击打开对话框，然后点击链接远程创建下载任务，或复制链接后手动粘贴下载

   ![bilibili](img/bilibili.gif)

### Downloader

> 本下载程序使用 [FFmpeg](https://ffmpeg.org/) 作为视频处理工具，windows 版本已内置到仓库，linux/mac 下需自行安装。

#### 运行脚本（二选一）

```bash
# 选项1: 用于点击链接远程调用下载
python daemon.py

# 选项2: 用于手动复制链接下载
python common.py
```

#### 可选命令行参数

```bash
usage: daemon.py / common.py [-h] [-s] [-t:h N] [-t:f N] [-f N] [-d]

optional arguments:
  -h, --help  show this help message and exit
  -s          if set, will save the temp files
  -t:h N      the thread count of hls download, default 8
  -t:f N      the thread count of fragments download, default 8
  -f N        the fragments count of each file, default 0 using the thread count
  -d          debug mode, log more info and save the temp files (ignore -s)
```



## 更新日志

### [v1.6] - 2020-09-12

#### 新增

- 支持爱奇艺国际站视频下载
- 支持多个字幕文件集成到视频中

### [v1.5] - 2020-09-01

#### 新增

- 支持 WeTV，愛奇藝台灣站视频下载
- 支持部分网站字幕文件集成到视频中
- 下载文件完整性检查
- 暴力猴脚本 font-awesome 图标预加载

#### 变更

- MP4 文件 moov box 前置，便于网络传输

### [v1.4] - 2020-06-30

#### 变更

- 守护模式运行时端口复用，其监听模式同时支持 HTTP Server 和 WebSocket
- 暴力猴脚本可自定义远程调用模式（HTTP 或 WebSocket）

### [v1.3] - 2020-06-27

#### 变更

- 暴力猴脚本重构 & 界面重写

### [v1.2] - 2020-06-18

#### 新增

- 支持爱奇艺 MPD 格式文件解析
- 支持 MSE 视频流通过 WebSocket导出（实验性）
- 新增两个暴力猴脚本：通用 hls 下载脚本和 MSE 视频流导出脚本（实验性）
- 命令行参数支持

#### 变更

- 守护模式运行时的监听模式由 HTTP Server 更改为 WebSocket 
- 哔哩哔哩多P下载的 python 脚本并入到通用的 python 下载脚本中

### [v1.1] - 2020-05-29

#### 新增

- 支持基于 HTTP Server 以守护模式运行，浏览器点击链接直接调用后台下载

#### 变更

- 合并4个网站脚本为单个，便于安装和管理

### [v1.0] - 2020-05-26

#### 新增

- 支持哔哩哔哩、爱奇艺、腾讯视频、芒果TV视频下载（手动复制链接粘贴）
  
[v1.6]: https://github.com/jaysonlong/webvideo-downloader/compare/v1.5...v1.6
[v1.5]: https://github.com/jaysonlong/webvideo-downloader/compare/v1.4...v1.5
[v1.4]: https://github.com/jaysonlong/webvideo-downloader/compare/v1.3...v1.4
[v1.3]: https://github.com/jaysonlong/webvideo-downloader/compare/v1.2...v1.3
[v1.2]: https://github.com/jaysonlong/webvideo-downloader/compare/v1.1...v1.2
[v1.1]: https://github.com/jaysonlong/webvideo-downloader/compare/v1.0...v1.1
[v1.0]: https://github.com/jaysonlong/webvideo-downloader/releases/tag/v1.0
