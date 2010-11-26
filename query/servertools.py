import hashlib

PORT = 26221
KEYFILE1 = "/home/amcat/resources/key" # for amcat
KEYFILE2 = "/usr/home/netframe/resources/key" # for parc
KEY = None

REQUEST_LIST = 1
REQUEST_LIST_DISTINCT = 2
REQUEST_QUOTE = 3

FILTER_VALUES = 1
FILTER_INTERVAL = 2

def hash(s):
    global KEY
    if KEY is None:
        try:
            KEY = open(KEYFILE1).read()
        except IOError:
            KEY = open(KEYFILE2).read()
    return hashlib.md5(KEY+s).digest()

