# -*- coding:utf-8 -*-
import tools


args = tools.getArguments({
    'name': '-t:h',
    'metavar': 'N',
    'type': int,
    'default': 8,
    'help': 'the thread count of hls download, default 8',
}, {
    'name': '-t:f',
    'metavar': 'N',
    'type': int,
    'default': 8,
    'help': 'the thread count of fragments download, default 8',
}, {
    'name': '-f',
    'metavar': 'N',
    'type': int,
    'default': 0,
    'help': 'the fragments count of each file, default 0 using the thread count',
}, {
    'name': '-p',
    'metavar': 'PORT',
    'type': int,
    'default': 18888,
    'help': 'the port that the backend server listens on, default 18888',
}, {
    'name': ['-c', '--correct'],
    'action': 'store_true', 
    'help': 'correct the timestamp of hls video, merge fragments using binnary mode',
}, {
    'name': '-s',
    'action': 'store_true', 
    'help': 'if set, will save the temp files',
}, {
    'name': '-d',
    'action': 'store_true', 
    'help': 'debug mode, log more info and save the temp files (ignore -s)',
}, {
    'name': '-i',
    'action': 'store_true', 
    'help': 'interactive mode, get url and file name from the command line',
})


# hls下载线程数
hlsThreadCnt = getattr(args, 't:h')

# 分段下载线程数
fragThreadCnt = getattr(args, 't:f')

# 分段下载的分段数
fragmentCnt = getattr(args, 'f')

# 守护模式下服务器监听的端口
port = getattr(args, 'p')

# 是否校正hls视频时间戳
correctTimestamp = getattr(args, 'correct')

# 调试模式
debug = getattr(args, 'd')

# 是否保留下载的临时文件，debug模式下忽略该选项
saveTempFile = debug or getattr(args, 's')

# 交互模式
interactive = getattr(args, 'i')

# 临时文件保存路径
tempFilePath = "../temp/"

# 视频文件保存路径
videoFilePath = "../videos/"

# 日志保存路径
logPath = './logs/'
