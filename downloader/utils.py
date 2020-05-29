# -*- coding:utf-8 -*-
import os
import requests
import threading
import time
import sys
from pathlib import Path

dlInfo = {
    'totalSize': 0,
    'currSize': 0,
    'sizeHistory': [],
    'startTime': 0,
}

userAgent = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
}

# 多线程并行数量控制
class MyThread(threading.Thread):
    threadSemaphore = threading.Semaphore(1)

    def __init__(self, target, args):
        threading.Thread.__init__(self)
        self.target = target
        self.args = args

    @classmethod
    def setParallelCount(cls, parallelCount):
        MyThread.threadSemaphore = threading.Semaphore(parallelCount)

    def run(self):
        with MyThread.threadSemaphore:
            self.target(*self.args)

def parseUrl(url):
    path, suffix = url.rsplit('/', 1)
    suffix = suffix.split('?')[0]
    return path + '/', suffix

def toAbsolutePath(path):
    path = str(Path(path))
    if path == str(Path(path).absolute()):
        return path
    else:
        scriptPath = os.path.split(os.path.abspath(__file__))[0]
        return os.path.join(scriptPath, str(Path(path)))

def ensureDir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def removeFiles(fileNames):
    if isinstance(fileNames, str):
        fileNames = [fileNames]

    for fileName in fileNames:
        if os.path.exists(fileName):
            os.remove(fileName)

def toMB(size):
    return '%.1f' % (size / 1024 / 1024)

