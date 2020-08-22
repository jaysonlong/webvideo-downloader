# -*- coding:utf-8 -*-
import time
import math
from concurrent.futures import ThreadPoolExecutor
from requests.exceptions import RequestException
from . import utils


CLIENT_CLOSE_EXCEPTION = Exception('Connection closed')

# 自定义线程池
class MyThreadPool(ThreadPoolExecutor):

    def reset(self, max_workers=None):
        self._max_workers = max_workers
        self.allTask = []
        self.doneCnt = 0
        self.exception = None
        self.taskCallbacks = []
        return self

    def _cancelAll(self):
        for task in self.allTask:
            task.cancel()

    # 出现异常自动取消所有任务
    def _onTaskFinish(self, task):
        if not task.cancelled() and task.exception():
            self.exception = task.exception()
            self._cancelAll()

        for callback in self.taskCallbacks:
            callback()
        self.doneCnt += 1

    def addTaskCallBack(self, callback):
        self.taskCallbacks.append(callback)

    def submit(self, fn, *args, **kwargs):
        task = ThreadPoolExecutor.submit(self, fn, *args, **kwargs)
        task.add_done_callback(self._onTaskFinish)
        self.allTask.append(task)
        return task

    # 等待任务完成，且所有回调函数也执行完成
    def isAlive(self):
        return self.doneCnt < len(self.allTask)



