# jobbole_article
伯乐在线scrapy-redis+docker分布式爬虫

# 需求分析
爬取某技术博客中所有的文章, 实现分布式并保存数据到mysql中.
# 难点
爬虫代理地址的使用, 由于免费代理的速度和质量都无法保证, 这里使用付费代理. 付费代理一般都有过期时间的限制, 并且可能会被目标网站设置为黑名单, 所以需要解决代理的过期和服务器的拒绝这两个问题. 
这里代理地址使用的方法是每次从代理api获取一个代理地址, 一个爬虫节点上只使用这一个代理直到它过期或被网站封禁, 然后再切换代理. 并且实现了简单高效的方法来判断代理的过期或网站的封禁, 以及解决了多个请求的代理同时过期, 同时向代理api请求获取代理地址的问题.
# 效果
经测试, 2个api代理地址足够5个爬虫节点使用, 可以扩展到10-20个节点. 1.2W个网页耗用的代理数量在20-30个. 某代理网站6块钱购买的1000个代理够爬某个技术博客30遍, 泪奔中...

# 关键代码1, 获取代理地址
```python

# 从2个不同的api中获取代理
def get_random_ip():
    mogu_api = 'http://piping.mogumiao.com/proxy/api/get_ip_al?appKey=04756895ae5b498bb9b985798e990b9f&count=1&expiryDate=0&format=1&newLine=2'

    # '{"code":"3001","msg":"提取频繁请按照规定频率提取!"}'
    # '{"code":"0","msg":[{"port":"35379","ip":"117.60.2.113"}]}'

    xdaili_api = 'http://api.xdaili.cn/xdaili-api//greatRecharge/getGreatIp?spiderId=9b3446e17b004293976e09a081022d73&orderno=YZ20188178415lSPZWO&returnType=2&count=1'

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
                    logger.info("从 {} 获取了一个代理 {}".format(re.split(r'.c', api)[0], proxies))
                    # print("从{}获取了一个代理{}".format(re.split(r'.c', api)[0], proxies))
                    return proxies
            break
        else:
            # print("提取太频繁, 等待中...")
            logger.info("api {} 提取太频繁, 等待中".format(api))
            time.sleep(random.randint(5, 10))

```
# 关键代码2, 实现代理失效时的自动切换, 以及防止多线程(协程)同时更换代理
```
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



```


