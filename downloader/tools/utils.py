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
import requests
import colorama

colorama.init(autoreset=True)


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



userAgent = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 " 
        + "(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
}

def mergeDict(*dicts):
    ret = {}
    for each in dicts:
        for key in each:
            ret[key] = each[key]
    return ret

def request(*args, **kargs):
    kargs['timeout'] = kargs.get('timeout', 5)
    kargs['headers'] = mergeDict(userAgent, kargs.get('headers', {}))

    response = requests.request(*args, **kargs)
    if response.status_code > 299:
        raise Exception('http响应: %d错误' % response.status_code)
    return response

def getText(url, headers = {}):
    if not url.startswith('http'):
        # 读取本地文件
        with open(url) as f:
            return f.read()
    response = request('GET', url, headers=headers)
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

def getSuffix(url):
    return '.' + url.split('?', 1)[0].rsplit('/', 1)[-1].rsplit('.', 1)[-1]

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

def toAbsolutePath(path, currFile):
    path = str(Path(path))
    if path == str(Path(path).absolute()):
        return path
    else:
        scriptPath = os.path.split(os.path.abspath(currFile))[0]
        return os.path.join(scriptPath, str(Path(path)))

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
    urls = re.findall(r'\S+\.ts\S*', content)

    if len(urls) > 0 and not urls[0].startswith('http'):
        basePath = getBasePath(url)
        urls = list(map(lambda url: basePath + url, urls))
    return urls

def getArguments(*options):
    # kwargs['dest'] = 'dest'
    parser = argparse.ArgumentParser()

    for option in options:
        name = option.pop('name')
        parser.add_argument(name, **option)
    rs = parser.parse_args(sys.argv[1:])
    return rs

def checkFFmpeg():
    with os.popen('ffmpeg -v quiet 2>&1') as f:
        if f.read().strip():
            print('\033[93m警告: ffmpeg命令找不到，将影响视频文件合并，' + \
                '请配置PATH路径，或将其置于当前目录（仅Windows）\033[0m')

def mergePartialVideos(fileNames, fileName, concat = True):
    print('正在合并视频')

    if concat:
        # 使用concat demuxer合并，只需编码相同无需格式相同，适应范围更广
        text = "file '" + ("'\nfile '".join(fileNames)) + "'" 
        with open('concat.txt', 'w') as f:
            f.write(text)
        
        extraArgs = '-movflags faststart' if fileName.endswith('.mp4') else ''
        cmd = 'ffmpeg -safe 0 -f concat -i concat.txt -c copy -v fatal ' + \
            '-bsf:a aac_adtstoasc -y %s "%s"' % (extraArgs, fileName)
        os.system(cmd)
        removeFiles('concat.txt')
    else:
        # 快速二进制合并，适用部分hls
        mergeFiles(fileNames, fileName)


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

    extraArgs = '-movflags faststart' if fileName.endswith('.mp4') else ''
    cmd = 'ffmpeg -i "%s" -i "%s"  -c copy -v fatal -y %s "%s"' % (audioName, videoName, extraArgs, fileName)
    os.system(cmd)

    isMultiAudio and removeFiles(audioName)
    isMultiVideo and removeFiles(videoName)

