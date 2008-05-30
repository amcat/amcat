import libxml2, toolkit, os

class Handler:
    def warning(self, msg):
        toolkit.warn("warning: %s" % msg)

    def error(self, msg):
        toolkit.warn("error:   %s" % msg)

    def fatalError(self, msg):
        toolkit.warn("fatal:   %s" % msg)

def parseAll(callbackHandler, filenamesOrTexts):
    for f in filenamesOrTexts:
        if 'newDocument' in dir(callbackHandler):
            callbackHandler.newDocument(f)
            
        parse(callbackHandler,f)

def parseDir(callbackHandler, path):
    files = toolkit.filesInDir(path)
    parseAll(callbackHandler, files)


def parse(callbackHandler, fileOrText):
    if not '<' in fileOrText: #probably a filename
        file = fileOrText
        text = open(file).read()
    else:
        file = '[stdin].xml'
        text = fileOrText

    ctxt = libxml2.createPushParser(callbackHandler, text, len(text), file)
    ctxt.parseChunk("",0, 0)
    

