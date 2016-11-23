#!usr/bin/python
#_*_ coding:utf-8 _*_
import  re, datetime, threading, urllib, os, mimetypes,cgi,logging,functools,types,sys,traceback
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
ctx = threading.local()

class Dict(dict):
    '''
    Simple dict but support access as x.y style

    >>> d1 = Dict()
    >>> d1['x'] = 100
    >>> d1.x
    100
    >>> d1.y = 200
    >>> d1['y']
    200
    >>> d2 = Dict(a=1, b=2, c='3')
    >>> d2.c
    '3'
    >>> d2.empty
    Traceback (most recent call last):
        ...
    AttributeError: 'Dict' object has no attribute 'empty'
    '''
    def __init__(self, names=(),values=(),**kwargs):
        super(Dict, self).__init__(**kwargs)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)
    def __setattr__(self, key, value):
        self[key] = value
_TIMEDELTA_ZERO = datetime.timedelta(0)
_RE_TZ = re.compile('^([\+\-])([0-9]{1,2})\:([0-9]{1,2})$')
class UTC(datetime.tzinfo):
    '''
    A UTC tzinfo object.
    >>> tz0 = UTC('+00:00')
    >>> tz0.tzname(None)
    'UTC+00:00'
    >>> tz8 = UTC('+8:00')
    >>> tz8.tzname(None)
    'UTC+8:00'
    >>> tz7 = UTC('-07:00')
    >>> tz7.tzname(None)
    'UTC-07:00'
    '''
    def __init__(self, utc):
        utc = str(utc.strip().upper())
        mt = _RE_TZ.match(utc)
        if mt:
            minus = mt.group(1)=='-'
            h = int(mt.group(2))
            m = int(mt.group(3))
            if minus:
                h, m = (-h), (-m)
            self._utcoffset = datetime.timedelta(hours=h, minutes=m)
            self._tzname = 'UTC%s' % utc

        else:
            raise ValueError('bad utc time zone')
    def utcoffset(self, date_time):
        return self._utcoffset
    def dst(self, date_time):
        return _TIMEDELTA_ZERO
    def tzname(self, date_time):
        return self._tzname
    def __str__(self):
        return 'UTC tzinfo object (%s)' % self._tzname
    __repr__ = __str__

_RESPONSE_STATUSES = {
    # Informational
    100: 'Continue',
    101: 'Switching Protocols',
    102: 'Processing',

    # Successful
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    207: 'Multi Status',
    226: 'IM Used',

    # Redirection
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',

    # Client Error
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: "I'm a teapot",
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    426: 'Upgrade Required',

    # Server Error
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    507: 'Insufficient Storage',
    510: 'Not Extended',
}

_RE_RESPONSE_STATUS = re.compile(r'^\d\d\d(\ [\w\ ]+)?$')
_RESPONSE_HEADERS = (
    'Accept-Ranges',
    'Age',
    'Allow',
    'Cache-Control',
    'Connection',
    'Content-Encoding',
    'Content-Language',
    'Content-Length',
    'Content-Location',
    'Content-MD5',
    'Content-Disposition',
    'Content-Range',
    'Content-Type',
    'Date',
    'ETag',
    'Expires',
    'Last-Modified',
    'Link',
    'Location',
    'P3P',
    'Pragma',
    'Proxy-Authenticate',
    'Refresh',
    'Retry-After',
    'Server',
    'Set-Cookie',
    'Strict-Transport-Security',
    'Trailer',
    'Transfer-Encoding',
    'Vary',
    'Via',
    'Warning',
    'WWW-Authenticate',
    'X-Frame-Options',
    'X-XSS-Protection',
    'X-Content-Type-Options',
    'X-Forwarded-Proto',
    'X-Powered-By',
    'X-UA-Compatible',
)
_RESPONSE_HEADER_DICT = dict(zip(map(lambda x: x.upper(), _RESPONSE_HEADERS), _RESPONSE_HEADERS))
_HEADER_X_POWER_Y = ('X-powered-By', 'transwrap/1.0')
class HTTPError(Exception):
    '''
    httpError that define http error.
    >>> e = HTTPError(404)
    >>> e.status
    '404 Not Found'
    '''
    def __init__(self, code):
        super(HTTPError, self).__init__()
        self.status = '%d %s' % (code, _RESPONSE_STATUSES[code])
    def header(self, name, value):
        if not hasattr(self, '_headers'):
            self._headers = [_HEADER_X_POWER_Y]
        self._headers.append((name,value))
    @property
    def headers(self):
        if hasattr(self,'_headers'):
            return self._headers
        return []
    def __str__(self):
        return self.status
    __repr__ = __str__
