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
Plugin for uploading csv files
"""



from __future__ import unicode_literals, absolute_import

import csv
from cStringIO import StringIO

from django import forms

from amcat.scripts.article_upload.upload import UploadScript

from amcat.models.article import Article
from amcat.models.medium import Medium

from amcat.tools.toolkit import readDate


class Mediargus(UploadScript):

    def split_text(self, text):
        partitions = text.partition("\n\n\n\n\n\n\n")
        data = partitions[0].split("\n\n\n")
        bodies = partitions[2].split("\n\n\n\n\n\n\n")
        
        return zip(data, bodies)

    def parse_document(self, tupleText):
        lines = tupleText[0].split('\n')
        kargs = {}
        kargs[externalid] = int(lines[0].partition(' ')[0].strip('?')) #? ?
        kargs[headline] = lines[0].parition(' ')[2]
        
        data = lines[2].split(', ')
        kargs[medium] = data[0]        
        kargs[date] = readDate(data[1])
        kargs[pagenr] = int(data[2].strip('p.'))
        kargs[length] = int(data[3].strip('w.'))
        
        lines = tupleText[1].split('\n')
        kargs[text] = lines[index(kargs[headline])+2:]
         
        return Article(**kargs)




