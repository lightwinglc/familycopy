#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import logging
import logging.config
import sys
import hashlib
import sqlite3
import datetime
import shutil

reload(sys)
sys.setdefaultencoding('utf-8')


# 数据库操作类，暂时只支持sqlite
class DBOperate(object):
    def __init__(self):
        try:
            self.conn = sqlite3.connect("db/facp.db")
            # self.conn.text_factory = str
            self.cu = self.conn.cursor()
            with self.conn:    # Using the connection as a context manager 自动commit()或者rollback()
                self.cu.execute('''CREATE TABLE IF NOT EXISTS familyfiles
                                  (id integer primary key autoincrement,
                                   hashvalue text UNIQUE,
                                   srcfile text,
                                   dstfile text)''')
                self.cu.execute('''CREATE INDEX IF NOT EXISTS familyfiles_hashvalue_index
                                    ON familyfiles (hashvalue)''')
        except sqlite3.Error, msg:
            logger.error("Generate table familyfiles failed : %s.exit...", str(msg))
            self.erase_resource()
            exit()
        else:
            logger.info("Generate table familyfiles succeed.")
        # finally:
            # self.conn.close()

    def erase_resource(self):
        self.cu.close()
        self.conn.close()

    def __del__(self):
        self.erase_resource()

    # 检查hash是否存在，返回True表示存在，False表示不存在
    def check_hash_existed(self, hashvalue):
        try:
            with self.conn:
                checkedvalue = (hashvalue, )
                self.cu.execute('''select id, srcfile, dstfile from familyfiles
                                    where hashvalue = ?''', checkedvalue)
                res = self.cu.fetchone()
                if res is None:
                    return False
                else:
                    logger.info("hashvalue %s already existed, same as srcfile %s, dstfile %s.",
                                hashvalue, res[1].encode("GBK"), res[2].encode("GBK"))
                    return True
        except sqlite3.Error, msg:
            logger.error("Check hash %s failed : %s.exit...", hashvalue, str(msg))
            exit()

    # 新增hash记录
    def add_hash(self, hashvalue, srcfile, dstfile):
        try:
            with self.conn:
                record = (hashvalue, srcfile, dstfile)
                self.cu.execute('''insert into familyfiles(hashvalue, srcfile, dstfile)
                                    values(?, ?, ?)''', record)
        except sqlite3.Error, msg:
            logger.error("DB add srcfile %s, hash %s failed : %s.exit...",
                         srcfile.encode("GBK"), hashvalue, str(msg))
            exit()