class RedirectError(HTTPError):
    '''
    RedirectError that defines http error redirect code.
    >>> e = RedirectError(302, 'http://www.apple.com/')
    >>> e.status
    '302 Found'
    >>> e.location
    'http://www.apple.com/'
    '''
    def __init__(self, code, location):
        super(RedirectError, self).__init__(code)
        self.location = location
    def __str__(self):
        return "%s, %s" % (self.status, self.location)
    __repr__ = __str__
def badrequest():
    '''
    send a bad request response.
    >>> raise badrequest()
    Traceback (most recent call last):
        ...
    HTTPError: 400 Bad Request
    '''
    return HTTPError(400)
def unauthorized():
    '''
    send an unauthorized request'
    >>> raise unauthorized()
    Traceback (most recent call last):
        ...
    HTTPError: 401 Unauthorized
    '''
    return HTTPError(401)
def forbidden():
    '''
    send a forbidden response
    >>> raise forbidden()
    Traceback (most recent call last):
        ...
    HTTPError: 403 Forbidden
    '''
    return HTTPError(403)
def notfound():
    '''
    send a not found response.
    >>> raise notfound()
    Traceback (most recent call last):
        ...
    HTTPError: 404 Not Found
    '''
    return HTTPError(404)
def conflict():
    '''
    send a conflict response.
    >>> raise conflict()
    Traceback (most recent call last):
        ...
    HTTPError: 409 Conflict
    '''
    return HTTPError(409)
def internalerror():
    '''
    Send an internal error response.
    >>> raise internalerror()
    Traceback (most recent call last):
        ...
    HTTPError: 500 Internal Server Error
    '''
    return HTTPError(500)
def redirect(location):
    '''
    Do permanent redirect.
    >>> raise redirect('http://www.itranswrap.com/')
    Traceback (most recent call last):
        ...
    RedirectError: 301 Moved Permanently, http://www.itranswrap.com/
    '''
    return RedirectError(301,location)
def found(location):
    '''
    Do temporary redirect
    >>> raise found('http://www.itranswrap.com')
    Traceback (most recent call last):
        ...
    RedirectError: 302 Found, http://www.itranswrap.com
    '''
    return RedirectError(302, location)
def seeother(location):
    '''
    Do temporary redirect
    >>> raise seeother('http://www.itranswrap.com/')
    Traceback (most recent call last):
        ...
    RedirectError: 303 See Other, http://www.itranswrap.com/
    '''
    return RedirectError(303, location)
def _to_str(s):
    '''
    convert to str
    >>> _to_str('s123') == 's123'
    True
    >>> _to_str(u'\u4e2d\u6587') == '\xe4\xb8\xad\xe6\x96\x87'
    True
    >>> _to_str(-123) == '-123'
    True
    '''
    if isinstance(s, str):
        return s
    if isinstance(s, unicode):
        return s.encode('utf-8')
    return str(s)
def _to_unicode(s, encoding = 'utf-8'):
    '''
    Convert to unicode
    >>> _to_unicode('\xe4\xb8\xad\xe6\x96\x87') == u'\u4e2d\u6587'
    True
    '''
    return s.decode('utf-8')
def quote(s,encoding='utf-8'):
    '''
    Url quote as str.
    >>> quote('http://example/test?a=1+')
    'http%3A//example/test%3Fa%3D1%2B'
    >>> quote(u'hello world!')
    'hello%20world%21'
    '''
    if isinstance(s, unicode):
        s = s.encode(encoding)
    return urllib.quote(s)
def _unquote(s, encoding='utf-8'):
    '''
    url unquote as unicode
    >>> _unquote('http%3A//example/test%3Fa%3D1+')
    u'http://example/test?a=1+'
    '''
    return urllib.unquote(s).decode(encoding)
