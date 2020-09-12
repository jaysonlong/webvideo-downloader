# -*- coding:utf-8 -*-
import os
import traceback
import config
import api
import tools
from tools import WebDownloader


class TaskDispatcher:
    
    def __init__(self):
        self.saveTempFile = config.saveTempFile
        self.hlsThreadCnt = config.hlsThreadCnt
        self.fragThreadCnt = config.fragThreadCnt
        self.fragmentCnt = config.fragmentCnt
        self.tempFilePath = tools.toAbsolutePath(config.tempFilePath, __file__)
        self.videoFilePath = tools.toAbsolutePath(config.videoFilePath, __file__)

        self.downloader = WebDownloader(self.saveTempFile)
        self.task = None

        tools.mkdirIfNotExists(self.tempFilePath)
        tools.mkdirIfNotExists(self.videoFilePath)
        tools.checkFFmpeg()
        tools.createRequestLogger(config.logPath, __file__)


    # hls: 下载所有ts分片并合并
    def _downloadHls(self, urls, fileName, headers = {}, concat = True):
        print("-- dispatcher/downloadHls")

        tempFileBase = os.path.join(self.tempFilePath, fileName)
        fileNames = tools.generateFileNames(urls, tempFileBase)
        targetFileName = os.path.join(self.videoFilePath, fileName + '.mp4')

        self.downloader.downloadAll(urls, fileNames, headers, self.hlsThreadCnt)
        tools.mergePartialVideos(fileNames, targetFileName, concat=concat)

        self.saveTempFile or tools.removeFiles(fileNames)
        return targetFileName

    # dash: 下载音频和视频并合并
    def _downloadDash(self, audioUrls, videoUrls, fileName, headers = {}):
        print("-- dispatcher/downloadDash")

        tempAudioBase = os.path.join(self.tempFilePath, fileName + '.audio')
        tempVideoBase = os.path.join(self.tempFilePath, fileName + '.video')
        audioNames = tools.generateFileNames(audioUrls, tempAudioBase)
        videoNames = tools.generateFileNames(videoUrls, tempVideoBase)
        targetFileName = os.path.join(self.videoFilePath, fileName + '.mp4')

        self.downloader.multiThreadDownloadAll(audioUrls, audioNames, headers, \
            self.fragThreadCnt, self.fragmentCnt)
        self.downloader.multiThreadDownloadAll(videoUrls, videoNames, headers, \
            self.fragThreadCnt, self.fragmentCnt)
        tools.mergeAudio2Video(audioNames, videoNames, targetFileName)

        self.saveTempFile or tools.removeFiles(audioNames + videoNames)
        return targetFileName

    # 普通分段视频: 下载并合并
    def _downloadPartialVideos(self, urls, fileName, headers = {}):
        print("-- dispatcher/downloadPartialVideos")

        tempFileBase = os.path.join(self.tempFilePath, fileName)
        fileNames = tools.generateFileNames(urls, tempFileBase)
        suffix = tools.getSuffix(urls[0])
        targetFileName = os.path.join(self.videoFilePath, fileName + suffix)

        for i, url in enumerate(urls):
            self.downloader.multiThreadDownload(url, fileNames[i], headers, \
                self.fragThreadCnt, self.fragmentCnt)
        tools.mergePartialVideos(fileNames, targetFileName)

        self.saveTempFile or tools.removeFiles(fileNames)
        return targetFileName

    # websocket视频流，保存至本地并合并
    def handleStream(self, fileName, audioFormat, videoFormat, **desc):
        print("-- dispatcher/handleStream")

        audioName = os.path.join(self.tempFilePath, fileName + '.audio' + audioFormat)
        videoName = os.path.join(self.tempFilePath, fileName + '.video' + videoFormat)
        targetFileName = os.path.join(self.videoFilePath, fileName + '.mp4')

        self.downloader.saveStream(audioName, videoName, **desc)
        tools.mergeAudio2Video([audioName], [videoName], fileName)

        self.saveTempFile or tools.removeFiles([audioName, videoName])
        print('完成\n')
        return targetFileName

    # 下载弹幕并集成到视频文件
    def handleSubtitles(self, subtitles, fileName, videoName, headers = {}):
        subtitleUrls, subtitleNames = [], []
        subtitlesInfo = []

        for name, url in subtitles:
            subtitleUrls.append(url)
            subtitleName = os.path.join(self.tempFilePath, '%s_%s%s' % \
                (fileName, name, tools.getSuffix(url)))
            subtitleNames.append(subtitleName)
            subtitlesInfo.append((name, subtitleName))

        self.downloader.downloadAll(subtitleUrls, subtitleNames, headers, self.hlsThreadCnt)

        for each in subtitleNames:
            tools.tryFixSrtFile(each)
        
        targetFileName = tools.integrateSubtitles(subtitlesInfo, videoName)
        self.saveTempFile or tools.removeFiles(subtitleNames)
        return targetFileName


    def download(self, linksurl, fileName):
        fileName = tools.escapeFileName(fileName)
        videoType, headers, audioUrls, videoUrls, subtitles = api.parseSingleUrl(linksurl)

        if audioUrls:
            print('匹配到%d段音频，%d段视频，开始下载' % (len(audioUrls), len(videoUrls)))
        else:
            print('匹配到%d段视频，开始下载' % len(videoUrls))

        targetFileName = ''
        if videoType == 'hls':
            # 存在字幕文件时，使用二进制合并以生成正确的时间戳
            concat = not bool(subtitles)
            targetFileName = self._downloadHls(videoUrls, fileName, headers, concat)
        elif videoType == 'dash':
            targetFileName = self._downloadDash(audioUrls, videoUrls, fileName, headers)
        elif videoType == 'partial':
            targetFileName = self._downloadPartialVideos(videoUrls, fileName, headers)

        if subtitles:
            print('匹配到%d个字幕，开始下载' % len(subtitles))
            self.handleSubtitles(subtitles, fileName, targetFileName, headers)

        print('完成\n')


    def downloadMultiParts(self, linksurl, baseFileName, pRange):
        startP, endP, allPartInfo = api.parseMultiPartUrl(linksurl, pRange)

        print('准备下载第%d-%dP\n' % (startP, endP))

        for i in range(startP-1, endP):
            partName, videoUrl = allPartInfo[i]['name'], allPartInfo[i]['videoUrl']
            fileName = 'P%03d__%s__%s' % (i + 1, baseFileName, partName)
            print('开始下载第%dP: %s' % (i + 1, fileName))
            self.download(videoUrl, fileName)

    def dispatch(self, **task):
        self.task = task
        task['type'] = task.get('type', 'link')
        print()

        try:
            if task['type'] == 'link':
                linksurl, fileName = task['linksurl'], task['fileName']
                if task.get('pRange'):
                    self.downloadMultiParts(linksurl, fileName, task['pRange'])
                else:
                    self.download(linksurl, fileName)
            elif task['type'] == 'stream':
                self.handleStream(**task)
        except Exception as e:
            print('-' * 100)
            traceback.print_exc()
            print('-' * 100)
        except KeyboardInterrupt:
            self.shutdown()
        finally:
            task['type'] == 'stream' and task['close']()
            self.task = None

    def shutdown(self):
        if self.task:
            task = self.task
            self.task = None

            if task['type'] == 'stream':
                task['dataQueue'].put(KeyboardInterrupt())
            self.downloader.shutdownAndClean()