# -*- coding:utf-8 -*-
import requests
import re
import json
import dispatcher
import utils

def getAllPartInfo(url):
    headers = {
        "referer": "https://www.bilibili.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
    }
    resp = requests.get(url, headers=headers)
    content = resp.content.decode('utf-8')

    # 获取分p名称和cid
    match = re.search(r'<script>window\.__INITIAL_STATE__=(.+?});.+?</script>', content)
    data = json.loads(match.group(1))
    isOpera = 'epList' in data
    pages = data['epList'] if isOpera else data['videoData']['pages']

    allPartInfo = []
    for page in pages:
        if isOpera:
            name, partUrl = page['longTitle'], re.sub(r'\d+$', str(page['id']), url)
        else:
            name, partUrl = page['part'], url + '?p=' + str(page['page'])

        allPartInfo.append({
            'cid': page['cid'],
            'name': name,
            'url': partUrl,
        })
    
    return allPartInfo


# 获取指定p的视频url
def getPartUrl(partUrl, partCid, basePlayInfoUrl, sessCookie):
    def getBandwidth(item):
        return item['bandwidth']

    headers = {
        "referer": "https://www.bilibili.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
        "Cookie": "CURRENT_FNVAL=16",
    }
    resp = requests.get(partUrl, headers=headers)
    content = resp.content.decode('utf-8')
    match = re.search(r'<script>window\.__playinfo__=(.+?)</script>', content)

    if match: 
        data = match.group(1)
        data = json.loads(data)['data']
    else: 
        playInfoUrl = basePlayInfoUrl + '&cid=' + str(partCid)
        headers = { 'Cookie': sessCookie }
        data = utils.getText(playInfoUrl, headers)
        data = json.loads(data)['data']

    if 'dash' in data:
        # 音视频分离
        data = data['dash']
        data['audio'].sort(key=getBandwidth, reverse=True)
        data['video'].sort(key=getBandwidth, reverse=True)
        combineVideoUrl = data['audio'][0]['baseUrl'] + '|' + data['video'][0]['baseUrl']
    elif 'durl' in data:
        # 视频分段
        data = data['durl']
        urls = list(map(lambda each: each['url'], data))
        combineVideoUrl = '|'.join(urls)

    return combineVideoUrl

def downloadRangeParts(linksurl, baseFileName, pRange):
    if linksurl.find('|') != -1:
        baseUrl, basePlayInfoUrl, sessCookie = linksurl.split('|')
    else:
        baseUrl, basePlayInfoUrl, sessCookie = linksurl, '', ''

    pRange = pRange.strip().split(' ')
    startP, endP = pRange if len(pRange) > 1 else pRange * 2
    baseUrl, startP, endP = baseUrl.split('?')[0], int(startP), int(endP)
    allPartInfo = getAllPartInfo(baseUrl)

    print('\n准备下载第%d-%dP\n' % (startP, endP))

    for p in range(startP, endP + 1):
        partInfo = allPartInfo[p-1]
        partUrl, partCid, partName = partInfo['url'], partInfo['cid'], partInfo['name']
        combineVideoUrl = getPartUrl(partUrl, partCid, basePlayInfoUrl, sessCookie)
        fileName = 'P{:03d}__{}__{}'.format(p, baseFileName, partName)

        print('开始下载第{}P: {}'.format(p, fileName))
        dispatcher.download(combineVideoUrl, fileName)

def main():
    while True:
        linksurl = input('输入油猴多p链接: ').strip()
        baseFileName = input('输入文件名: ').strip()
        pRange = input('输入首、尾P(空格分隔)或单P: ').strip()
        
        try:
            downloadRangeParts(linksurl, baseFileName, pRange)
        except Exception as e:
            print(e)

if __name__ == '__main__':
    main()