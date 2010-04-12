from engineserver import readobj, sendobj, sendauth, PORT
import socket

import pooleddb

class ProxyEngine(object):
    def getList(self, *args, **kargs):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1',PORT))
        sendauth(s)
        sendobj(s, (args, kargs))
        x = readobj(s)
        if isinstance(x, Exception):
            raise x
        return x
