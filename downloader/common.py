# -*- coding:utf-8 -*-
import sys
import os
import dispatcher


def main():
    while True:
        linksurl = input('输入油猴链接或本地m3u8路径:')
        filename = input('输入保存文件名:')

        if not linksurl or not filename:
            continue
        dispatcher.download(linksurl, filename)


if __name__ == "__main__":
    main()
