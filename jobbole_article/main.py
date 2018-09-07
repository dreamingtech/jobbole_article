#coding = utf-8

from scrapy import cmdline
import sys, os

#os.path.abspath(__file__)得到的是当前的main文件所在的绝对目录, 而os.path.dirname得到的是某个文件的父级目录.
# print(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# cmdline.execute(['scrapy', 'crawl', 'jobbole'])
cmdline.execute("scrapy crawl jobbole".split())
