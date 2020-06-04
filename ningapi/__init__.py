# Ning XAPI OAuth library
# Copyright (C) 2010-2012 Ning, Inc.
#
# Depends on python-oauth2 -- http://github.com/simplegeo/python-oauth2

import binascii
import httplib2
from . import multipart
import oauth2 as oauth
import socket
import ssl
import urllib.request, urllib.parse, urllib.error

try:
    import json
except ImportError:
    import simplejson as json


class NingError(Exception):
    """Base exception used for all Ning API errors"""

    def __init__(self, status, reason, error_code=None, error_subcode=None,
        trace=None):
        self.status = status
        self.reason = reason
        self.error_code = error_code
        self.error_subcode = error_subcode
        self.trace = trace

    def __str__(self):
        if self.error_code and self.error_subcode:
            return "%s (%d) %d-%d" % (self.reason, self.status,
                self.error_code, self.error_subcode)
        else:
            return "%s (%d)" % (self.reason, self.status)

# All Ning connections should go over SSLv3; Python 2.7 sometimes throws exceptions if you don't do this
class HTTPSConnectionV3(httplib2.HTTPSConnectionWithTimeout):
    def connect(self):
        if not hasattr(self, '_tunnel_host'):
            # old version of Python that doesn't need the hack
            return httplib2.HTTPSConnectionWithTimeout.connect(self)

        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        try:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_SSLv3)
        except ssl.SSLError as e:
            print("Trying SSLv3.")
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_SSLv23)

class Client(object):
    """Helper class that simplifies OAuth requests to the Ning API.

    Additionally it provides a helper method for generating OAuth tokens."""

    SECURE_PROTOCOL = "https://"
    """Protocol used for secure requests"""

    INSECURE_PROTOCOL = "http://"
    """Protocol used for insecure requests"""

    def __init__(self, host, network, consumer, token=None, screenName=None):

        self.host = host
        self.network = network
        self.consumer = consumer
        self.token = token
        self.screenName = screenName
        self.method = oauth.SignatureMethod_HMAC_SHA1()

    def call(self, url, method="GET", body='', token=None, headers=None,
        secure=False):
        """Makes an authenticated request to the Ning API using OAuth."""

        if self.method.name == 'PLAINTEXT':
            secure = True

        if secure:
            protocol = self.SECURE_PROTOCOL
            connection_type = HTTPSConnectionV3
        else:
            protocol = self.INSECURE_PROTOCOL
            connection_type = None # default

        url = '%s%s/xn/rest/%s/1.0/%s' % (protocol, self.host, self.network,
            url)
        self.client = oauth.Client(self.consumer, token)
        if self.method is not None:
            self.client.set_signature_method(self.method)

        resp, content = self.client.request(url, method, headers=headers,
            body=body, connection_type=connection_type)
        if int(resp['status']) != 200:
            try:
                result = json.loads(content)
                if result:
                    raise NingError(result['status'], result['reason'],
                        result['code'], result['subcode'], result['trace'])
                else:
                    raise NingError(int(resp['status']),
                        "HTTP response %s and %s" % (resp, content))
            except ValueError:
                raise NingError(int(resp['status']),
                    "HTTP response %s and %s" % (resp, content))

        return json.loads(content)

    def post(self, path, body):
        """Send a POST request to the Ning API."""
        if 'file' in body:
            mp = multipart.Multipart()
            mp.attach(multipart.FilePart({'name': 'file'}, body['file'],
                body['content_type']))
            for k, v in list(body.items()):
                if k != 'file' and k != 'content_type':
                    mp.attach(multipart.Part({'name': k}, v))
            return self.call("Photo", method="POST", token=self.token,
                headers={'Content-Type': mp.header()[1]}, body=str(mp))

        elif 'bin' in body:
            mp = multipart.Multipart()
            mp.attach(multipart.Part({'name': 'file', 'filename': 'file'},
                body['bin'], body['content_type']))

            for k, v in list(body.items()):
                if k != 'bin' and k != 'content_type':
                    mp.attach(multipart.Part({'name': k}, v))
            return self.call("Photo", method="POST", token=self.token,
                headers={'Content-Type': mp.header()[1]}, body=str(mp))

        else:
            return self.call(path, method="POST", token=self.token,
                body=urllib.parse.urlencode(body))

    def put(self, path, body):
        """Send a PUT request to the Ning API."""
        return self.call(path, method="PUT", token=self.token,
            body=urllib.parse.urlencode(body))

    def delete(self, path, attrs=None):
        """Send a DELETE request to the Ning API."""
        if attrs is not None:
            path += ('&' if path.find("?") != -1 else '?') + \
                urllib.parse.urlencode(attrs)
        return self.call(path, method="DELETE", token=self.token)

    def get(self, path, attrs=None):
        """Send a GET request to the Ning API."""
        if attrs is not None:
            path += ('&' if path.find("?") != -1 else '?') + \
                urllib.parse.urlencode(attrs)
        return self.call(path, token=self.token)

    def login(self, login, password):
        """Generate an OAuth token using the given email address and password.
        """
        info = self.call("Token", method="POST", headers={
            'Authorization': 'Basic %s' %
                binascii.b2a_base64('%s:%s' % (login, password)),
            }, secure=True)

        self.screenName = info['entry']['author']
        self.token = oauth.Token(key=info['entry']['oauthToken'],
            secret=info['entry']['oauthTokenSecret'])
        return self.token
