import hashlib


def get_md5(url):
    #如果url是以unicode字符串, 就把它进行utf-8的编码, 转换为bytes类型
    if isinstance(url, str):
        url = url.encode("utf-8")
    m = hashlib.md5()
    m.update(url)
    return m.hexdigest()


if __name__ == '__main__':
    # 进行hash的字符串必须要先进行utf-8的编码, 才能对它进行hash操作
    print(get_md5("http://jobbole.com".encode("utf-8")))