def get(path):
    '''
    A @get decorator
    >>> @get('/test/:id')
    ... def test():
    ...     return 'ok'
    ...
    >>> test.__web_router__
    '/test/:id'
    >>> test.__web_method__
    'GET'
    >>> test()
    'ok'
    '''
    def _decorator(func):
        func.__web_router__ = path
        func.__web_method__ = 'GET'
        return func
    return _decorator
def post(path):
    '''
    A @post decorator.
    >>> @post('/post/:id')
    ... def testpost():
    ...     return '200'
    ...
    >>> testpost.__web_router__
    '/post/:id'
    >>> testpost.__web_method__
    'POST'
    >>> testpost()
    '200'
    '''
    def _decorator(func):
        func.__web_router__ = path
        func.__web_method__ = 'POST'
        return func
    return _decorator
_re_router = re.compile(r'(\:[a-zA-Z_]\w*)')
def _build_regex(path):
    r'''
    Convert route path to regex.
    >>> _build_regex('/path/to/:file')
    '^\\/path\\/to\\/(?P<file>[^\\/]+)$'
    >>> _build_regex('/:user/:comments/list')
    '^\\/(?P<user>[^\\/]+)\\/(?P<comments>[^\\/]+)\\/list$'
    '''
    re_list = ['^']
    var_list = []
    is_var = False
    for v in _re_router.split(path):
        if is_var:
            var_name = v[1:]
            var_list.append(var_name)
            re_list.append(r'(?P<%s>[^\/]+)'%var_name)
        else:
            s = ''
            for ch in v:
                if ch>='0' and ch<='9':
                    s = s +ch
                elif ch>='a' and ch<='z':
                    s = s+ch
                elif ch>='A' and ch<='Z':
                    s = s+ch
                else:
                    s = s +'\\' +ch
            re_list.append(s)
        is_var = not is_var
    re_list.append('$')
    return ''.join(re_list)
class Route(object):
    def __init__(self, func):
        self.path = func.__web_router__
        self.method = func.__web_method__
        self.is_static = _re_router.search(self.path) is None
        if not self.is_static:
            self.route = re.compile(_build_regex(self.path))
        self.func = func
    def match(self,url):
        m = self.route.match(url)
        if m:
            return m.groups()
        return None
    def __call__(self, *args):
        return self.func(*args)
    def __str__(self):
        if self.is_static:
            return 'Route(static,%s,path=%s)' % (self.method,self.path)
        return 'Route(dynamic,%s,path=%s)' %(self.method,self.path)
    __repr__ = __str__

def _static_file_generate(fpath):
    BLOCK_SIZE = 8192
    with open(fpath,'rb') as f:
        block = f.read(BLOCK_SIZE)
        while block:
            yield block
            block = f.read(BLOCK_SIZE)
class StaticFileRoute(object):
    def __init__(self):
        self.method = 'GET'
        self.is_static = False
        self.route = re.compile('^/static/(.+)$')
    def match(self,url):
        if url.startswith('/static/'):
            return (url[1:],)
        return None
    def __call__(self, *args):
        fpath = os.path.join(ctx.application.document_root, args[0])
        if not os.path.isfile(fpath):
            raise notfound()
        fext = os.path.splitext(fpath)[1]
        ctx.response.content_type = mimetypes.types_map.get(fext.lower(),'application/octet-stream')
        return _static_file_generate(fpath)
class MulitipartFile():
    def __init__(self,storage):
        self.filename = _to_unicode(storage.filename)
        self.file = storage.file
