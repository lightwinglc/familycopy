#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import logging
import logging.config
import sys
import hashlib
import sqlite3

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
                                   oldfilename text,
                                   newfilename text)''')
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
                self.cu.execute("select id, oldfilename from familyfiles where hashvalue = ?",
                                checkedvalue)
                res = self.cu.fetchone()
                if res is None:
                    return False
                else:
                    logger.info("hashvalue %s already existed, same as oldfile %s.",
                                hashvalue, res[1])
                    return True
        except sqlite3.Error, msg:
            logger.error("Check hash %s failed : %s.exit...", hashvalue, str(msg))
            exit()

    # 新增hash记录
    def add_hash(self, hashvalue, oldfilename):
        try:
            with self.conn:
                record = (hashvalue, oldfilename)
                self.cu.execute('''insert into familyfiles(hashvalue, oldfilename)
                                    values(?, ?)''', record)
        except sqlite3.Error, msg:
            logger.error("Add oldfilename %s, hash %s failed : %s.exit...",
                         oldfilename, hashvalue, str(msg))
            exit()


# 处理复制文件并改名分类的类
class FamilyCopy(object):
    def __init__(self, srcdir, dstdir):
        self.fadb = DBOperate()
        self.filehandled = 0
        self.fileignored = 0
        # 保存成员变量
        self.srcdir = srcdir.decode("GBK")
        self.dstdir = dstdir.decode("GBK")

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
            logger.debug("Calc file %s, type %s, hash value %s", inputfile, hashtype, hashvalue)
            return hashvalue

    # 处理源文件
    def handle_src_file(self, srcfile):
        hashvalue = self.calc_file_hash(srcfile, "sha256")
        if self.fadb.check_hash_existed(hashvalue):
            logger.info("file %s already existed, ignore", srcfile)
            self.fileignored += 1
        else:
            self.fadb.add_hash(hashvalue, srcfile)
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
    parser.add_argument("-c", "--config", help="path of config file")
    args = parser.parse_args()

    # 校验参数
    # 源文件目录是否存在
    logger.info("Check source directory:")
    if os.path.isdir(args.src):
        logger.info("%s is existed directory.", args.src)
    else:
        logger.error("%s is not directory, exit...", args.src)
        exit()

    # 目标文件目录是否存在，不存在则提醒用户新建
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

    # 配置文件
    if args.config:
        if os.path.isfile(args.config):
            # 读取配置文件
            pass
        else:
            logger.info("%s is not file, use default config file", args.config)

    # 使用FamilyCopy类
    facp = FamilyCopy(args.src, args.dst)
    facp.handle_src_dir()

# 初始化日志系统
# CRITICAL > ERROR > WARNING > INFO > DEBUG > NOTSET
logging.config.fileConfig('logging.conf')
logger = logging.getLogger("familycopy")

if __name__ == '__main__':
    main()

