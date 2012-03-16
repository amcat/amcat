#! /usr/bin/python
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
Plugin for uploading mediargus text files
"""



from __future__ import unicode_literals, absolute_import

import csv
from cStringIO import StringIO

from django import forms

from amcat.scripts.article_upload.upload import UploadScript

from amcat.models.article import Article
from amcat.models.medium import Medium, get_or_create_medium
from amcat.tools.toolkit import readDate


class Mediargus(UploadScript):

    def split_text(self, text):
        text = text.replace('\r\n','\n')
        text = text.replace('\r','\n')

        partitions = text.partition('\n\n\n\n\n\n')
        metas = partitions[0].split('\n\n\n')
        bodies = partitions[2].split('\n\n\n\n\n')
        return zip(metas, bodies)

    def parse_document(self, tupleText):
        meta, body = tupleText
        meta = meta.strip()
        meta = meta.split('\n')
        kargs = {}
        kargs['externalid'] = int(meta[0].split('.')[0].lstrip('?'))
        kargs['headline'] = meta[0].partition('. ')[2]
        
        medium_name, date, pagenr, length = meta[2].split(', ')
        kargs['medium'] = get_or_create_medium(medium_name)
        kargs['date'] = readDate(date)
        kargs['pagenr'] = int(pagenr.strip('p.'))
        kargs['length']  = int(length.strip('w.'))
        
        body = body.split('\n')
        kargs['section'] = body[2]
        
        kargs['text'] = '\n'.join(body[5:])
        
        kargs['project'] = self.options['project']
        
        return Article(**kargs)

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    a = cli.run_cli(Mediargus, handle_output=False)


