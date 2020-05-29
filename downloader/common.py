# -*- coding:utf-8 -*-
import sys
import os
import dispatcher


def main():
    while True:
        linksurl = input('输入油猴链接或本地m3u8路径:').strip()
        fileName = input('输入保存文件名:').strip()
        print()

        try:
            dispatcher.download(linksurl, fileName)
        except Exception as e:
            print(e)

if __name__ == "__main__":
    main()