class Request(object):
    def __init__(self, environ):
        self._environ = environ
    def _parse_input(self):
        def _convert(item):
            if isinstance(item,list):
                return [_to_unicode(i.value) for i in item]
            if item.filename:
                return MulitipartFile(item)
            return _to_unicode(item.value)
        fs = cgi.FieldStorage(fp=self._environ['wsgi.input'],environ=self._environ,keep_blank_values=True)
        input = dict()
        for keys in fs:
            input[keys] = _convert(fs[keys])
        return input
    def _get_raw_input(self):
        if not hasattr(self,'_raw_input'):
            self._raw_input = self._parse_input()
        return self._raw_input
    def __getitem__(self,key):
        '''Get input parameter value.
        >>> from StringIO import StringIO
        >>> r = Request({'REQUEST_METHOD':'POST', 'wsgi.input':StringIO('a=1&b=M%20M&c=ABC&c=XYZ&e=')})
        >>> r['a']
        u'1'
        >>> r['c']
        u'ABC'
        >>> b = '----WebKitFormBoundaryQQ3J8kPsjFpTmqNz'
        >>> pl = ['--%s' % b, 'Content-Disposition: form-data; name=\\"name\\"\\n', 'Scofield', '--%s' % b, 'Content-Disposition: form-data; name=\\"name\\"\\n', 'Lincoln', '--%s' % b, 'Content-Disposition: form-data; name=\\"file\\"; filename=\\"test.txt\\"', 'Content-Type: text/plain\\n', 'just a test', '--%s' % b, 'Content-Disposition: form-data; name=\\"id\\"\\n', '4008009001', '--%s--' % b, '']
        >>> payload = '\\n'.join(pl)
        >>> r = Request({'REQUEST_METHOD':'POST', 'CONTENT_LENGTH':str(len(payload)), 'CONTENT_TYPE':'multipart/form-data; boundary=%s' % b, 'wsgi.input':StringIO(payload)})
        >>> r.get('name')
        u'Scofield'
        >>> r.gets('name')
        [u'Scofield', u'Lincoln']
        >>> f = r.get('file')
        >>> f.filename
        u'test.txt'
        >>> f.file.read()
        'just a test'
        '''
        r = self._get_raw_input()[key]
        if isinstance(r,list):
            return r[0]
        return r
    def get(self, key, default=None):
        '''
        The same as request[key], but return default value if key is not found
        >>> from StringIO import StringIO
        >>> r=Request({'REQUEST_METHOD':'POST', 'wsgi.input':StringIO('a=1&b=M%20M&c=ABC&c=XYZ&e=')})
        >>> r.get('a')
        u'1'
        >>> r.get('empty')
        >>> r.get('empty', 'DEFAULT')
        'DEFAULT'
        '''
        r = self._get_raw_input().get(key,default)
        if isinstance(r,list):
            return r[0]
        return r
    def gets(self,key):
        '''
        Get multiple values for specified key.
        >>> from StringIO import StringIO
        >>> r = Request({'REQUEST_METHOD':'POST', 'wsgi.input':StringIO('a=1&b=M%20M&c=ABC&c=XYZ&e=')})
        >>> r.gets('a')
        [u'1']
        >>> r.gets('c')
        [u'ABC', u'XYZ']
        '''
        r = self._get_raw_input()[key]
        if isinstance(r,list):
            return r[:]
        return [r]
    def input(self,**kwargs):
        '''
        Get input as dict from request, fill dict using provided default value if key not exist.
        >>> from StringIO import StringIO
        >>> r = Request({'REQUEST_METHOD':'POST', 'wsgi.input':StringIO('a=1&b=M%20M&c=ABC&c=XYZ&e=')})
        >>> i = r.input(x=2008)
        >>> i.a
        u'1'
        >>> i.b
        u'M M'
        >>> i.c
        u'ABC'
        >>> i.x
        2008
        >>> i.get('d', u'100')
        u'100'
        >>> i.x
        2008
        '''
        copy = Dict(**kwargs)
        raw = self._get_raw_input()
        for k,v in raw.iteritems():
            copy[k] = v[0] if isinstance(v,list) else v
        return copy
    def get_body(self):
        '''
        Get raw data from HTTP POST and return as str.
        >>> from StringIO import StringIO
        >>> r = Request({'REQUEST_METHOD':'POST', 'wsgi.input':StringIO('<xml><raw/>')})
        >>> r.get_body()
        '<xml><raw/>'
        '''
        fp = self._environ['wsgi.input']
        return fp.read()
    @property
    def remote_addr(self):
        '''
        Get remote addr. Return '0.0.0.0' if can't get remote_addr.
        >>> r = Request({'REMOTE_ADDR': '192.168.0.100'})
        >>> r.remote_addr
        '192.168.0.100'
        '''
        return self._environ.get('REMOTE_ADDR','0.0.0.0')
    @property
    def document_root(self):
        '''
        Get raw document_root as str. Return '' if not document_root
        >>> r = Request({'DOCUMENT_ROOT': '/srv/path/to/doc'})
        >>> r.document_root
        '/srv/path/to/doc'
        '''
        return self._environ.get('DOCUMENT_ROOT','')
    @property
    def query_string(self):

        return self._environ.get('QUERY_STRING','')
    @property
    def environ(self):
        '''
        Get raw environ as dict. both key, value are str.
        >>> r = Request({'REQUEST_METHOD': 'GET', 'wsgi.url_scheme':'http'})
        >>> r.environ.get('REQUEST_METHOD')
        'GET'
        >>> r.environ.get('wsgi.url_scheme')
        'http'
        '''
        return self._environ
    @property
    def request_method(self):
        return self._environ['REQUEST_METHOD']
    @property
    def path_info(self):
        return urllib.unquote(self._environ.get('PATH_INFO',''))
    @property
    def host(self):
        return self._environ.get('HTTP_HOST','')
    def _get_headers(self):
        if not hasattr(self,'_headers'):
            hdrs = {}
            for k,v in self._environ.iteritems():
                if k.startswith('HTTP_'):
                    hdrs[k[5:].replace('_','-').upper()] = v.decode('utf-8')
            self._headers = hdrs
        return self._headers
    @property
    def headers(self):
        '''
        Get all HTTP headers with key as str and value as unicode. The header names are 'XXX-XXX' uppercase.
        >>> r = Request({'HTTP_USER_AGENT': 'Mozilla/5.0', 'HTTP_ACCEPT': 'text/html'})
        >>> H = r.headers
        >>> H['ACCEPT']
        u'text/html'
        >>> H['USER-AGENT']
        u'Mozilla/5.0'
        >>> L = H.items()
        >>> L.sort()
        >>> L
        [('ACCEPT', u'text/html'), ('USER-AGENT', u'Mozilla/5.0')]
        '''
        return dict(**self._get_headers())
    def header(self, header, default=None):
        return self._get_headers().get(header.upper(),default)
    def _get_cookies(self):
        if not hasattr(self,'_cookies'):
            cookies={}
            cookie_str = self._environ.get('HTTP_COOKIE')
            if cookie_str:
                for c in cookie_str.split(';'):
                    pos = c.find('=')
                    if pos>0:
                        cookies[c[:pos].strip()]= _unquote(c[pos+1:])
            self._cookies = cookies
        return self._cookies
    @property
    def cookies(self):
        '''
        Return all cookies as dict. The cookie name is str and values is unicode.
        >>> r = Request({'HTTP_COOKIE':'A=123; url=http%3A%2F%2Fwww.example.com%2F'})
        >>> r.cookies['A']
        u'123'
        >>> r.cookies['url']
        u'http://www.example.com/'
        '''
        return Dict(**self._get_cookies())
    def cookie(self,name,default=None):
        '''
        Return specified cookie value as unicode. Default to None if cookie not exists.
        >>> r = Request({'HTTP_COOKIE':'A=123; url=http%3A%2F%2Fwww.example.com%2F'})
        >>> r.cookie('A')
        u'123'
        >>> r.cookie('url')
        u'http://www.example.com/'
        >>> r.cookie('test')
        >>> r.cookie('test', u'DEFAULT')
        u'DEFAULT'
        '''
        return self._get_cookies().get(name,default)
