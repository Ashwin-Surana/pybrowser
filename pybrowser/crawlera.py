import warnings

import requests
from random import choice

from requests.auth import HTTPBasicAuth
from requests.auth import HTTPProxyAuth
from functools import wraps

PROXY_HOST = "proxy.crawlera.com"
PROXY_PORT = "8010"

PROXIES = {"https": "https://{}:{}/".format(PROXY_HOST, PROXY_PORT),
           "http": "http://{}:{}/".format(PROXY_HOST, PROXY_PORT)
           }

DEFAULT_TIMEOUT = 100
REDIRECT_CODES = [301, 302, 303, 307]


def debug(http_method_func):
    @wraps(http_method_func)
    def log(instance, *args, **kwargs):
        response = http_method_func(instance, *args, **kwargs)
        if instance.debug:
            print 'RESPONSE STATUS: ', response.status_code, '  ', response.url
            print 'HEADERS: \n', response.headers
            if response.status_code == 200:
                with open('log.html', 'wb') as html:
                    html.write(response.text.encode('latin-1', 'ignore'))
        return response

    return log


class SessionCreateException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, 'ERROR CREATING A NEW CRAWLERA SESSION: ' + msg)


class SessionDestroyException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, 'ERROR DESTROYING SESSION: ' + msg)


class CrawleraSession(requests.Session):
    def __init__(self, api_key, user_agent=None, cert='crawlera-ca.crt', timeout=DEFAULT_TIMEOUT, debug=False):
        requests.Session.__init__(self)
        self.api_key = api_key
        self.user_agent = user_agent
        self.cert = cert
        self.timeout = timeout
        self.debug = debug
        self.proxy_auth = HTTPProxyAuth(api_key, "")
        self.server_auth = HTTPBasicAuth(api_key, "")
        self.__create_session()

    def __create_session(self):
        url = "http://proxy.crawlera.com:8010/sessions"
        response = requests.post(url, auth=self.server_auth, timeout=self.timeout, verify=self.cert)
        if response.status_code == 200:
            self.session_id = response.text
            self.headers["X-Crawlera-Session"] = response.text
            if self.user_agent is not None:
                self.headers['X-Crawlera-UA'] = 'pass'
                self.headers['User-agent'] = self.user_agent
        else:
            raise Exception("Problem creating session. RESPONSE CODE: " + str(response.status_code))

    @debug
    def get(self, url):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            params = {
                'proxies': PROXIES,
                'auth': self.proxy_auth,
                'timeout': self.timeout,
                'verify': self.cert,
                'allow_redirects' : False
            }
            response = super(CrawleraSession, self).get(url, **params)

            while response.status_code in REDIRECT_CODES:
                if 'location' in response.headers:
                    url = response.headers['location']
                    response = super(CrawleraSession, self).get(url, **params)
                else:
                    break
            return response

    @debug
    def post(self, url, data):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return self.post(url, proxies=PROXIES, auth=self.proxy_auth, data=data, timeout=self.timeout,
                             verify=self.cert, allow_redirects=False)

    def destroy(self):
        url = "http://proxy.crawlera.com:8010/sessions/" + self.session_id
        response = requests.delete(url, auth=self.server_auth, timeout=DEFAULT_TIMEOUT, verify=self.cert)
        if response.status_code != 204:
            raise Exception("Problem destroying session. RESPONSE CODE: " + self.status_code)

    def get_all_sessions(self):
        url = "http://proxy.crawlera.com:8010/sessions"
        response = requests.get(url, auth=self.server_auth, verify=self.cert)
        if response.status_code != 200:
            raise Exception("Problem destroying session. RESPONSE CODE: " + self.status_code)
        return response.json()

    def clear_all_session(self):
        url = "http://proxy.crawlera.com:8010/sessions"
        response = requests.get(url, auth=self.server_auth, verify=self.cert)
        if response.status_code != 200:
            raise Exception("Problem destroying session. RESPONSE CODE: " + self.status_code)
        sessions = response.json()
        for session in sessions.keys():
            url = "http://proxy.crawlera.com:8010/sessions/" + session
            response = requests.delete(url, auth=self.server_auth, timeout=DEFAULT_TIMEOUT, verify=self.cert)
            if response.status_code != 204:
                raise Exception("Problem destroying session. RESPONSE CODE: " + self.status_code)


class Crawlera:
    def __init__(self, api_key, user_agent=None, cert='crawlera-ca.crt', timeout=None, debug=False, max_tries=5):
        self.user_agent = user_agent
        self.max_tries = max_tries
        self.api_key = api_key
        self.timeout = timeout
        self.cert = cert
        self.debug = debug
        self.proxy_auth = HTTPProxyAuth(self.api_key, "")

    @debug
    def get(self, url, **kwargs):
        retry = 0
        with warnings.catch_warnings():
            if self.timeout is not None:
                kwargs['timeout'] = self.timeout
            warnings.simplefilter("ignore")
            response = requests.get(url, proxies=PROXIES, auth=self.proxy_auth, verify=self.cert, **kwargs)
            while response.status_code != 200 and retry < self.max_tries:
                response = requests.get(url, proxies=PROXIES, auth=self.proxy_auth, verify=self.cert, **kwargs)
                retry += 1
                print 'RETRY'
            return response

    @debug
    def post(self, url, data=None, json=None, **kwargs):
        if self.timeout is not None:
            kwargs['timeout'] = self.timeout
        response = requests.post(url, proxies=PROXIES, auth=self.proxy_auth, data=data, json=json,
                                 verify=self.cert)
        return response


class RandomizedCrawlera(Crawlera):
    def __init__(self, api_keys, user_agent=None, cert='crawlera-ca.crt', log=False):
        Crawlera.__init__(self, choice(api_keys), user_agent=user_agent, cert=cert, log=log)
        self.api_keys = api_keys

    def get(self, url, **kwargs):
        self.api_key = choice(self.api_keys)
        return super(RandomizedCrawlera, self).get(url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        self.api_key = choice(self.api_keys)
        return super(RandomizedCrawlera, self).post(url, data, json, **kwargs)


def log_response_info(response):
    print response.status_code, ' ', response.request.url
