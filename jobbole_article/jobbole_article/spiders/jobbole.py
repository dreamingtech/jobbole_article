# -*- coding: utf-8 -*-
import scrapy
import re
from jobbole_article.items import JobboleArticleItem
from jobbole_article.utils.common import get_md5
import datetime


class JobboleSpider(scrapy.Spider):
    # 爬虫的名称 后续启动爬虫是采用此名称
    name = 'jobbole'
    # 爬取允许的域名
    allowed_domains = ['blog.jobbole.com']
    # 起始url列表 , 其中的每个URL会进入下面的parse函数进行解析
    # start_urls = ['http://blog.jobbole.com/45/', 'http://blog.jobbole.com/106093/']
    start_urls = ['http://blog.jobbole.com/all-posts/']

    # 列表页面的解析
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
            article_url = response.css("a.archive-title::attr(href)").extract_first("")
            article_url = response.xpath(".//a[@class='archive-title']/@href").extract_first("")
            # 构建请求对象, 把提取到的文章详情页的url交给parse_detail这个解析函数进行处理. 因为所有文章都可以从all-posts这个列表页获取到, 这里就不需要对链接进行跟进了
            # meta是字典dict类型的, 通过在Request请求对象中添加meta信息来在不同的解析函数之间传递数据. 
            yield scrapy.Request(url=article_url, meta={'front_image_url': front_image_url}, callback=self.parse_detail)
            # 测试代码
            break

        # 提取出了包含下一页的a标签. 使用extract_first就可以避免在最后一页时出错.
        next_url = response.xpath('//a[@class="next page-numbers"]/@href').extract_first('')
        # .next和.page-numbers是属于同一个div的class.
        next_url = response.css('a.next.page-numbers::attr(href)').extract_first('')
        # 如果存在下一页的这个值, 就构建Request对象. 在最后一页时这个值不存在.
        if next_url:
            # 使用回调函数把下一页的url传回到parse函数中重复进行提取. 不用写成self.parse(). scrapy是基于异步处理twisted完成的, 会自动根据函数名来调用函数.
            yield scrapy.Request(url=next_url, callback=self.parse)

    def parse_detail(self, response):
        # 从文章详情页提取信息

        # 从response中的meta中取出文章封面图信息
        front_image_url = response.meta.get('front_image_url', '')

        # 文章标题
        title = response.xpath("//div[@class='entry-header']/h1/text()").extract_first()
        title = response.css("div.entry-header h1::text").extract_first()
        # 发表时间
        create_date = response.xpath('//p[@class="entry-meta-hide-on-mobile"]/text()').extract_first(
            default='1970/01/01').strip().replace("·", "").strip()
        create_date = response.css("p.entry-meta-hide-on-mobile::text").extract_first(
            default='1970/01/01').strip().replace("·", "").strip()
        # 把 create_date 转换为日期格式, 不在这里进行处理, 而是在pipelines.py中写入到mysql数据库之间时处理, 这样就能避免date不能json序列化的问题了.
        # create_date = datetime.datetime.strptime(create_date, "%Y/%m/%d").date()
        # 点赞数量
        praise_num = response.xpath("//span[contains(@class, 'vote-post-up')]/h10/text()").extract_first(default='0')
        praise_num = response.css("span.vote-post-up h10::text").extract_first(default='0')
        # 收藏数量
        fav_num_str = response.xpath("//span[contains(@class, 'bookmark-btn')]/text()").extract_first('')
        fav_num_str = response.css("span.bookmark-btn::text").extract_first('')
        fav_num = re.match(r".*?(\d+).*?", fav_num_str).group(1) if re.match(r".*?(\d+).*?", fav_num_str) else '0'
        # 评论数量
        comment_num_str = response.xpath("//a[@href='#article-comment']/span/text()").extract_first('')
        comment_num_str = response.css("a[href='#article-comment'] span::text").extract_first('')
        comment_num = re.match(r".*?(\d+).*", comment_num_str).group(1) if re.match(r".*?(\d+).*",
                                                                                    comment_num_str) else '0'
        # 文章正文, 除掉所有的标签
        content_str = response.xpath("//div[@class='entry']").extract_first('')
        content_str = response.css("div.entry").extract_first('')
        content = re.sub(r"<.*?>", "", content_str).strip()
        # 文章标签
        tag_list = response.xpath('//p[@class="entry-meta-hide-on-mobile"]/a/text()').extract()
        tag_list = response.css("p.entry-meta-hide-on-mobile a::text").extract()
        # 去除掉评论数, 不能直接删除列表中的第2个元素, 因为没有评论的时候, 是不会产生1评论这个标签的.
        tag_list = [element for element in tag_list if not element.strip().endswith('评论')]
        # 把列表拼接成字符串
        tags = ','.join(tag_list)

        # 实例化article对象
        article_item = JobboleArticleItem(
            title=title,
            create_date=create_date,
            article_url=response.url,
            url_object_id=get_md5(response.url),
            front_image_url=[front_image_url],
            praise_num=praise_num,
            fav_num=fav_num,
            comment_num=comment_num,
            content=content,
            tags=tags
        )

        yield article_item
