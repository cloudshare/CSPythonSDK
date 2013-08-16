import time, hashlib, json, random, string, sys
try:
    from urllib.request import urlopen
    from urllib.parse import quote
    from urllib.error import HTTPError
except ImportError:
    # try to import python 2.7 functions
    from urllib import quote, urlopen
    from urllib2 import HTTPError    

# make unicode available in python 3
if 'unicode' not in globals():
    unicode = str

def token_generator():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10))

def prettify_json(s):
    try:
        return json.dumps(json.loads(s.decode('utf-8')), False, sort_keys=True, indent=4).replace('\\r', '\r').replace('\\n','\n')
    except:
        return s
    

class ApiException(Exception):
    def __init__(self, content, code):
        self.content = content
        self.code = code

    def __str__(self):
        return "\ncontent:\n\n%s\n\nhttp status code: %d\n\n" % (prettify_json(self.content), self.code)

class ApiResponse(object):
    def __init__(self, content, code):
        self.content = content
        self.code = code

    def pretty_content(self):
        return prettify_json(self.content)

    def json(self):
        try:
            return json.loads(self.content.decode('utf-8'))
        except:
            return { 'content': self.content }


class CSLowApi(object):
    DEFAULT_HOST = "use.cloudshare.com"
    DEFAULT_VERSION = "v2"

    def __init__(self, id, key, version=DEFAULT_VERSION, host=DEFAULT_HOST):
        self.id = id
        self.key = key
        self.version = version
        self.host = host
    
    def call(self, category, command, **params):        
        url = self.gen_url(category, command, params)

        try:
            f = urlopen(url)
            
            if f.code != 200:
                raise ApiException(f.read(), f.code)
        except HTTPError as e:
            raise ApiException(e.read(), e.code)

        return ApiResponse(f.read(), f.code)
    
    def gen_url(self, category, command, params):
        hmac = hashlib.sha1()
        hmac.update(self.key.encode('utf-8'))
        
        if self.version != "v1":
            hmac.update(command.lower().encode('utf-8'))

        params['timestamp'] = str((int)(time.time()))
        params['UserApiId'] = self.id
        
        if self.version != "v1":
            params['token'] = token_generator()
        
        sorted_param_keys = sorted(params.keys(), key=lambda x: unicode.lower(x) if type(x) == unicode else str.lower)
        query = ''
        for pkey in sorted_param_keys:
            pkey_lower = pkey.lower()
            if pkey_lower == "hmac":
                continue

            if query != '': 
                query += '&'

            hmac.update(pkey_lower.encode('utf-8'))
            pvalue = params[pkey]
            query += pkey + '='
            if pvalue and len(pvalue) > 0:
                hmac.update(pvalue.encode('utf-8'))
                query += quote(pvalue.encode('utf-8'))

        return (b'https://' + 
                self.host.encode('utf-8') + 
                b'/Api/' + 
                self.version.encode('utf-8') + b'/' +
                category.encode('utf-8') + b'/' +
                command.encode('utf-8') + b'?' +
                query.encode('utf-8') + b'&HMAC=' + 
                hmac.hexdigest().encode('utf-8')).decode('utf-8')

    def check_keys(self):
        return self.call('ApiTest', 'Ping').json()['data']
        

