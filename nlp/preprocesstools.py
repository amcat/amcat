import toolkit


AMCAT_RESOURCES = "/home/amcat/resources"
AMCAT_HOSTNAME = 'amcat'
ALT_RESOURCES = "/home/wva/resources"
def getResourcesDir():
    import socket
    if socket.gethostname() == AMCAT_HOSTNAME:
        return AMCAT_RESOURCES
    else:
        return ALT_RESOURCES
    
def clean(s):
    return toolkit.clean(s, level=1).encode('ascii', 'replace')

def getInputFromSentences(sentences):
    """list of (id, str) tuples to \n-joined cleaned strs"""
    input = "\n".join(clean(s) for (id, s) in sentences if s.strip())
    sids = [id for (id, s) in sentences if s.strip()]
    return sids, input
