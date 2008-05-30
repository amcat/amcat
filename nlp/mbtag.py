import socket,toolkit, tokenize, sbd

TEXT_TYPE=6

class Tagger(object):

    def __init__(self, host='localhost', port=1999):
        self.conn = socket.socket()
        self.conn.connect(('localhost', 1999))
        self.conn.recv(1024)

    def tag(self, text):
        self.conn.send(text + "\n")
        return self.conn.recv(1024)
                    
    def tagtext(self, text, token=0):
        ret = []
        for par in sbd.splitPars(text):
            for sent in par:
                sent = toolkit.clean(sent, level=1)
                sent = tokenize.tokenize(sent)
                tagged = self.tag(sent)
                ret.append(tagged.strip())
            ret.append("\n\n")
        return " ".join(ret)
        

if __name__ == '__main__':
    tagger = MBTagger()
    import sys
    input = sys.stdin.read()

    print tagger.tagtext(input)
    
            
