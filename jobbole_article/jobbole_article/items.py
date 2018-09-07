# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html
import re
import datetime
import hashlib

import scrapy
from scrapy.loader.processors import MapCompose
from scrapy.loader.processors import TakeFirst
from scrapy.loader.processors import Join
from scrapy.loader import ItemLoader


class JobboleArticleItem(scrapy.Item):
    title = scrapy.Field()
    create_date = scrapy.Field()
    # 文章详情的url
    article_url = scrapy.Field()
    # url是变长的, 通过md5把它变成固定长度的.
    url_object_id = scrapy.Field()
    # 封面图的url地址
    front_image_url = scrapy.Field()
    # 封面图在本地保存的路径.
    front_image_path = scrapy.Field()
    praise_num = scrapy.Field()
    fav_num = scrapy.Field()
    comment_num = scrapy.Field()
    content = scrapy.Field()
    tags = scrapy.Field()


# MapCompose这个方法可以传递任意多的函数, 能传递过来的值进行预处理. 如对于title字段, 想要加一个后缀-jobbole, 在这个类之前先定义一个函数add_jobbole()
def add_jobbole(value):
    return value + '-jobbole'


def remove_dot(value):
    return value.replace("·", "").strip()


# 处理文章的发表时间, 这里不把字符串转换为时间格式, 而是使用mysql的自动转换功能. 也能避免时期无法使用josn序列化的问题.
def date_convert(value):
    try:
        create_time = datetime.datetime.strptime(value, "%Y/%m/%d").date()
    except Exception as e:
        create_time = datetime.datetime.now().date()
    return create_time


# 提取数字
def get_num(value):
    match_re = re.match(r'.*?(\d+).*', value)
    if match_re:
        x_num = int(match_re.group(1))
    else:
        x_num = 0
    return x_num


# 删除文章正文的所有html标签
def remove_tags(value):
    return re.sub(r"<.*?>", "", value).strip()


# 去掉tag中的评论
def remove_comment_tag(value):
    if "评论" in value:
        return ""
    else:
        return value


# 处理front_image_url, 什么也不做, 只返回值
def return_value(value):
    return value


def get_md5(url):
    # 如果url是以unicode字符串, 就把它进行utf-8的编码, 转换为bytes类型
    if isinstance(url, str):
        url = url.encode("utf-8")
    m = hashlib.md5()
    m.update(url)
    return m.hexdigest()

# 替换正文中出现的无法使用utf-8编码的文字
def replace_unknown(value):
    return value.replace("\xa0", "")

# 为了使原来jobbole.py中的item依旧可用, 这里新建一个item, 并在jobbole_it.py中使用
class JobboleArticleProcessItem(scrapy.Item):
    title = scrapy.Field()
    # 文章的发表时间, 这里不把字符串转换为时间格式, 而是使用mysql的自动转换功能. 也能避免时期无法使用josn序列化的问题.
    create_date = scrapy.Field(
        input_processor=MapCompose(remove_dot)
    )
    # 文章详情的url
    article_url = scrapy.Field()
    # url是变长的, 通过md5把它变成固定长度的.
    url_object_id = scrapy.Field(
        input_processor=MapCompose(get_md5)
    )
    # 封面图的url地址
    # 由于在下载图片时必须要传递一个列表, 所以要对front_image_url单独使用output_processor, 以覆盖JobboleArticleItemLoader中默认的output_processor
    front_image_url = scrapy.Field(
        output_processor=MapCompose(return_value)
    )
    # 封面图在本地保存的路径. 
    front_image_path = scrapy.Field()

    # 对于没有点赞数量的帖子, 不能提取出数据, 也就不能进入到input_processor中进行处理, 所以在数据库写入时使用get方法从item中取出数据..
    praise_num = scrapy.Field(
        input_processor=MapCompose(get_num)
    )
    fav_num = scrapy.Field(
        input_processor=MapCompose(get_num)
    )
    comment_num = scrapy.Field(
        input_processor=MapCompose(get_num)
    )
    content = scrapy.Field(
        input_processor=MapCompose(remove_tags, replace_unknown)
    )
    tags = scrapy.Field(
        input_processor=MapCompose(remove_comment_tag),
        # 对tags单独设置output_processor, 这样就能覆盖掉JobboleArticleItemLoader默认的default_output_processor
        # 查看Join()的源码, 它的参数是seperator, 即连接符, 在这里把它设置成","
        output_processor=Join(",")
    )


# 自定义item_loader, 继承于ItemLoader.
class JobboleArticleItemLoader(ItemLoader):
    # 查看ItemLoader的源码, 其中可以设置一个default_output_processor
    """
    class ItemLoader(object):

        default_item_class = Item
        default_input_processor = Identity()
        default_output_processor = Identity()
        default_selector_class = Selector

    """
    default_output_processor = TakeFirst()
