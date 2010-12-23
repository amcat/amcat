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

import dbpool, dbtoolkit, socket, cPickle, toolkit, tableoutput, time

class ProxyDB(dbtoolkit.amcatDB):
    def __init__(self, profile=False):
        self.init(profile)
    def doQuery(self, sql, *args, **kargs):
        sql = self.fireBeforeQuery(sql)
        t = time.time()
        result = doQuery(sql, *args, **kargs)
        self.fireAfterQuery(sql, time.time() - t, result)
        return result
    def commit(self):
        pass
    def rollback(self):
        abstract
        
def doQuery(sql, port=dbpool.SOCKETPORT, select='dummy'):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1',port))
    dbpool.sendi(s, sql)
    data = dbpool.readi(s)
    data = cPickle.loads(data)
    if isinstance(data, Exception):
        raise data
    return data or []

def usage():
    print "Usage: dbpool [-pPORT] COMMAND\nExecute SQL COMMAND on dbpool server on port PORT (default 14330)"
    sys.exit()

############## Driver ###################
if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        usage()
    port = dbpool.SOCKETPORT
    if sys.argv[1].startswith("-p"):
        port = int(sys.argv[1][2:])
        del sys.argv[1]
    data = doQuery(" ".join(sys.argv[1:]), port)
    if data:
        toolkit.warn("Received %i rows" % len(data))
        tableoutput.printTable(data)
    else:
        toolkit.warn("OK")
