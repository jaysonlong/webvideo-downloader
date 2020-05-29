# -*- coding:utf-8 -*-
import os
import utils

# 是否静默删除下载的临时文件
delSilent = True 

# 临时文件保存路径
tempFilePath = utils.toAbsolutePath("../temp/")

# 视频文件保存路径
videoFilePath = utils.toAbsolutePath("../videos/")


utils.ensureDir(tempFilePath)
utils.ensureDir(videoFilePath)