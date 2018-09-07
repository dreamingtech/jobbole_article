# -*- coding: utf-8 -*-
from scrapy.pipelines.images import ImagesPipeline
import codecs, json
import datetime


class JobboleArticlePipeline(object):
    def process_item(self, item, spider):
        return item


# 自定义图片下载处理的中间件
class JobboleImagePipeline(ImagesPipeline):
    # 重写函数, 改写item处理完成的函数
    def item_completed(self, results, item, info):
        # result是一个list的结构. 可以获取多个图片保存的信息. 但由于使用yield, 一次只传递过一个item, 所以这里的result中只有一个元素.
        if "front_image_url" in item:
            for key, value in results:
                try:
                    front_image_path = value.get('path', '')
                except Exception as e:
                    front_image_path = ''
            item["front_image_path"] = front_image_path
        # 在完成处理后一定要返回item, 这样数据才能被下一个pipeline接收并处理.
        # 在此处添加断点再次进行调试, 看item中是否保存了图片下载的路径. 
        return item


# 自定义管道将Item导出为Json文件
class JsonWithEncodingPipeline(object):

    # 初始化时调用
    def __init__(self):
        # 打开json文件
        # 使用codecs完成文件的打开和写入能够解决编码方面的问题
        self.file = codecs.open('article.json', 'w', encoding="utf-8")

    # 重写Item处理
    def process_item(self, item, spider):
        # 先把item转换为dict格式, 再使用json.dump把它转换为字符串. 
        # 需要关闭ensure_ascii, 使用utf-8编码写入数据, 否则会以ascii方式写入, 中文字符就无法正确显示.
        # 用这种方法写入的每一行数据都是一个字典, 整体上其实并不是一个真正的json文件.
        lines = json.dumps(dict(item), ensure_ascii=False, indent=2) + "\n"
        # 将一行数据写入
        self.file.write(lines)
        # 重写process_item方法时必须要使用return把它返回去, 以供其它的pipeline使用.
        return item

    # 爬虫结束关闭spider时调用spider_closed方法
    def spider_closed(self, spider):
        # 关闭文件句柄
        self.file.close()


from scrapy.exporters import JsonItemExporter


# 调用scrapy提供的json export导出json文件.
class JsonExporterPipeline(object):
    # 调用scrapy提供的json exporter导出json文件
    def __init__(self):
        # 以二进制方法打开json文件
        self.file = open('json_item_exporter.json', 'wb')
        # 实例化一个JsonItemExporter对象exporter, 在实例化时需要传递几个参数. 
        self.exporter = JsonItemExporter(self.file, encoding="utf-8", ensure_ascii=False, indent=2)
        # 使用start_exporting方法开始导出
        self.exporter.start_exporting()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item

    def close_spider(self, spider):
        # 使用finish_exporting方法结束导出
        self.exporter.finish_exporting()
        self.file.close()


import MySQLdb


