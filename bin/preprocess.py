#!/usr/bin/python
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

"""
Usage: python preprocess.py ACTION ANALYSISID [<ARTICLEIDS]

Possible ACTIONs:

split:  Split the given articles
        Ignores sentences already split
assign: Split the given articles and assign to the given analysis
        Ignores sentences already parsed or assigned.
"""

import sys, dbtoolkit, analysis, preprocessing, system, toolkit, amcatwarning

db = dbtoolkit.amcatDB()

def usage(msg=None):
    if msg: print msg, "\n"
    print __doc__
    print "\nAvailable analyses:"
    for a in system.System(db).analyses:
        if a.id > 0:
            print " %i) %s" % (a.id, a.label)
    sys.exit()
    
if len(sys.argv) < 2: usage()

action = sys.argv[1]

if action == "split":
    aids = list(toolkit.intlist())
    print "Splitting %i articles" % len(aids)
    n = preprocessing.splitArticles(db, aids)
    print "%i articles where split, committing" % n
    db.commit()
    print "Done!"
elif action == "assign":
    try:
        analysisid = int(sys.argv[2])
        a = analysis.Analysis(db, analysisid)
        if a.id == 0 or (not a.exists()):
            raise ValueError("Analysis %i does not exist" % analysisid)
    except Exception, e:
        usage(e)
    aids = list(toolkit.intlist())
    amcatwarning.Information("Assigning %i articles to analysis %s" % (len(aids), a))
else:
    usage("Uknown action: %s" % action)