UTC_0 = UTC('+00:00')
class Response(object):
    def __init__(self):
        self._status = '200 OK'
        self._headers = {'CONTENT-TYPE':'text/html; charset=utf-8'}
    @property
    def headers(self):
        '''
        Return response headers as [(key1, value1), (key2, value2)...] including cookies.
        >>> r = Response()
        >>> r.headers
        [('Content-Type', 'text/html; charset=utf-8'), ('X-powered-By', 'transwrap/1.0')]
        >>> r.set_cookie('s1', 'ok', 3600)
        >>> r.headers
        [('Content-Type', 'text/html; charset=utf-8'), ('Set-Cookie', 's1=ok; Max-Age=3600; Path=/; HttpOnly'), ('X-powered-By', 'transwrap/1.0')]
        '''
        L = [(_RESPONSE_HEADER_DICT.get(k,k), v) for k,v in self._headers.iteritems()]
        if hasattr(self,'_cookies'):
            for v in self._cookies.itervalues():
                L.append(('Set-Cookie',v))
        L.append(_HEADER_X_POWER_Y)
        return L
    def header(self,name):
        '''
        Get header by name, case-insensitive.
        >>> r = Response()
        >>> r.header('content-type')
        'text/html; charset=utf-8'
        >>> r.header('CONTENT-type')
        'text/html; charset=utf-8'
        >>> r.header('X-Powered-By')
        '''
        key = name.upper()
        if not key in _RESPONSE_HEADER_DICT:
            key = name
        return self._headers.get(key)
    def unset_header(self,name):
        '''
        Unset header by name and value.
        >>> r = Response()
        >>> r.header('content-type')
        'text/html; charset=utf-8'
        >>> r.unset_header('CONTENT-type')
        >>> r.header('content-type')
        '''
        key = name.upper()
        if not key in _RESPONSE_HEADER_DICT:
            key = name
        if key in _RESPONSE_HEADER_DICT:
            del self._headers[key]
    def set_header(self,name,value):
        key = name.upper()
        if not key in _RESPONSE_HEADER_DICT:
            key = name
        self._headers[key] = _to_str(value)
    @property
    def content_type(self):
        return self.header('CONTENT-TYPE')
    @content_type.setter
    def content_type(self,value):
        if value:
            self.set_header('CONTENT-TYPE',value)
        else:
            self.unset_header('CONTENT-TYPE')
    @property
    def content_length(self):
        return self.header('CONTENT-LENGTH')
    @content_length.setter
    def content_length(self,value):
        self.set_header('CONTENT-LENGTH',str(value))
    def delete_cookie(self,name):
        self.set_cookie(name,'__deleted__',expires=0)

    def set_cookie(self,name,value,max_age=None,expires=None,path='/',domain = None,secure=False,http_only=True):
        if not hasattr(self,'_cookies'):
            self._cookies = {}
        L = ["%s=%s"%(quote(name),quote(value))]
        if expires is not None:
            if isinstance(expires,(float,int,long)):
                L.append('Expires=%s'% datetime.datetime.fromtimestamp(expires,UTC_0).strftime('%a, %d-%b-%Y %H:%M:%S GMT'))
            if isinstance(expires,(datetime.date, datetime.datetime)):
                L.append('Expires=%s' % expires.astimezone(UTC_0).strftime('%a, %d-%b-%Y %H:%M:%S GMT'))
        elif isinstance(max_age,(int,long)):
            L.append(' Max-Age=%s' % max_age)
        L.append(' Path=%s'%path)
        if domain:
            L.append(' Domain =%s'%domain)
        if secure:
            L.append(' Secure=%s'%secure)
        if http_only:
            L.append(' HttpOnly')
        self._cookies[name] = ';'.join(L)
    def unset_cookie(self, name):
        if hasattr(self,'_cookies'):
            if name in self._cookies:
                del self._cookies[name]
    @property
    def status_code(self):
        return self._status[:3]
    @property
    def status(self):
        return self._status
    @status.setter
    def status(self,value):
        if isinstance(value,(int,long)):
            if value>=100 and value<=999:
                st = _RESPONSE_STATUSES.get(value,'')
                if st:
                    self._status = '%d %s' %(value,st)
                else:
                    self._status = str(value)
            else:
                raise ValueError('Bad response code %d'%value)
        elif isinstance(value,basestring):
            if isinstance(value,unicode):
                value = value.encode('utf-8')
            if _RE_RESPONSE_STATUS.match(value):
                self._status = value
            else:
                raise ValueError('Bad response code %s'%value)
        else:
            raise ValueError('Bad type of response code')


