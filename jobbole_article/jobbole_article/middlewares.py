# -*- coding: utf-8 -*-

from fake_useragent import UserAgent
import time
import re
import os
import random
from twisted.internet import defer
from twisted.internet.error import TimeoutError, ConnectionRefusedError, ConnectError, ConnectionLost, TCPTimedOutError, ConnectionDone
import logging
import json
import requests

logger = logging.getLogger(__name__)


class RandomFakeUserAgentMiddleware(object):
    def __init__(self, crawler):
        # 调用父类的初始化方法进行初始化. 
        super(RandomFakeUserAgentMiddleware, self).__init__()
        self.ua = UserAgent()

    def process_request(self, request, spider):
        # 处理所有的request, 把它的默认的headers中的user-agent设置为randowm_agent
        request.headers.setdefault('User-Agent', self.ua.random)


# from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware

# 也可以继承自UserAgentMiddleware
# class RandomLocalUserAgentMiddleware(UserAgentMiddleware):
class RandomLocalUserAgentMiddleware(object):

    def __init__(self, user_agent=''):
        super(RandomLocalUserAgentMiddleware, self).__init__()
        self.project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.json_file = os.path.join(self.project_path, "fake_useragent.json")
        with open(self.json_file, "r") as f:
            self.ua_list = json.load(f)
            # 把随机选择的功能放在__init__中, 只能在启动爬虫时随机选择一个user-agent
            # self.user_agent = random.choice(self.ua_list)

    def process_request(self, request, spider):
        self.user_agent = random.choice(self.ua_list)
        request.headers.setdefault('User-Agent', self.user_agent)
        pass


# 从2个不同的api中获取代理
def get_random_ip():
    mogu_api = 'http://piping.mogumiao.com/proxy/api/get_ip_al?appKey=&count=1&expiryDate=0&format=1&newLine=2'

    # '{"code":"3001","msg":"提取频繁请按照规定频率提取!"}'
    # '{"code":"0","msg":[{"port":"35379","ip":"117.60.2.113"}]}'

    xdaili_api = 'http://api.xdaili.cn/xdaili-api//greatRecharge/getGreatIp?spiderId=&orderno=Y&returnType=2&count=1'

    # '{"ERRORCODE":"10055","RESULT":"提取太频繁,请按规定频率提取!"}'
    # '{"ERRORCODE":"0","RESULT":[{"port":"48448","ip":"115.203.196.254"}]}'

    api_list = [mogu_api, xdaili_api]
    # 打乱api_list的顺序, 以免列表中第1个代理使用的次数过多
    random.shuffle(api_list)

    for api in api_list:
        response = requests.get(api)
        js_str = json.loads(response.text)
        # 如果正确提取到了ip地址
        if js_str.get('code') == '0' or js_str.get('ERRORCODE') == '0':
            # 从中取出ip
            for i, j in js_str.items():
                if j != '0':
                    # proxies = { 
                    #     "http": "http://{}:{}".format(j[0].get('ip'), j[0].get('port')), 
                    #     "https": "https://{}:{}".format(j[0].get('ip'), j[0].get('port'))
                    #     }
                    proxies = "http://{}:{}".format(j[0].get('ip'), j[0].get('port'))
                    logger.warning("从 {} 获取了一个代理 {}".format(re.split(r'.c', api)[0], proxies))
                    # print("从{}获取了一个代理{}".format(re.split(r'.c', api)[0], proxies))
                    return proxies
            break
        else:
            # print("提取太频繁, 等待中...")
            logger.warning("api {} 提取太频繁, 等待中".format(api))
            time.sleep(random.randint(5, 10))


def get_random_ua():
    # 从本地读取useragent并随机选择
    project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_file = os.path.join(project_path, "fake_useragent.json")
    with open(json_file, "r") as f:
        ua_list = json.load(f)
        user_agent = random.choice(ua_list)
        # print("当前的user-agent是:%s" % user_agent)
        logger.warning("随机获取了一个ua {}".format(user_agent))
        return user_agent

from twisted.internet.defer import DeferredLock

class RandomUAIPDownloaderMiddleware(object):
    def __init__(self, ua=''):
        # 初始时从api获取代理地址, 并给所有代理都设置为这个代理
        super(RandomUAIPDownloaderMiddleware, self).__init__()
        self.user_agent = get_random_ua()
        self.proxy = get_random_ip()
        self.exception_list = (defer.TimeoutError, TimeoutError, ConnectionRefusedError, ConnectError, ConnectionLost, TCPTimedOutError, ConnectionDone)
        # 设置一个过期的代理集合
        self.blacked_proxies = set()
        self.lock = DeferredLock()

    def process_request(self, request, spider):
        # 把更新代理的操作都放在process_request中进行. 这样, 不论是第一次的请求, 还是
        # 判断request中使用的代理, 如果它不等于当前的代理, 就把它设置为当前的代理
        if request.meta.get('proxy') != self.proxy and self.proxy not in self.blacked_proxies:
            request.headers.setdefault('User-Agent', self.user_agent)
            request.meta["proxy"] = self.proxy
            pass

    def process_response(self, request, response, spider):
        # 如果返回的response状态不是200，这里不再重新返回request对象, 因为很可能是因为无法请求对应的资源.
        # 如http://images2015.cnblogs.com/blog/992994/201703/992994-20170302204433063-1243104447.png 这个图片无法下载, 如果返回request, 所有的线程都会去请求这个图片, 所以这里只记录错误即可.
        if response.status != 200:
            logger.error("{} 响应出错, 状态码为 {}".format(request.url, response.status))
            # return request
        return response

    def process_exception(self, request, exception, spider):


        # 如果出现了上面列表中的异常, 就认为代理失效了. 由于scrapy使用的是异步框架, 所以代理失效时会有很多个请求同时出现上面列表中的异常, 同时进入到这里的代码中执行. 如果按照一般的思路, 把更新代理的操作放在这里, 那么所有异常的请求进入此代码后都要更新代理, 都要向api发送请求获取代理地址, 此时就会出现代理请求太频繁的提示. 
        # 这里使用的方法是, 只要出现了认为是代理失效的异常, 就把请求的proxy和user-agent设置为None, 同时设置另一个条件判断产生异常的代理是否等于self.proxy, 当异常发生时, 必定会有先后的顺序, 第1个异常的请求进入这里时, 满足此条件, 执行下面的代码, 更新self.user_agent和self.proxy. 当以后发生异常的请求再次进入到这里的逻辑时, 因为第1个请求已经更新了self.proxy的值, 就不能满足第2个if判断中的条件, 就不会执行更新代理的操作了, 这样就避免了所有发生异常的请求同时请求api更新代理的情况. 
        if isinstance(exception, self.exception_list):
            logger.info("Proxy {} 链接出错 {}".format(request.meta['proxy'], exception))
            self.lock.acquire()
            # 如果失效的代理不在代理黑名单中, 表示这是这个代理地址第一次失效, 就执行更新代理的操作.
            if request.meta.get('proxy') not in self.blacked_proxies:
                # 如果代理过期, 就把它添加到代理黑名单列表中
                self.blacked_proxies.add(self.proxy)
                print('\n\n')
                print(self.blacked_proxies)
                print('\n\n')
                self.user_agent = get_random_ua()
                self.proxy = get_random_ip()

            self.lock.release()
            request.meta["proxy"] = None
            request.headers.setdefault('User-Agent', None)

        return request.replace(dont_filter=True)
