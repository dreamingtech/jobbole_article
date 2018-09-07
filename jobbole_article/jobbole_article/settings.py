# -*- coding: utf-8 -*-

# Scrapy settings for jobbole_article project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://doc.scrapy.org/en/latest/topics/settings.html
#     https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://doc.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'jobbole_article'

SPIDER_MODULES = ['jobbole_article.spiders']
NEWSPIDER_MODULE = 'jobbole_article.spiders'

# 设置下载超时时间
DOWNLOAD_TIMEOUT = 10
# 禁止请求失败时重试
RETRY_ENABLED = True
# RETRY_ENABLED = False
# 设置重试次数
RETRY_TIMES = 1


###################################################
# 日志设置
# LOG_LEVEL = 'INFO'

###################################################

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = 'jobbole_article (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://doc.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN = 16
# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    # 'Accept-Language': 'en',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
}

# Enable or disable spider middlewares
# See https://doc.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'jobbole_article.middlewares.JobboleArticleSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    # 'jobbole_article.middlewares.JobboleArticleDownloaderMiddleware': 543,
    # 'jobbole_article.middlewares.RandomFakeUserAgentMiddleware': 100,
    # 'jobbole_article.middlewares.RandomLocalUserAgentMiddleware': 100,
    # 'jobbole_article.middlewares.UADMiddleware': 100,
    'jobbole_article.middlewares.RandomUAIPDownloaderMiddleware': 100,
}

# Enable or disable extensions
# See https://doc.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See https://doc.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    # 'jobbole_article.pipelines.JsonWithEncodingPipeline': 300,
    # 'jobbole_article.pipelines.JsonExporterPipeline': 301,
    # 'scrapy.pipelines.images.ImagesPipeline' : 200,
    # 'jobbole_article.pipelines.JobboleImagePipeline': 200,
    # 'jobbole_article.pipelines.MysqlPipeline': 302,
    'jobbole_article.pipelines.MysqlTwistedPipline': 302,
}

################################################################
# 图片下载设置

# 设置图片url的字段, scrapy将从item中找出此字段进行图片下载
IMAGES_URLS_FIELD = "front_image_url"
# 设置图片下载保存的目录, 这里不直接使用本机的绝对路径, 而是通过程序获取路径. 这样在程序迁移后也能够正常运行. 
import os

# os.path.dirname(__file__)获取当前文件所在的文件夹名称.
# os.path.abspath(os.path.dirname(__file__))获得当前文件所在的绝对路径. 
project_path = os.path.dirname(os.path.abspath(__file__))
# 想要把下载的图片保存在与settings同目录的images文件夹中, 要先在项目中新建此文件夹. 
# IMAGES_STORE中定义保存图片的路径
IMAGES_STORE = os.path.join(project_path, "images")
# 表示只下载大于100x100的图片, 查看images.py的源码, 程序会自动的从settings.py中读取设置的IMAGES_MIN_HEIGHT和IMAGES_MIN_WIDTH值
# IMAGES_MIN_HEIGHT = 100
# IMAGES_MIN_WIDTH = 100

if not os.path.exists(IMAGES_STORE):
    os.mkdir(IMAGES_STORE)
else:
    pass
################################################################


################################################################
# mysql配置

MYSQL_HOST = '127.0.0.1'
# 这里设置的是数据库的名字, 不是数据表的名字
MYSQL_DBNAME = 'jobbole_article'
MYSQL_USERNAME = 'root'
MYSQL_PASSWORD = 'Xzq@8481'
MYSQL_PORT = 3306

################################################################


# Enable and configure the AutoThrottle extension (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