class Template(object):
    def __init__(self, template_name,**kwargs):
        self.template_name=template_name
        self.model = dict(**kwargs)


class TemplateEngine(object):
    def __call__(self, path, model):
        return '<!-- override this method to render template--!>'


class Jinja2TemplateEngine(TemplateEngine):
    '''
    Render using jinja2 template engine.

    >>> templ_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test')
    >>> engine = Jinja2TemplateEngine(templ_path)
    >>> engine.add_fliter('datetime', lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S'))
    >>> engine('jinja2-test.html', dict(name='Michael', posted_at=datetime.datetime(2014, 6, 1, 10, 11, 12)))
    '<p>Hello, Michael.</p><span>2014-06-01 10:11:12</span>'
    '''
    def __init__(self,template_dir,**kwargs):
        from jinja2 import Environment, FileSystemLoader
        if not 'autoescape' in kwargs:
            kwargs['autoescape'] = True
        self._env = Environment(loader=FileSystemLoader(template_dir), **kwargs)

    def add_fliter(self, name, fn_filter):
        self._env.filters[name] = fn_filter

    def __call__(self, path, model):
        return self._env.get_template(path).render(**model).encode('utf-8')
def _debug():
    pass
def _default_error_handle(e,start_response, is_debug):
    if isinstance(e,HTTPError):
        logging.info('HTTPERROR %s'% e.status)
        headers = e.headers[:]
        headers.append(('Content-Type','text/html'))
        start_response(e.status,headers)
        return ('<html><body><h1></h1>%s</h1></body></html>' % e.status)
    logging.exception('Exception:')
    start_response('500 Internal Server Error',[('content-Type','text/html'),_HEADER_X_POWER_Y])
    if is_debug:
        return _debug()
    return ('<html><body><h1>500 Internal Server Error</h1><h3>%s</h3></body></html>'%str(e))