# 处理复制文件并改名分类的类
class FamilyCopy(object):
    def __init__(self, srcdir, dstdir):
        self.fadb = DBOperate()
        self.filehandled = 0
        self.fileignored = 0
        self.picset = (['.bmp', '.dib', '.gif', '.png', '.rle', '.tif', '.tiff', '.bw',
                        '.cdr', '.col', '.wmf', '.emf', '.ico', '.jpg', '.jpeg', '.pic'])
        self.videoset = (['.mp4', '.rm', '.rmvb', '.avi', '.divx', '.mpg', '.mpeg', '.wmv',
                          '.mov', '.asf', '.3gp', '.tp', '.ts'])
        # 保存成员变量
        self.srcdir = srcdir
        self.dstdir = dstdir

    # 计算文件hash加密，hash算法种类支持md5,sha1,sha256三种
    @staticmethod
    def calc_file_hash(inputfile, hashtype="md5", chunksize=10240):
        with open(inputfile, 'rb') as calcfile:
            hashobj = hashlib.md5()
            if hashtype == "md5":
                pass
            elif hashtype == "sha1":
                hashobj = hashlib.sha1()
            elif hashtype == "sha256":
                hashobj = hashlib.sha256()
            else:
                pass

            while True:
                chunk = calcfile.read(chunksize)
                if not chunk:
                    break
                hashobj.update(chunk)
            hashvalue = hashobj.hexdigest()
            logger.debug("Calc file %s, type %s, hash value %s", inputfile.encode("GBK"), hashtype, hashvalue)
            return hashvalue

    # 处理源文件
    def handle_src_file(self, srcfile):
        # 根据后缀区分照片和视频，未知后缀不处理
        filetype = "picture"
        filepart1, filepart2 = os.path.splitext(srcfile)
        if filepart2 in self.picset:
            pass
        elif filepart2 in self.videoset:
            filetype = "video"
        else:
            logger.warnning("file %s type not recognized, ignore", srcfile.encode("GBK"))
            return None

        # 计算文件hash，过滤重复文件
        hashvalue = self.calc_file_hash(srcfile, "sha256")
        if self.fadb.check_hash_existed(hashvalue):
            logger.info("file %s already existed, ignore", srcfile.encode("GBK"))
            self.fileignored += 1
            return None

        # 取文件创建时间
        srcfilectime = datetime.datetime.fromtimestamp(os.path.getctime(srcfile))
        # 拼接目标文件目录
        dstfilepath = os.path.join(self.dstdir, filetype, str(srcfilectime.year),
                                   str(srcfilectime.month), str(srcfilectime.day))
        if not os.path.isdir(dstfilepath):
            os.makedirs(dstfilepath)
            logger.info("Create directory %s succeed.", dstfilepath.encode("GBK"))
        # 拼接目标文件
        splitfilepath, splitfilename = os.path.split(srcfile)
        dstfile = os.path.join(dstfilepath, splitfilename)
        # 复制文件
        shutil.copyfile(srcfile, dstfile)
        logger.debug("File %s copy to %s.", srcfile.encode("GBK"), dstfile.encode("GBK"))

        # 插入数据库记录
        self.fadb.add_hash(hashvalue, srcfile, dstfile)
        self.filehandled += 1

    # 遍历源文件目录
    def handle_src_dir(self):
        for parentdir, dirnames, filenames in os.walk(self.srcdir):
            for filename in filenames:
                fullfilename = os.path.join(parentdir, filename)
                self.handle_src_file(fullfilename)
        logger.info("%d files was handled, %d files was ignored.", self.filehandled, self.fileignored)


def main():
    logger.info("Program started.")
    # 命令行参数处理，接收两个定位参数：源文件目录和目标文件目录；一个可选参数：配置文件路径
    parser = argparse.ArgumentParser()
    parser.add_argument("src", help="source file directory")
    parser.add_argument("dst", help="destination file directory")
    # parser.add_argument("-c", "--config", help="path of config file")
    args = parser.parse_args()
    srcdir = args.src.decode("GBK")
    dstdir = args.dst.decode("GBK")

    # 校验参数
    # 源文件目录是否存在
    logger.info("Check source directory:")
    if os.path.isdir(srcdir):
        logger.info("%s is existed directory.", srcdir.encode("GBK"))
    else:
        logger.error("%s is not directory, exit...", srcdir.encode("GBK"))
        exit()

    # 目标文件目录是否存在，不存在则提醒用户新建
    logger.info("Check destination directory:")
    if os.path.isdir(dstdir):
        logger.info("%s is existed directory.", dstdir.encode("GBK"))
    else:
        userchoice = raw_input("%s is not directory. Need to create? (y/n)" % dstdir.encode("GBK"))
        cpchoice = userchoice.lower()
        if "yes" == cpchoice or "y" == cpchoice:
            # 创建目录
            try:
                os.makedirs(dstdir)
            except OSError, msg:
                logger.error("Create directory %s failed : %s.exit...", dstdir.encode("GBK"), str(msg))
                exit()
            else:
                logger.info("Create directory %s succeed.", dstdir.encode("GBK"))
        else:
            logger.info("Choose not to create directory, exit...")
            exit()

    """
    # 配置文件
    if args.config:
        if os.path.isfile(args.config):
            # 读取配置文件
            pass
        else:
            logger.info("%s is not file, use default config file", args.config)
    """

    # 使用FamilyCopy类
    facp = FamilyCopy(srcdir, dstdir)
    facp.handle_src_dir()

# 初始化日志系统
# CRITICAL > ERROR > WARNING > INFO > DEBUG > NOTSET
logging.config.fileConfig('logging.conf')
logger = logging.getLogger("familycopy")

if __name__ == '__main__':
    main()