# 同步机制写入数据库
class MysqlPipeline(object):
    def __init__(self):
        # 创建一个连接MySQLdb.connect('host', 'user', 'password', 'dbname', charset, use_unicode), 可以打开connect函数查看其源码.
        # self.conn = MySQLdb.connect('127.0.0.1', 'root', 'mysql', ' article_spider', charset="utf8", use_unicode=True)
        self.conn = MySQLdb.connect(
            host='127.0.0.1',
            user='root',
            password='password',
            db='jobbole_article',
            port=3306,
            charset='utf8',
        )

        # 执行数据库的具体操作是由cursor来完成的.
        self.cursor = self.conn.cursor()

    def process_item(self, item, spider):
        # 这里insert插入的操作要与之前数据库中设置的字段的名称和顺序相同.
        insert_sql = '''
            insert ignore into
            article(title, create_date, article_url, url_object_id, front_image_url, front_image_path, comment_num, praise_num, fav_num, tags, content)
            VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        # 因为mysql中定义的create_date为日期格式的, 所以要先把item中字符串格式的create_date转换为日期格式
        # item['create_date'] = datetime.datetime.strptime(item['create_date'], "%Y/%m/%d").date()
        # 注意, 当点赞数量为0时, 在jobbole.py中是无法取到值的, 也就无法进入到items.py中的input_processor进行处理, item中就没有这个字段的值, 所以这里对praise_num要使用get方法进行选择.
        self.cursor.execute(insert_sql, (item.get("title"), item.get("create_date"), item.get("article_url"), item.get("url_object_id"), item.get("front_image_url")[0], item['front_image_path'], item.get("comment_num"), item.get("praise_num", ""), item.get("fav_num"), item.get("tags")), item.get("content"))
        # 注意使用的是conn.commit, 不是cursor.commit
        self.conn.commit()

    def spider_closed(self, spider):
        self.conn.close()


import MySQLdb.cursors
from twisted.enterprise import adbapi


# 异步操作写入数据库
class MysqlTwistedPipline(object):
    # from_settings和__init__这两个方法就能实现在启动spider时, 就把dbpool传递进来
    def __init__(self, dbpool):
        self.dbpool = dbpool

    # 在初始化时scrapy会调用from_settings方法, 将setting文件中的配置读入, 成为一个settings对象, 这种写法是固定的, 其中的参数不能修改. 
    @classmethod
    def from_settings(cls, settings):
        dbparas = dict(
            host=settings["MYSQL_HOST"],
            # 可以在settings中设置此pipeline, 在此处放置断点, 进行debug, 查看能否导入. 在attribute中可以看到settings中定义的所有的值. F6执行, 就能看到取到了settings中设置的host的值了.
            port=settings["MYSQL_PORT"],
            db=settings["MYSQL_DBNAME"],
            user=settings["MYSQL_USERNAME"],
            passwd=settings["MYSQL_PASSWORD"],
            # charset="utf8",
            charset="utf8mb4",
        # pymysql模块中也有类似的模块pymysql.cursors.DictCursor
            cursorclass=MySQLdb.cursors.DictCursor,
            use_unicode=True
        )
        # 创建twisted的mysql连接池, 使用twisted的连接池, 就能把mysql的操作转换为异步操作.
        # twisted只是提供了一个异步的容器, 并没有提供连接mysql的方法, 所以还需要MySQLdb的连接方法. 
        # adbapi可以将mysql的操作变成异步化的操作. 查看ConectionPool, def __init__(self, dbapiName, *connargs, **connkw). 
        # 需要指定使用的连接模块的模块名, 第一个参数是dbapiName, 即mysql的模块名MySQLdb. 第二个参数是连接mysql的参数, 写为可变化的参数形式. 查看MySQLdb的源码, 在from MySQLdb.connections import Connection中查看Connection的源码, 在class Connection中就能看到MySQLdb模块在连接mysql数据库时需要传递的参数. param这个dict中参数的名称要与其中的参数名称保持一致. 即与connections.py中 class Connection中的def __init__中定义的参数保持一致. 
        dbpool = adbapi.ConnectionPool("MySQLdb", **dbparas)
        # 如果对上面的写法不太理解, 可以写成下面的形式
        # dbpool = adbapi.ConnectionPool("MySQLdb", host = settings["MYSQL_HOST"], db = settings["MYSQL_DBNAME"], user = settings["MYSQL_USERNAME"], passwd = settings["MYSQL_PASSWORD"], charset = "utf8", cursorclass = MySQLdb.cursors.DictCursor, use_unicode = True)
        # 因为使用@classmethod把这个方法转换为类方法了, 所以cls就是指的MysqlTwistedPipline这个类, 所以cls(dbpool) 就相当于使用dbpool这个参数实例化MysqlTwistedPipline类的一个对象, 再把这个对象返回. 然后在init方法中接收这里创建的异步连接对象.
        return cls(dbpool)

    def process_item(self, item, spider):
        # 使用twisted将mysql数据库的插入变成异步插入, 第一个参数是自定义的函数, runInteraction可以把这个函数的操作变成异步的操作. 第二个参数是要插入的数据, 这里是item. 
        query = self.dbpool.runInteraction(self.do_insert, item)
        # 处理异常, 这里也可以不传递item和spider
        query.addErrback(self.handle_error, item, spider)

    # 自定义错误处理, 处理异步插入的异常, 这里也可以不传递item和spider, 只传递failure即可.
    def handle_error(self, failure, item, spider):
        print(failure)
        print(item)

    # 执行具体的插入, 此时的cursor就是self.dbpool.runInteraction中传递过来的cursor, 使用这个cursor, 就可以把mysql的操作变成异步的操作. 并且此时也不用再手动执行commit的操作了.
    def do_insert(self, cursor, item):
        insert_sql = '''
            INSERT IGNORE INTO 
            article(title, create_date, article_url, url_object_id, front_image_url, front_image_path, comment_num, praise_num, fav_num, tags, content)
            VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        # 注意, 当点赞数量为0时, 在jobbole.py中是无法取到值的, 也就无法进入到items.py中的input_processor进行处理, item中就没有这个字段的值, 所以这里对praise_num要使用get方法进行选择.
        cursor.execute(insert_sql, (item.get("title"), item.get("create_date"), item.get("article_url"), item.get("url_object_id"), item.get("front_image_url")[0], item.get("front_image_path",""), item.get("comment_num"), item.get("praise_num", "0"), item.get("fav_num"), item.get("tags"), item.get("content")))