def view(path):
    def _decorator(func):
        @functools.wraps(func)
        def _wrapper(*args,**kwargs):
            r = func(*args,**kwargs)
            if isinstance(r, dict):
                logging.info('return Template')
                return Template(path,**r)
            raise ValueError('Except return a dict when using @view() decorator')
        return _wrapper
    return _decorator
_RE_ENTERCEPTROR_STARTS_WITH = re.compile(r'^([^\*\?]+)\*?$')
_RE_ENTERCEPTROR_ENDS_WITH = re.compile(r'^\*([^\*\?]+)$')


def _build_pattern_fn(pattern):
    m = _RE_ENTERCEPTROR_STARTS_WITH.match(pattern)
    if m:
        return lambda p: p.startswith(m.group(1))
    m = _RE_ENTERCEPTROR_ENDS_WITH.match(pattern)
    if m:
        return lambda p: p.endswith(m.group(1))
    raise ValueError('Invaild pattern definition in interceptor')


def interceptor(pattern='/'):
    def _decorator(func):
        func.__interceptor__=_build_pattern_fn(pattern)
        return func
    return _decorator


def _build_interceptor_fn(func, next):
    def _wrapper():
        if func.__interceptor__(ctx.request.path_info):
            return func(next)
        else:
            return next()
    return _wrapper




def _build_interceptor_chain(last_fn, *interceptor):
    '''
    Build interceptor chain.

    >>> def target():
    ...     print 'target'
    ...     return 123
    >>> @interceptor('/')
    ... def f1(next):
    ...     print 'before f1()'
    ...     return next()
    >>> @interceptor('/test/')
    ... def f2(next):
    ...     print 'before f2()'
    ...     try:
    ...         return next()
    ...     finally:
    ...         print 'after f2()'
    >>> @interceptor('/')
    ... def f3(next):
    ...     print 'before f3()'
    ...     try:
    ...         return next()
    ...     finally:
    ...         print 'after f3()'
    >>> chain = _build_interceptor_chain(target, f1, f2, f3)
    >>> ctx.request = Dict(path_info='/test/abc')
    >>> chain()
    before f1()
    before f2()
    before f3()
    target
    after f3()
    after f2()
    123
    >>> ctx.request = Dict(path_info='/api/')
    >>> chain()
    before f1()
    before f3()
    target
    after f3()
    123
    '''
    L = list(interceptor)
    L.reverse()
    fn = last_fn
    for f in L:
        fn = _build_interceptor_fn(f, fn)
    return fn


def load_moudle(module_name):
    last_doat = module_name.rfind('.')
    if last_doat==(-1):
        return __import__(module_name,globals(),locals())
    from_module = module_name[:last_doat]
    import_module = module_name[last_doat+1:]
    m = __import__(module_name,globals(),locals(),[import_module])
    return getattr(m,import_module)
