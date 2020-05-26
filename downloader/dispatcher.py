# -*- coding:utf-8 -*-
import re
import json
import os
import threading
import time
import config
import utils

# 通用m3u8下载: 下载所有ts分段并合并
def downloadM3u8(m3u8Url, fileName, headers={}):
    print("-- dispatcher/downloadM3u8")

    if isIqiyi:
        data = json.loads(utils.getText(m3u8Url, headers))
        videos = data['data']['program']['video']
        videos = list(filter(lambda each: 'm3u8' in each and each['m3u8'] != '', videos))
        content = videos[0]['m3u8']
    else:
        content = utils.getText(m3u8Url, headers)

    urls = re.findall(r'\S+\.ts\S+', content)
    print('匹配到%d段视频，开始下载...' % len(urls))

    if len(urls) > 0 and not urls[0].startswith('http'):
        path, holder = utils.parseUrl(m3u8Url)
        urls = list(map(lambda ele: path + ele, urls))

    suffix = '.ts'
    threadList, names = [], []
    for i in range(len(urls)):
        name = '%s_第%d段%s' % (fileName, i+1, suffix)
        name = os.path.join(config.tempFilePath, name)
        names.append(name)

    utils.downloadAll(urls, names, headers, 2)

    fileName = os.path.join(config.videoFilePath, fileName + '.mp4')
    utils.mergePartialVideos(names, fileName)

# flv/f4v视频分段下载并合并
def downloadFlv(urls, fileName, headers={}):
    print("-- dispatcher/downloadFlv")
    if isinstance(urls, str):
        urls = urls.split('|')
    _, suffix = utils.parseUrl(urls[0])
    suffix = '.' + suffix.rsplit('.', 1)[-1]

    print('匹配到' + str(len(urls)) + '段视频，开始下载...')

    names = []
    for i in range(len(urls)):
        name = '%s_第%d段%s' % (fileName, i+1, suffix)
        name = os.path.join(config.tempFilePath, name)
        names.append(name)

        if isBilibili:
            # 1080p视频的第一段，多线程下载容易失败（官方限制）
            if i == 0 and urls[i].find('-80.flv') > 0:
                # 每个线程下载500k，减轻失败代价
                fileSize = utils.getFileSize(urls[i], headers)
                threadCount = fileSize // (1024 * 500) + 1
                # 并行数量降低，降低失败率
                utils.multiThreadDownload(urls[i], name, headers, threadCount, 8)
            else:
                utils.multiThreadDownload(urls[i], name, headers, 16)
        else:
            utils.download(urls[i], name, headers)

    fileName = os.path.join(config.videoFilePath, fileName + suffix)
    utils.mergePartialVideos(names, fileName)

# bilibili专属: 下载m4s音视频并合并
def downloadM4s(urls, fileName, headers={}):
    print("-- dispatcher/downloadM4s")

    audioUrl, videoUrl = urls.split('|')
    _, suffix = utils.parseUrl(videoUrl)
    suffix = '.' + suffix.rsplit('.', 1)[-1]

    audioName = os.path.join(config.tempFilePath, fileName + suffix + '.audio')
    videoName = os.path.join(config.tempFilePath, fileName + suffix + '.video')
    fileName = os.path.join(config.videoFilePath, fileName + '.mp4')

    print('匹配到一段音频和一段视频，开始下载音频和视频...')

    utils.download(audioUrl, audioName, headers)
    utils.download(videoUrl, videoName, headers)
    utils.mergeAudio2Video(videoName, audioName, fileName)



def download(linksurl, fileName, headers={}):
    fileName = re.sub(r'[/\:*?"<>|]', '_', fileName)

    global isBilibili, isIqiyi, isMgtv
    isBilibili = linksurl.find('acgvideo.com') > 0 or linksurl.find('bili') > 0
    isIqiyi = linksurl.find('iqiyi.com') > 0
    isMgtv = linksurl.find('mgtv.com') > 0

    if isBilibili:
        headers['referer'] = 'https://www.bilibili.com/'
    elif isMgtv:
        headers['referer'] = 'https://www.mgtv.com/'

    if linksurl.find('.m3u8') > 0 or linksurl.find('dash?') > 0:
        downloadM3u8(linksurl, fileName, headers)
    elif linksurl.find('m4s') > 0:
        downloadM4s(linksurl, fileName, headers)
    elif linksurl.find('.flv') > 0 or linksurl.find('.f4v') > 0:
        downloadFlv(linksurl, fileName, headers)
    else:
        downloadFlv(linksurl, fileName, headers)