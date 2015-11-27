#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import logging
import logging.config
import sys

reload(sys)
sys.setdefaultencoding('utf-8')


class FamilyCopy(object):
    def __init__(self):
        # 初始化日志系统
        logging.config.fileConfig('logging.conf')
        logger = logging.getLogger("familycopy")

        logger.info("Program started.")
        # logger.warning("An error has happened!")

        # 命令行参数处理，接收两个定位参数：源文件目录和目标文件目录；两个可选参数：配置文件路径和日志文件路径
        parser = argparse.ArgumentParser()
        parser.add_argument("src", help="source file directory")
        parser.add_argument("dst", help="destination file directory")
        parser.add_argument("-c", "--config", help="path of config file")
        args = parser.parse_args()

        # 校验参数
        logger.info("Check source directory:")
        if os.path.isdir(args.src):
            logger.info("%s is existed directory.", args.src)
        else:
            logger.error("%s is not directory, exit...", args.src)
            exit()

        logger.info("Check destination directory:")
        if os.path.isdir(args.dst):
            logger.info("%s is existed directory.", args.dst)
        else:
            userchoice = raw_input("%s is not directory. Need to create? (y/n)" % args.dst)
            cpchoice = userchoice.lower()
            if "yes" == cpchoice or "y" == cpchoice:
                # 创建目录
                try:
                    os.makedirs(args.dst)
                except OSError, msg:
                    logger.error("Create directory %s failed : %s.exit...", args.dst, str(msg))
                    exit()
                else:
                    logger.info("Create directory %s succeed.", args.dst)
            else:
                logger.info("Choose not to create directory, exit...")
                exit()

        if args.config:
            if os.path.isfile(args.config):
                # 读取配置文件
                pass
            else:
                logger.info("%s is not file, use default config file", args.config)

        # 保存成员变量
        self.logger = logger
        self.src = args.src
        self.dst = args.dst

    # 计算MD5值
    def calcmd5(self):
        pass

    # 计算sha1值
    def calcsha1(self):
        pass

    # 计算sha256值
    def calcsha256(self):
        pass

    # 处理源文件
    def handlesrcfile(self, srcfile):
        pass

    # 遍历源文件目录
    def handlesrcdir(self, srcdir):
        pass


def main():
    FamilyCopy()

if __name__ == '__main__':
    main()

