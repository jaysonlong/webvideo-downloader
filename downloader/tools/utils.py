# -*- coding:utf-8 -*-
import os
import sys
import json
import argparse
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse, unquote
import xml.etree.ElementTree as ET
import logging
import requests
import colorama

colorama.init(autoreset=True)


debug = False

reqLogger = None

userAgent = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 " 
        + "(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
}


# xml工具，自动补全namespace
class XMLUtils:
    @classmethod
    def parse(clz, source):
        try:
            root = ET.fromstring(source)
        except:
            root = ET.parse(source).getroot()

        matches = re.match(r'{.+}', root.tag)
        clz.namespace = matches.group(0) if matches else ''
        return root

    @classmethod
    def _addns(clz, xpath):
        xpath = xpath if xpath.startswith('./') else './' + xpath
        return re.sub(r'([/\[])([\w\-]+)', ('\\g<1>%s\\g<2>' % clz.namespace), xpath)

    @classmethod
    def findall(clz, node, xpath):
        return node.findall(clz._addns(xpath))

    @classmethod
    def find(clz, node, xpath):
        return node.find(clz._addns(xpath))

    @classmethod
    def findtext(clz, node, xpath):
        return node.findtext(clz._addns(xpath))


def setupDebug(val):
    global debug
    debug = val

def setupRequestLogger(logPath, logFileName = 'trace.log'):
    global reqLogger
    reqLogger = logging.getLogger('request')
    reqLogger.setLevel(logging.INFO)

    logPath = realPath(logPath)
    mkdirIfNotExists(logPath)
    logFileName = os.path.join(logPath, logFileName)

    file_handler = logging.FileHandler(logFileName, mode='w')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    reqLogger.addHandler(file_handler)

def mergeDict(*dicts):
    ret = {}
    for each in dicts:
        for key in each:
            ret[key] = each[key]
    return ret

def request(*args, **kargs):
    kargs['timeout'] = kargs.get('timeout', 8)
    kargs['headers'] = mergeDict(userAgent, kargs.get('headers', {}))
    reqLogger and reqLogger.info('%s %s' % (args, kargs))

    method, url = args[:2]

    try:
        response = requests.request(*args, **kargs)
    except Exception as e:
        reqLogger and reqLogger.error('%s %s error: %s' % (method, url, str(e)))
        raise e

    if response.status_code > 299:
        reqLogger and reqLogger.error('%s %s http响应: %d错误' \
            % (method, url, response.status_code))
        raise Exception('%s %s http响应: %d错误' \
            % (method, url, response.status_code))
    return response

def getText(url, headers = {}, **kargs):
    if not url.startswith('http'):
        # 读取本地文件
        with open(url, 'r', encoding="utf-8") as f:
            return f.read()
    response = request('GET', url, headers=headers, **kargs)
    return response.text

def getFileSize(url, headers = {}):
    response = request("GET", url, headers=headers, stream=True)
    return int(response.headers['Content-Length'])


def escapeFileName(fileName):
    return re.sub(r'[/\:*?"<>|]', '_', fileName)

def stringify(obj):
    return json.dumps(obj, indent=4, ensure_ascii=False, \
            default=lambda x: '<not serializable>')

def parseUrlQuery(url):
    ret = {}

    items = urlparse(unquote(url)).query.split('&')
    for item in items:
        key, value = item.split('=')
        ret[key] = value
    return ret

def normalResponse(handler, resp, contentType = 'text/html'):
    handler.send_response(200)
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Content-type', contentType)
    handler.end_headers()

    if isinstance(resp, str):
        resp = resp.encode('utf-8')
    handler.wfile.write(resp)

def getBasePath(url):
    return url.split('?', 1)[0].rsplit('/', 1)[0] + '/'

def getFileName(url):
    return url.split('?', 1)[0].rsplit('/', 1)[-1]

def getSuffix(url):
    return '.' + getFileName(url).rsplit('.', 1)[-1]

def generateFileNames(urls, baseFileName):
    suffix = getSuffix(urls[0])

    if len(urls) == 1:
        return [baseFileName + suffix]
    else:
        fileNames = []
        for i in range(len(urls)):
            fileName = '%s_第%03d段%s' % (baseFileName, i+1, suffix)
            fileNames.append(fileName)
        return fileNames

def realPath(path):
    path = Path(sys.path[0]).joinpath(path)
    return os.path.realpath(str(path))

def join(*args):
    return os.path.realpath(os.path.join(*args))

def mkdirIfNotExists(path):
    os.path.exists(path) or os.makedirs(path)

def touchIfNotExists(file):
    Path(file).touch()

def removeFiles(fileNames):
    if isinstance(fileNames, str):
        fileNames = [fileNames]

    for fileName in fileNames:
        try:
            os.remove(fileName)
        except Exception:
            pass

def mergeFiles(fileNames, dstFileName):
    with open(dstFileName, "wb") as dstFile:
        for fileName in fileNames:
            with open(fileName, 'rb') as srcFile:
                shutil.copyfileobj(srcFile, dstFile)

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
 
def filterHlsUrls(content, url = None):
    urls = re.findall(r'[^#"\s]+\.(?:ts|mp4)[^"\s]*', content, re.MULTILINE)

    if len(urls) > 0 and not urls[0].startswith('http'):
        basePath = getBasePath(url)
        urls = list(map(lambda url: basePath + url, urls))
    return urls