class WebDownloader:

    historySize = 5
    chunkSize = 1024 * 30
    barLength = 50

    def __init__(self, saveTempFile = False):
        self.saveTempFile = saveTempFile
        self.threadPool = MyThreadPool()

    def _reset(self, downloadFiles, totalSize, percent = None):
        self.downloadFiles = downloadFiles
        self.totalSize = totalSize
        self.currSize = 0
        # percent为None时，由currSize和totalSize自动计算生成
        self.percent = percent
        self.history = [0 for i in range(self.historySize)]
        self.startTime = time.time()
        self.failedSize = 0
        self.hasWarned = False

    # 更新下载进度
    def _updateProgress(self):
        if self.threadPool.exception or self.totalSize == 0:
            return

        percent = self.percent if isinstance(self.percent, float) else (self.currSize/self.totalSize)
        barStr = ('#' * int(percent * self.barLength)).ljust(self.barLength, ' ')
        percent = int(percent * 100)

        currSize = utils.toMB(self.currSize)
        totalSize = self.totalSize
        totalSize = utils.toMB(totalSize) if isinstance(totalSize, int) else totalSize
        progress = '%12s' % ('%s/%sMB' % (currSize, totalSize))

        self.history.append(self.currSize)
        self.history.pop(0)
        averSize = (self.history[-1] - self.history[0]) / (self.historySize - 1)
        speed = utils.formatSize(int(averSize * 2))
        usedTime = utils.formatTime(time.time() - self.startTime)

        print("\r进度: \033[92m[%s]\033[0m %2d%% %s %6s/s %s  " % (
            barStr, percent, progress, speed, usedTime
        ), end='')

    # 非阻塞等待下载完成，并实时更新下载进度
    def _waitUtilFinish(self):
        while self.threadPool.isAlive():
            time.sleep(0.5)
            self._updateProgress()
        print() 

        if self.threadPool.exception:
            self.saveTempFile or utils.removeFiles(self.downloadFiles)
            raise self.threadPool.exception

    # 通用下载，支持指定range
    def _downloadRange(self, url, fileName, headers, start = 0, end = None):
        utils.touchIfNotExists(fileName)

        with open(fileName, 'rb+') as f:
            f.seek(start)
            headers = headers.copy()
            end = ('%d' % end) if isinstance(end, int) else ''
            downloadedSize = 0
            rangeSize = None
            response = None

            while True:
                try:
                    headers['Range'] = 'bytes=%d-%s' % (start + downloadedSize, end)
                    response = utils.request("GET", url, headers=headers, stream=True)
                    rangeSize = rangeSize or int(response.headers['Content-Length'])

                    if response.status_code != 206 and not (start == 0 and end == ''):
                        raise Exception('服务器不支持Range请求')

                    for chunk in response.iter_content(self.chunkSize):
                        if self.threadPool.exception:
                            raise self.threadPool.exception
                        f.write(chunk)
                        downloadedSize += len(chunk)
                        self.currSize += len(chunk)

                    if downloadedSize < rangeSize:
                        continue
                    else:
                        break
                except RequestException:
                    if response and response.status_code != 206:
                        f.seek(start)
                        self.currSize -= downloadedSize
                        self.failedSize += downloadedSize
                        downloadedSize = 0

                        if not self.hasWarned and self.failedSize > self.currSize * 0.5:
                            self.hasWarned = True
                            print('\n\033[93m警告: 当前下载失败几率较高，且服务器不支持断点续传，' \
                                + '可尝试降低下载线程数量以提高下载速度，命令行参数: -t:h N\033[0m')

    def directDownload(self, url, fileName, headers):
        self._reset(fileName, utils.getFileSize(url, headers))
        self.threadPool.reset(max_workers=1)
        self.threadPool.submit(self._downloadRange, url, fileName, headers)
        print('正在下载', fileName)
        self._waitUtilFinish()

    def downloadAll(self, urls, fileNames, headers, threadCnt):
        totalCnt = len(urls)
        finishedCnt = 0
        self._reset(fileNames, '-', 0.0)

        def onFinish():
            nonlocal finishedCnt
            finishedCnt += 1
            self.percent = finishedCnt / totalCnt

        self.threadPool.reset(max_workers=threadCnt)
        self.threadPool.addTaskCallBack(onFinish)
        for i, url in enumerate(urls):
            self.threadPool.submit(self._downloadRange, url, fileNames[i], headers)

        print('并行%d线程下载' % threadCnt)
        self._waitUtilFinish()

    def multiThreadDownload(self, url, fileName, headers, threadCnt, fragmentCnt):
        self._reset(fileName, utils.getFileSize(url, headers))
        fragmentCnt = max(threadCnt, fragmentCnt)
        fragmentSize = math.ceil(self.totalSize / fragmentCnt)
        
        self.threadPool.reset(max_workers=threadCnt)
        for i in range(fragmentCnt):
            start, end = fragmentSize * i, fragmentSize * (i + 1) - 1
            self.threadPool.submit(self._downloadRange, url, fileName, headers, start, end)

        print('正在下载', fileName)
        print('分%d段, 并行%d线程下载' % (fragmentCnt, threadCnt))
        self._waitUtilFinish()

    def multiThreadDownloadAll(self, urls, fileNames, headers, threadCnt, fragmentCnt):
        if len(urls) == 1:
            self.multiThreadDownload(urls[0], fileNames[0], headers, threadCnt, fragmentCnt)
            return

        fragmentCnt = max(threadCnt, fragmentCnt)
        fileSizes = [utils.getFileSize(url, headers) for url in urls]
        fragmentSizes = [math.ceil(fileSize / fragmentCnt) for fileSize in fileSizes]
        self._reset(fileNames, sum(fileSizes))

        self.threadPool.reset(max_workers=threadCnt)
        for i, url in enumerate(urls):
            for j in range(fragmentCnt):
                start, end = fragmentSizes[i] * j, fragmentSizes[i] * (j + 1) - 1
                self.threadPool.submit(self._downloadRange, url, fileNames[i], headers, start, end)

        print('分%dx%d段, 并行%d线程下载' % (len(urls), fragmentCnt, threadCnt))
        self._waitUtilFinish()

    def saveStream(self, audioName, videoName, duration, startTime, dataQueue, **extra):
        def startSaving():
            audioFile, videoFile = None, None

            while True:
                data = dataQueue.get()
                if data is None:
                    continue
                elif isinstance(data, BaseException):
                    if data == CLIENT_CLOSE_EXCEPTION:
                        break
                    raise data
                elif data['type'] == 'video':
                    videoFile = videoFile or open(videoName, 'wb')
                    videoFile.write(data['chunk'])
                elif data['type'] == 'audio':
                    audioFile = audioFile or open(audioName, 'wb')
                    audioFile.write(data['chunk'])
                elif data['type'] == 'finish':
                    self.percent = 1.0
                    break
                else:
                    continue
                self.percent = min(1.0, abs(data['endPoint']-startTime) / (duration-startTime))
                self.currSize += len(data['chunk'])

            audioFile and audioFile.close()
            videoFile and videoFile.close()

        self._reset([audioName, videoName], '-', 0.0)
        self.threadPool.reset(max_workers=1)
        self.threadPool.submit(startSaving)

        print('正在传输视频流')
        self._waitUtilFinish()

    def shutdownAndClean(self):
        print('\nShutting down...')

        self.threadPool.exception = KeyboardInterrupt()
        while self.threadPool.isAlive():
            time.sleep(0.5)
        self.saveTempFile or utils.removeFiles(self.downloadFiles)

        print('Shutting down finished\n')