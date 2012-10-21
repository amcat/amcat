#!/usr/bin/python

##########################################################################
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
Serialize a project to zipped RDF (e.g. for storage at DANS)
"""

import collections, re

from zipfile import ZipFile
import logging
from cStringIO import StringIO

from django import forms

from amcat.models import Project, Article, Codebook
from amcat.scripts.script import Script

from amcat.tools import amcatrdf
from amcat.tools.toolkit import set_closure


log = logging.getLogger(__name__)

_MODEL2DIRNAME = {"Code" : "Codebook",
                  "Coding" : "CodingJob",
                  "ArticleSet" : "Article",
                  "CodingSchemaField" : "CodingSchema"}
_MODEL2FILENAME = {"CodingSchemaField" : "CodingSchema"}

class SerializeProject(Script):
    """Serialize a project to zipped RDF"""

    output_type = str
    
    class options_form(forms.Form):
        project = forms.ModelChoiceField(queryset=Project.objects.all())
        outputfile = forms.CharField(required=False)

    def get_filename(self, model, id):
        dir = _MODEL2DIRNAME.get(model, model)
        fn = _MODEL2FILENAME.get(model, model)
        return "{dir}s/{fn}_{id}.rdf.xml".format(**locals())
        
    def run(self, _input):
        project = self.options['project']
        outfile = self.options['outputfile']
        
        if not outfile:
            outfile = StringIO()
        self.zipfile = ZipFile(outfile, 'w')

        triples_by_file = collections.defaultdict(list)
        
        for triple in amcatrdf.get_triples_project(project):
            m = re.match(r"http://amcat.vu.nl/amcat3/(\w+)/\w+_(\d+)", triple[0])
            model, id = m.group(1), int(m.group(2))
            if model == "Project":
                fn = "project.rdf.xml"
            else:
                fn = self.get_filename(model, id)
            triples_by_file[fn].append(triple)
            
        for fn, triples in triples_by_file.iteritems():
            self.serialize_triples(triples, fn)
            
        try:
            return outfile.getvalue()
        except AttributeError:
            return outfile
      
    def serialize_triples(self, triples, filename):
        bytes = amcatrdf.serialize(triples)
        self.zipfile.writestr(filename, bytes)



    
    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
