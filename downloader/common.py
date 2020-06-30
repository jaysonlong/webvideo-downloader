# -*- coding:utf-8 -*-
from dispatcher import TaskDispatcher


def main():
    taskDispatcher = TaskDispatcher()
    
    while True:
        try:
            linksurl = input('输入暴力猴链接或本地m3u8路径: ').strip()
            fileName = input('输入文件名: ').strip()
            isMultiPart = linksurl.find('www.bilibili.com') != -1
            pRange = input('输入首、尾P(空格分隔)或单P: ').strip() if isMultiPart else None
        except KeyboardInterrupt:
            break

        taskDispatcher.dispatch(linksurl=linksurl, fileName=fileName, pRange=pRange)

if __name__ == '__main__':
    main()