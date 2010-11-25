import hashlib

PORT = 26221
KEYFILE = "/home/amcat/resources/key" # for amcat
KEYFILE = "/usr/home/netframe/resources/key" # for parc
KEY = None

REQUEST_LIST = 1
REQUEST_LIST_DISTINCT = 2
REQUEST_QUOTE = 3

FILTER_VALUES = 1
FILTER_INTERVAL = 2

def hash(s):
    global KEY
    if KEY is None: KEY = open(KEYFILE).read()
    return hashlib.md5(KEY+s).digest()

