###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

HOST = 'amcat.vu.nl'

from servertools import *
import socketio
import datamodel
from enginebase import QueryEngineBase, ConceptTable, postprocess
import filter
import tableserial
import logging; log = logging.getLogger(__name__)

class ProxyEngine(QueryEngineBase):
    def __init__(self, datamodel, log=False, profile=False, port=PORT, idlabelfactory=None):
        self.port = port
        QueryEngineBase.__init__(self, datamodel, log, profile)
        self.idlabelfactory = idlabelfactory

    def connect(self):
        s = socketio.connect(HOST, self.port)
        clienthandshake(s)
        return s
        
    def getList(self, concepts, filters, sortfields=None, limit=None, offset=None, distinct=False):
        sock = self.connect()
        data = queryList(sock, concepts, filters, distinct, self.idlabelfactory)
        if not data: data = []
        result = ConceptTable(concepts, data)
        log.info( "Received table with %i rows" % len(result.data))
        postprocess(result, sortfields, limit, offset)
        
        # serialisers = list(tableserial.getColumns(result.concepts, IDLabelFactory=self.idlabelfactory))
        # data = []
        # log.debug("deserializing")
        # for row in result.data:
            # data.append([s.deserialiseSQL(val) for (s, val) in zip(serialisers, row)])
        # result.data = data
        
        return result

    def getQuote(self, aid, words):
        words = " ".join(words)
        log.info('get quote in articleid %s for words %s' % (aid, words))
        sock = self.connect()
        sock.sendint(REQUEST_QUOTE)
        sock.sendint(aid)
        sock.sendstring(words)
        sock.flush()
        return sock.readstring()

def authenticateToServer(socket):
    challenge = socket.readstring()
    response = hash(challenge)
    #print "Received challenge %r, hashed with key %r, response is %r" % (challenge, KEY, response)
    socket.write(response)
    socket.flush()
def clienthandshake(socket):
    log.debug( "Sending version number")
    socket.sendint(1) # version no
    socket.flush()
    log.debug( "Reading server version")
    serverversion = socket.readint(checkerror=True)
    if serverversion is None: raise Exception("Server returned invalid serverversion")
    log.info( "Connected to AmCAT EngineServer version %i" % serverversion)
    authenticateToServer(socket)
    serverok = socket.readint(checkerror=True)
    if serverok<>1: raise Exception("Server returned invalid OK status %i" % serverok)
    log.info( "Server ok: %i" % serverok)

def queryList(socket, concepts, filters, distinct=False, idlabelfactory=None):
    socket.sendint(REQUEST_LIST_DISTINCT if distinct else REQUEST_LIST)
    log.info('distinct: %s' % REQUEST_LIST_DISTINCT if distinct else REQUEST_LIST)
    socket.sendint(len(concepts))
    socket.sendint(len(filters))
    for c in concepts:
        socket.sendstring(c.label)
    for f in filters:
        log.info("Sending filter %s" % f)
        if isinstance(f, filter.IntervalFilter):
            filterid, data = FILTER_INTERVAL, [[f.fromValue], [f.toValue]]
        else:
            filterid, data = FILTER_VALUES, [[x] for x in f.values]
        socket.sendint(filterid) 
        socket.sendstring(f.concept.label)
        tableserial.serialiseData([f.concept], data, socket)
    socket.flush()
    
    return tableserial.deserialiseData(socket, concepts, idlabelfactory)
    
                               
if __name__ == '__main__':
    import sys; port = int(sys.argv[1])
    dm = datamodel.DataModel()
    p = ProxyEngine(dm, port=port)
    from filter import *
    #p.getList([dm.article, dm.url], [])
    #p.getList([dm.article, dm.headline, dm.date, dm.sourcetype, dm.project, dm.source], [filter.ValuesFilter(dm.storedresult, 958), filter.IntervalFilter(dm.date, '2010-01-01','2010-12-10')])
    #t = p.getList([dm.source], [filter.ValuesFilter(dm.storedresult, 958), filter.IntervalFilter(dm.date, '2010-01-01','2010-12-10')], distinct=True, limit=3)
    #t = p.getList([dm.article], [ValuesFilter(dm.article, 46599856), ValuesFilter(dm.brand, 16545)])
    t = p.getList([dm.article], [ValuesFilter(dm.article, 7777777)])
    import tableoutput; print tableoutput.table2ascii(t)