def formatSize(size):
    if size < 1024 * 1024:
        return '%dKB' % (size // 1024)
    else:
        return '%.1fMB' % (size / 1024 / 1024)

def formatTime(value):
    value = int(value)
    if value < 60:
        return '%ds' % value
    else:
        return '%2dmin%02ds' % (value // 60, value % 60)

def mergeDict(dst, src):
    for key in src:
        dst[key] = src[key]
    return dst

def request(*args, **kargs):
    response = requests.request(*args, **kargs)
    if response.status_code > 299:
        print(response.status_code, '错误')
        exit()
    return response

def getText(url, extraHeaders = {}):
    if not url.startswith('http'):
        with open(url) as f:
            return f.read()

    headers = mergeDict(userAgent, extraHeaders)
    response = request('GET', url, headers=headers)
    return response.text

def resetDownloadInfo(totalSize):
    dlInfo['totalSize'] = totalSize
    dlInfo['currSize'] = 0
    dlInfo['sizeHistory'] = [0 for i in range(5)]
    dlInfo['startTime'] = time.time()

# 打印下载进度
def updateProgress(percent = None, barLength = 50):
    if percent is None:
        if dlInfo['totalSize'] == 0:
            # 响应头尚未获取，未设置totalSize
            return
        percent = dlInfo['currSize'] / dlInfo['totalSize']
        currSize, totalSize = toMB(dlInfo['currSize']), toMB(dlInfo['totalSize'])
    else:
        currSize, totalSize = toMB(dlInfo['currSize']), '-'

    sizeHistory = dlInfo['sizeHistory']
    sizeHistory.append(dlInfo['currSize'])
    sizeHistory.pop(0)

    hashLength = int(percent * barLength)
    bar = '#' * hashLength + ' ' * (barLength - hashLength)
    percent = int(percent * 100)
    progress = '%12s' % ('%s/%sMB' % (currSize, totalSize))
    speed = formatSize((sizeHistory[4] - sizeHistory[0]) // 2)
    usedTime = formatTime(time.time() - dlInfo['startTime'])

    sys.stdout.write("\r进度: \033[40;32m[%s]\033[0m %2d%% %s %6s/s %s  " % (
        bar, percent, progress, speed, usedTime
    ))
    sys.stdout.flush()

def download(url, fileName, extraHeaders = {}):
    headers = mergeDict(userAgent, extraHeaders)
    
    def startDownload():
        response = request("GET", url, headers=headers, stream=True, timeout=10)

        resetDownloadInfo(int(response.headers['Content-Length']))
        print('正在下载', fileName)

        try:
            with open(fileName, 'wb') as fd:
                for chunk in response.iter_content(10240):
                    fd.write(chunk)
                    dlInfo['currSize'] += len(chunk)
        except Exception as e:
            print('\n下载失败: %s，重新下载' % str(e))
            time.sleep(1)
            startDownload()

    # 另起线程下载
    t = threading.Thread(target=startDownload)
    t.setDaemon(True)
    t.start()

    # 统计下载速度
    while t.isAlive():
        time.sleep(0.5)
        updateProgress()

    print()

def downloadAll(urls, fileNames, extraHeaders = {}, parallelCount = 2):
    headers = mergeDict(userAgent, extraHeaders)

    totalCount = len(urls)
    currCount = 0
    downloadedSize = [0 for i in range(totalCount)]

    # 下载函数
    def startDownload(i):
        nonlocal currCount
        try:
            response = request("GET", urls[i], headers=headers, stream=True, timeout=10)

            downloadedSize[i] = 0
            with open(fileNames[i], 'wb') as fd:
                for chunk in response.iter_content(10240):
                    fd.write(chunk)
                    downloadedSize[i] += len(chunk)

            currCount += 1
        except Exception as e:
            print('\n第%d段下载失败: %s，重新下载' % (i+1, str(e)))
            time.sleep(1)
            startDownload(i)

    resetDownloadInfo('-')
    MyThread.setParallelCount(parallelCount)

    threadList = []
    for i in range(len(urls)):
        t = MyThread(target=startDownload, args=(i, ))
        t.setDaemon(True)
        t.start()
        threadList.append(t)

    # 统计下载速度
    for t in threadList:
        while t.isAlive():
            time.sleep(0.5)
            dlInfo['currSize'] = sum(downloadedSize)
            percent = currCount / totalCount
            updateProgress(percent)

    print()

def downloadRange(url, headers, downloadedData, downloadedSize, threadIndex):
    try:
        response = request("GET", url, headers=headers, stream=True, timeout=10)

        bytesdata = b''
        downloadedSize[threadIndex] = 0
        for chunk in response.iter_content(10240):
            bytesdata += chunk
            downloadedSize[threadIndex] += len(chunk)

        downloadedData[threadIndex] = bytesdata
    except Exception as e:
        print('\n线程%d下载失败: %s，重新下载' % (threadIndex + 1, str(e)))
        time.sleep(1)
        downloadRange(url, headers, downloadedData, downloadedSize, threadIndex)

def multiThreadDownload(url, fileName, extraHeaders = {}, threadCount = 16, parallelCount = None):
    headers = mergeDict(userAgent, extraHeaders)
    response = request("HEAD", url, headers=headers)

    resetDownloadInfo(int(response.headers['Content-Length']))
    segmentSize = (dlInfo['totalSize'] + threadCount - 1) // threadCount
    downloadedData = [b'' for i in range(threadCount)]
    downloadedSize = [0 for i in range(threadCount)]

    parallelCount = parallelCount or threadCount
    MyThread.setParallelCount(parallelCount)

    print('正在下载', fileName)
    print('分%d线程, 并行%d线程下载' % (threadCount, parallelCount))

    threadList = []
    for i in range(threadCount):
        start, end = segmentSize * i, segmentSize * (i + 1) - 1
        subHeaders = headers.copy()
        subHeaders['Range'] = 'bytes=%d-%d' % (start, end)
        t = MyThread(target=downloadRange, args=(url, subHeaders, downloadedData, downloadedSize, i))
        t.setDaemon(True)
        t.start()
        threadList.append(t)

    # 统计下载速度
    for t in threadList:
        while t.isAlive():
            time.sleep(0.5)
            dlInfo['currSize'] = sum(downloadedSize)
            updateProgress()

    with open(fileName, 'wb') as f:
        for data in downloadedData:
            f.write(data)

    print()

def mergePartialVideos(subfiles, fileName, delSilent):
    # 这一行没毛病
    text = "file '" + ("'\nfile '".join(subfiles)) + "'" 
    with open('concat.txt', 'w') as f:
        f.write(text)

    cmd = 'ffmpeg -safe 0 -f concat -i concat.txt -c copy "%s"' % (fileName)
    os.system(cmd)
    removeFiles('concat.txt')

    delete = delSilent or input('是否删除临时文件(Y/n):').lower() == 'y'
    delete and removeFiles(subfiles)

def mergeAudio2Video(videoName, audioName, fileName, delSilent):
    cmd = 'ffmpeg -i "%s" -i "%s"  -c copy "%s"' % (audioName, videoName, fileName)
    os.system(cmd)

    delete = delSilent or input('是否删除临时文件(Y/n):').lower() == 'y'
    delete and removeFiles([audioName, videoName])
