import requests

from random import *

from urlparse import urlparse
from functools import wraps

USER_AGENTS = [
    r'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:48.0) Gecko/20100101 Firefox/48.0',
    r'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:48.0) Gecko/20100101 Firefox/46.0',
    r'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2490.80 Safari/537.36',
    r'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36',
    r'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36'
]


def header_generator(host=None, user_agent=None):
    header = {
        'User-Agent': choice(USER_AGENTS),
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    if user_agent is not None:
        header['User-Agent'] = user_agent

    if host is not None:
        header["Host"] = host

    return header


def get_host(url):
    parsed_uri = urlparse(url)
    domain = '{uri.netloc}'.format(uri=parsed_uri)
    return domain


def debug(http_method_func):
    @wraps(http_method_func)
    def log(instance, *args, **kwargs):
        response = http_method_func(instance, *args, **kwargs)
        if instance.debug:
            with open('log.html', 'wb') as html:
                html.write(response.text.encode('UTF-8'))
        return response

    return log


class Session(requests.Session):
    def __init__(self, user_agent=None, headers=None, timeout=None, debug=False):
        self.debug = debug
        self.timeout = timeout
        self.user_agent = choice(USER_AGENTS) if user_agent is None else user_agent
        requests.Session.__init__(self)
        if headers is None:
            self.headers = header_generator(user_agent=self.user_agent)
        else:
            headers['User-Agent'] = self.user_agent

    @debug
    def get(self, url, **kwargs):
        if self.timeout is not None:
            kwargs['timeout'] = self.timeout
        self.headers["Host"] = get_host(url)
        response = super(Session, self).get(url, **kwargs)
        response.raise_for_status()
        return response

    @debug
    def post(self, url, data=None, json=None, **kwargs):
        if self.timeout is not None:
            kwargs['timeout'] = self.timeout
        self.headers["Host"] = get_host(url)
        response = super(Session, self).post(url, data=data, json=json, **kwargs)
        response.raise_for_status()
        return response


class Browser:
    def __init__(self, timeout=None, debug=False):
        self.debug = debug
        self.timeout = timeout

    @debug
    def get(self, url, **kwargs):
        if self.timeout is not None:
            kwargs['timeout'] = self.timeout
        response = requests.get(url, headers=header_generator(get_host(url)), **kwargs)
        return response

    @debug
    def post(self, url, data=None, json=None, **kwargs):
        if self.timeout is not None:
            kwargs['timeout'] = self.timeout
        headers = header_generator(get_host(url))
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
            kwargs.pop('headers')
        response = requests.post(url, data=data, json=json, headers=headers, **kwargs)
        return response
