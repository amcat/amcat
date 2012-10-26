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

from amcat.models import Project, Article, Codebook, CodingSchemaField
from amcat.scripts.script import Script

from amcat.tools import amcatrdf
from amcat.tools.toolkit import set_closure


log = logging.getLogger(__name__)


class SerializeProject(Script):
    """Serialize a project to zipped RDF"""

    output_type = str
    
    class options_form(forms.Form):
        project = forms.ModelChoiceField(queryset=Project.objects.all())
        outputfile = forms.CharField(required=False)

        
    def run(self, _input):
        project = self.options['project']
        outfile = self.options['outputfile']
        
        if not outfile:
            outfile = StringIO()

        serialize_project_to_zipfile(project, outfile)

        try:
            return outfile.getvalue()
        except AttributeError:
            return outfile

# Mappings to determine folder and filename for triples about models
_MODEL2DIRNAME = {"Code" : "Codebook",
                  "Coding" : "CodingJob",
                  "ArticleSet" : "Article",
                  "CodingSchemaField" : "CodingSchema"}
_MODEL2FILENAME = {"CodingSchemaField" : "CodingSchema"}

RE_DECONSTRUCT_URI = r"http://amcat.vu.nl/amcat3/(\w+)/\w+_(\d+)"

def _get_filename(subject, predicate, object):
    """Return the filename to which the triple with this subject should be serialized"""
    model, id = re.match(RE_DECONSTRUCT_URI, subject).groups()
    if model == "Project":
        return "project.rdf.xml"
    dir = _MODEL2DIRNAME.get(model, model)
    if model == "CodingSchemaField": # place schema fields with schema
        #HACK There must be a nicer way to do this...
        i = CodingSchemaField.objects.get(pk=id)
        model, id = "CodingSchema",  i.codingschema_id
    if model == "Code" : # place hierarchy with codebook, not with codes
        m = re.match(RE_DECONSTRUCT_URI, predicate)
        if m:
            model, id = m.groups()
        
    fn = '{model}_{id}'.format(**locals())
    return "{dir}s/{fn}.rdf.xml".format(**locals())          
      
def serialize_project_to_zipfile(project, outfile):
    triples_by_file = collections.defaultdict(list)
    for triple in amcatrdf.get_triples_project(project):
        fn = _get_filename(*triple)
        triples_by_file[fn].append(triple)

    zipfile = ZipFile(outfile, 'w')
    for fn, triples in triples_by_file.iteritems():
        bytes = amcatrdf.serialize(triples)
        zipfile.writestr(fn, bytes)
    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
