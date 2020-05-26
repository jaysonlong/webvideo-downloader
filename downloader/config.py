# -*- coding:utf-8 -*-
import os

# 是否静默删除下载的临时文件
delSilent = True 

# 临时文件保存路径
tempFilePath = "../temp/"

# 视频文件保存路径
videoFilePath = "../videos/"


if not os.path.exists(tempFilePath):
    os.makedirs(tempFilePath)

if not os.path.exists(videoFilePath):
    os.makedirs(videoFilePath)