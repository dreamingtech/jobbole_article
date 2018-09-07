# -*- coding: utf-8 -*-
import scrapy
from scrapy.loader import ItemLoader
from jobbole_article.items import JobboleArticleProcessItem
from jobbole_article.items import JobboleArticleItemLoader
from scrapy_redis.spiders import RedisSpider


class JobboleItSpider(RedisSpider):
    name = 'jobbole_docker'
    allowed_domains = ["blog.jobbole.com"]
    # start_urls = ['http://blog.jobbole.com/all-posts/']
    redis_key = 'jobbole:start_urls'

    # 自定义设置
    custom_settings = {

        'LOG_LEVEL': 'DEBUG',
        'DOWNLOAD_DELAY': 0,

        # 修改为分布式的爬虫
        # 使用redis的调度器, 确保request存储到redis中
        "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
        # 使用scrapy_redis进行去重, 确保所有爬虫共享相同的去重指纹
        "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",

        # 在redis中保持scrapy-redis用到的队列, 不会清理redis中的队列, 从而可以实现暂停和恢复的功能. 
        "SCHEDULER_PERSIST": True,

        # 指定redis数据库的连接参数
        'REDIS_HOST': '172.17.0.1',
        'REDIS_PORT': 6379,

        # 指定redis数据库的连接参数, 这里使用ubuntu物理机的redis数据库
        'REDIS_PARAMS' : {
            'password': 'Xzz@8481',
            'db': 2
        },

        # 把数据保存到ubuntu物理机中的mysql数据库中.
        'MYSQL_HOST': '172.17.0.1',
        # 这里设置的是数据库的名字, 不是数据表的名字
        'MYSQL_DBNAME': 'jobbole_article',
        'MYSQL_USERNAME': 'root',
        'MYSQL_PASSWORD': 'Xzz@8481',
        'MYSQL_PORT': 3306,

        # 启动redis的pipeline, 把提取到的数据都传输并保存到redis服务器中.
        "ITEM_PIPELINES": {
            # 'jobbole_article.pipelines.JsonWithEncodingPipeline': 300,
            # 'jobbole_article.pipelines.JsonExporterPipeline': 301,
            # 'scrapy.pipelines.images.ImagesPipeline' : 200,
            # 'jobbole_article.pipelines.JobboleImagePipeline': 200,
            # 'jobbole_article.pipelines.MysqlPipeline': 302,
            'jobbole_article.pipelines.MysqlTwistedPipline': 302,
            # 'scrapy_redis.pipelines.RedisPipeline': 300
        },

        # 启用扩展功能, 当爬虫爬取结束时, 空跑5次时自动结束爬虫.
        'EXTENSIONS': {
            'jobbole_article.extensions.CloseSpiderRedis': 100,
        },

        'CLOSE_SPIDER_AFTER_IDLE_TIMES': 5
    }

    def parse(self, response):
        # 从文章列表页获取详情页url

        article_nodes = response.xpath('//div[@class="grid-8"]/div[not(contains(@class, "navigation"))]')
        article_nodes = response.xpath('//div[@class="post floated-thumb"]')
        article_nodes = response.css('div.post.floated-thumb')

        for article_node in article_nodes:
            # 列表页文章图片
            front_image_url = article_node.xpath('.//img/@src').extract_first("")
            front_image_url = article_node.css('img::attr(src)').extract_first("")
            # 列表页文章链接地址
            article_url = article_node.css("a.archive-title::attr(href)").extract_first("")
            article_url = article_node.xpath(".//a[@class='archive-title']/@href").extract_first("")
            # 构建请求对象, 把提取到的文章详情页的url交给parse_detail这个解析函数进行处理. 因为所有文章都可以从all-posts这个列表页获取到, 这里就不需要对链接进行跟进了
            # meta是字典dict类型的, 通过在Request请求对象中添加meta信息来在不同的解析函数之间传递数据. 
            yield scrapy.Request(url=article_url, meta={'front_image_url': front_image_url}, callback=self.parse_detail)
            # 测试代码
            # break

        # 提取出了包含下一页的a标签. 使用extract_first就可以避免在最后一页时出错.
        next_url = response.xpath('//a[@class="next page-numbers"]/@href').extract_first('')
        # .next和.page-numbers是属于同一个div的class.
        next_url = response.css('a.next.page-numbers::attr(href)').extract_first('')
        # 如果存在下一页的这个值, 就构建Request对象. 在最后一页时这个值不存在.
        if next_url:
            # 使用回调函数把下一页的url传回到parse函数中重复进行提取. 不用写成self.parse(). scrapy是基于异步处理twisted完成的, 会自动根据函数名来调用函数.
            yield scrapy.Request(url=next_url, callback=self.parse)

    def parse_detail(self, response):

        # 文章封面图
        front_image_url = response.meta.get("front_image_url", "")

        # 通过item loader加载item
        # item_loader = ItemLoader(item=JobboleArticleProcessItem(), response=response)
        # 使用自定义的itemloader
        item_loader = JobboleArticleItemLoader(item=JobboleArticleProcessItem(), response=response)

        # 通过item_loader的add_css方法加载item
        item_loader.add_css('title', 'div.entry-header h1::text')
        # item_loader.add_xpath('title', '//div[@class="entry-header"]/h1/text()')

        item_loader.add_css('create_date', 'p.entry-meta-hide-on-mobile::text')
        # item_loader.add_xpath('create_date', '//p[@class="entry-meta-hide-on-mobile"]/text()')

        # url的值并不是调用css选择器提取出来的, 而是通过response.url直接传递过来的, 要使用add_value直接添加值的方法. 而add_css则是调用css选择器把值取出来后再传递给前面的字段中. 
        item_loader.add_value('article_url', response.url)
        # 把生成md5值的操作也放在items.py中进行处理
        item_loader.add_value('url_object_id', response.url)
        item_loader.add_value('front_image_url', [front_image_url])

        item_loader.add_css('praise_num', 'span.vote-post-up h10::text')
        # item_loader.add_xpath('praise_num', '//span[contains(@class, "vote-post-up")]/h10/text()')

        item_loader.add_css('fav_num', 'span.bookmark-btn::text')
        # item_loader.add_xpath('fav_num', '//span[contains(@class, "bookmark-btn")]/text()')

        item_loader.add_css('comment_num', 'a[href="#article-comment"] span::text')
        # item_loader.add_xpath('comment_num', '//a[@href="#article-comment"]/span/text()"] span::text')

        item_loader.add_css('content', 'div.entry')
        # item_loader.add_xpath('content', '//div[@class="entry"]')

        item_loader.add_css('tags', 'p.entry-meta-hide-on-mobile a::text')
        # item_loader.add_xpath('tags', '//p[@class="entry-meta-hide-on-mobile"]/a/text()')

        # 写完上面的规则之后要调用item_loader的load_item()方法对以上的规则进行解析. 解析之后就生成了item对象.
        article_item = item_loader.load_item()

        yield article_item
