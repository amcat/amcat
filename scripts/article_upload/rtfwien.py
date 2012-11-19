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
Plugin for uploading RTF files from Wien (need better name)
"""

from __future__ import unicode_literals

from amcat.scripts.article_upload.upload import UploadScript

from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.tools.djangotoolkit import get_or_create

from cStringIO import StringIO
import subprocess
from tempfile import TemporaryFile

class Text(UploadScript):

    
    
    def split_text(self, text):
        return text.split("\n\page ")
        
    def parse_document(self, text):
        with TemporaryFile() as f:
            f.write(text)
            print f
            xml = subprocess.check_output(["rtf2xml", f.name])
        
        
        print xml
        raise Exception()
        
if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli
    run_cli(handle_output=False)
