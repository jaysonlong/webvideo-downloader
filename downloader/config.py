# -*- coding:utf-8 -*-
import tools


args = tools.getArguments({
    'name': '-s',
    'action': 'store_true', 
    'help': 'if set, will not delete the temp files',
}, {
    'name': '-t:h',
    'metavar': 'N',
    'type': int,
    'default': 16,
    'help': 'the thread count of hls download, default 16',
}, {
    'name': '-t:f',
    'metavar': 'N',
    'type': int,
    'default': 16,
    'help': 'the thread count of fragments download, default 16',
}, {
    'name': '-f',
    'metavar': 'N',
    'type': int,
    'default': 0,
    'help': 'the fragments count of each file, default 0 using the thread count',
})

# 是否保留下载的临时文件
saveTempFile = getattr(args, 's')

# hls下载线程数
hlsThreadCnt = getattr(args, 't:h')

# 分段下载线程数
fragThreadCnt = getattr(args, 't:f')

# 分段下载的分段数
fragmentCnt = getattr(args, 'f')

# 临时文件保存路径
tempFilePath = "../temp/"

# 视频文件保存路径
videoFilePath = "../videos/"

# 日志保存路径
logPath = './logs/'