def tryFixSrtFile(srtFile):
    convertVttToSrt(srtFile)
    fillSrtNumber(srtFile)

def convertVttToSrt(srtFile):
    if not srtFile.endswith('.vtt'):
        return

    with open(srtFile, 'r+', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        if re.search(r'STYLE\r?\n[^}]+}\r?\n\r?\n', content):
            no_style_content = re.sub(r'STYLE\r?\n[^}]+}\r?\n\r?\n', '', content)
            f.seek(0)
            f.truncate()
            f.write(no_style_content)

    logLevel = 'info' if debug else 'fatal'
    realSrtFile = srtFile.rsplit('.', 1)[0] + '.srt'
    cmd = ('ffmpeg -i "%s" -v %s "%s"') % (srtFile, logLevel, realSrtFile)
    os.system(cmd)

    if debug:
        os.rename(srtFile, srtFile + '.tmp')
    else:
        removeFiles(srtFile)
    os.rename(realSrtFile, srtFile)

def fillSrtNumber(srtFile):
    with open(srtFile, 'r+', encoding='utf-8', errors='ignore') as f:
        content = f.read()

        if not re.search(r'\r?\n\r?\n.+-->', content):
            return

        items = re.finditer(r'\r?\n.+-->', content)

        rs = ''
        lastPos = 0
        for i, item in enumerate(items):
            rs += content[lastPos:item.start()] + str(i+1) + item.group()
            lastPos = item.end()

        rs += content[lastPos:]
        f.seek(0)
        f.write(rs)

def getArguments(*options):
    # kwargs['dest'] = 'dest'
    parser = argparse.ArgumentParser()

    for option in options:
        name = option.pop('name')
        names = name if isinstance(name, list) else [name]
        parser.add_argument(*names, **option)
    rs = parser.parse_args(sys.argv[1:])
    return rs

def checkFFmpeg():
    with os.popen('ffmpeg -v quiet 2>&1') as f:
        if f.read().strip():
            print('\033[93m警告: ffmpeg命令找不到，将影响视频文件合并，' + \
                '请配置PATH路径，或将其置于当前目录（仅Windows）\033[0m')

def mergePartialVideos(fileNames, fileName, correct = False):
    print('正在合并视频')

    if correct:
        # 快速二进制合并，用于校正hls视频时间戳
        mergeFiles(fileNames, fileName)
    else:
        # 使用concat demuxer合并，只需编码相同无需格式相同，适应范围更广
        concatFile = join(os.path.dirname(fileName), 'concat.txt')

        text = "file '" + ("'\nfile '".join(fileNames)) + "'" 
        with open(concatFile, 'w', encoding="utf-8") as f:
            f.write(text)
        
        extraArgs = ''
        if fileName.endswith('.mp4'):
            extraArgs += ' -movflags faststart '
        logLevel = 'info' if debug else 'fatal'

        cmd = ('ffmpeg -safe 0 -f concat -i %s -c copy %s -bsf:a aac_adtstoasc ' \
            + '-v %s -y "%s"') % (concatFile, extraArgs, logLevel, fileName)
        os.system(cmd)

        if debug:
            print('\nffmpeg command:', cmd)
        else:
            removeFiles(concatFile)


def mergeAudio2Video(audioNames, videoNames, fileName):
    print('正在合并视频')

    audioName = audioNames[0]
    videoName = videoNames[0]
    isMultiAudio = len(audioNames) > 1
    isMultiVideo = len(videoNames) > 1

    if isMultiAudio:
        audioName = fileName + '.audio'
        mergeFiles(audioNames, audioName)
    if isMultiVideo:
        videoName = fileName + '.video'
        mergeFiles(videoNames, videoName)

    extraArgs = ''
    if fileName.endswith('.mp4'):
        extraArgs += ' -movflags faststart '
    logLevel = 'info' if debug else 'fatal'

    cmd = 'ffmpeg -i "%s" -i "%s" -c:v copy -c:a copy %s -v %s -y "%s"' \
        % (audioName, videoName, extraArgs, logLevel, fileName)
    os.system(cmd)

    if debug:
        print('\nffmpeg command:', cmd)
    else:
        isMultiAudio and removeFiles(audioName)
        isMultiVideo and removeFiles(videoName)

def integrateSubtitles(subtitlesInfo, videoName):
    print('正在集成字幕')

    subtitleNames = list(map(lambda x: x[1], subtitlesInfo))
    fileNames = [videoName] + subtitleNames
    inputCmd = ' '.join(map(lambda x: ('-i "%s"' % x), fileNames))
    mapCmd = '-map 0'
    for i, (name, subtitleName) in enumerate(subtitlesInfo):
        mapCmd += ' -map %d -metadata:s:s:%d title="%s"' % (i+1, i, name)

    isMp4 = videoName.endswith('.mp4')
    tempVideoName = videoName.rsplit('.', 1)[0] + '.srt.mp4'
    targetFileName = videoName if isMp4 else (videoName.rsplit('.', 1)[0] + '.mp4')
    logLevel = 'info' if debug else 'fatal'

    cmd = ('ffmpeg %s %s -c:v copy -c:a copy -c:s mov_text -movflags faststart ' + \
        '-v %s -y "%s"') % (inputCmd, mapCmd, logLevel, tempVideoName)
    os.system(cmd)

    if debug:
        print('\nffmpeg command:', cmd)
    else:
        removeFiles(videoName)
        os.rename(tempVideoName, targetFileName)
    return targetFileName