class WSGIApplication(object):
    def __init__(self,document_root=None,**kwargs):
        self._running = False
        self._document_root = document_root
        self._interceptors=[]
        self._template_engine = None
        self._get_static = {}
        self._post_static = {}
        self._get_dynamic = []
        self._post_dynamic = []

    def _check_not_running(self):
        if self._running:
            raise RuntimeError('Cannot modify WSGIApplication when running.')

    @property
    def template_enginer(self):
        return self._template_engine

    @template_enginer.setter
    def template_enginer(self,engine):
        self._check_not_running()
        self._template_engine = engine

    def add_module(self,mod):
        self._check_not_running()
        m = mod if type(mod) == types.ModuleType else load_moudle(mod)
        logging.info('Add module: %s' % m.__name__)
        for name in dir(m):
            fn = getattr(m,name)
            if callable(fn) and hasattr(fn,'__web_router__') and hasattr(fn,'__web_method__'):
                self.add_url(fn)

    def add_url(self,func):
        self._check_not_running()
        route = Route(func)
        if route.is_static:
            if route.method == 'GET':
                self._get_static[route.path] = route
            if route.method =='POST':
                self._post_static[route.path] = route
        else:
            if route.method == 'GET':
                self._get_dynamic.append(route)
            if route.method == 'POST':
                self._post_dynamic.append(route)
        logging.info('Add route: %s'%str(route))

    def add_interceptor(self,func):
        self._check_not_running()
        self._interceptors.append(func)
        logging.info('Add interceptor: %s' % str(func))

    def run(self,port=9001,host='127.0.0.1'):
        from wsgiref.simple_server import make_server
        logging.info('application (%s) will start at %s:%s...'%(self._document_root, host, port))
        server_web = make_server(host,port,self.get_wsgi_application(debug=True))
        server_web.serve_forever()

    def get_wsgi_application(self, debug=False):
        self._check_not_running()
        if debug:
            self._get_dynamic.append(StaticFileRoute())
        self._running = True
        _application = Dict(document_root=self._document_root)

        def fn_router():
            request_method=ctx.request.request_method
            path_info= ctx.request.path_info
            if request_method=='GET':
                fn = self._get_static.get(path_info, None)
                if fn:
                    return fn()
                for fn in self._get_dynamic:
                    args= fn.match(path_info)
                    if args:
                        return fn(*args)
                raise notfound()
            if request_method=='POST':
                fn = self._post_static.get(path_info,None)
                if fn:
                    return fn()
                for fn in self._post_dynamic:
                    args = fn.match(path_info)
                    if args:
                        return fn(*args)
                raise notfound()
            raise badrequest()
        fn_exec=_build_interceptor_chain(fn_router, *self._interceptors)



        def wsgi(env,start_response):
            ctx.application = _application
            ctx.request = Request(env)
            response = ctx.response = Response()
            try:
                r = fn_exec()
                if isinstance(r,Template):
                    r = self._template_engine(r.template_name,r.model)
                if isinstance(r, unicode):
                    r = r.encode('utf-8')
                if r is None:
                    r = []
                start_response(response.status, response.headers)
                return r
            except RedirectError,e:
                response.set_header('Location',e.location)
                start_response(e.status,response.headers)
                return []
            except HTTPError,e:
                start_response(e.status,response.headers)
                return ['<html><body><h1>',e.status,'</h1></body></html>']
            except Exception,e:
                logging.exception(e)
                if not debug:
                    start_response('500 Internal Server Error',[])
                    return ['<html><body><h1>500 Internal Server Error</h1></body></html>']
                exc_type,exc_value,exc_traceback = sys.exc_info()
                fp = StringIO()
                traceback.print_exception(exc_type,exc_value,exc_traceback,file = fp)
                stacks = fp.getvalue()
                fp.close()
                start_response('500 Internal Server Error',[])
                return [
                    r'''<html><body><h1>500 Internal Server Error</h1><div style="font-family:Monaco, Menlo, Consolas, 'Courier New', monospace;"><pre>''',
                    stacks.replace('<','&lt;').replace('>','&gt;'),
                    '</pre></div></body></html>']
            finally:
                del ctx.application
                del ctx.request
                del ctx.response
        return wsgi
if __name__=='__main__':
    sys.path.append('.')
    import doctest
    doctest.testmod()


