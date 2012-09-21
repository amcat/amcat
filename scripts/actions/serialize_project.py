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

from zipfile import ZipFile
import logging
from cStringIO import StringIO

from django import forms

from amcat.models import Project, Article
from amcat.scripts.script import Script

from amcat.tools import amcatrdf

log = logging.getLogger(__name__)

class AddUserForm(forms.Form):
    project = forms.ModelChoiceField(queryset=Project.objects.all(), required=False)

class SerializeProject(Script):
    """Serialize a project to zipped RDF"""

    output_type = str
    
    class options_form(forms.Form):
        project = forms.ModelChoiceField(queryset=Project.objects.all())
        outputfile = forms.CharField(required=False)

    def run(self, _input):
        self.project = self.options['project']

        outfile = self.options['outputfile']
        if not outfile:
            outfile = StringIO()
        self.zipfile = ZipFile(outfile, 'w')

        from amcat.tools import amcatlogging
        amcatlogging.debug_module("django.db.backends")
        
        #self.serialize_project_meta()
        #self.serialize_articles()
        #self.serialize_coding_schemas()
        self.serialize_codebooks()
        
        try:
            return outfile.getvalue()
        except AttributeError:
            return outfile

    def serialize_project_meta(self):
        self.serialize_objects(self.project, "project.rdf.xml")

        
    def serialize_coding_schemas(self):
        for schema in self.project.get_codingschemas().prefetch_related("project", "fields"):
            self.serialize_objects([schema] + list(schema.fields.all()),
                                   filename="CodingSchemas/%i.rdf.xml" % schema.id)
            
    def serialize_codebooks(self):
        for codebook in self.project.get_codebooks():
            codes = codebook.get_codes()
            for c in codes:
                print c.id
            #self.serialize_objects([codebook], filename="CodeBooks/%i.rdf.xml" % codebook.id)
            break
            
            
    def serialize_articles(self):
        direct =  Article.objects.filter(project=self.project)
        indirect = Article.objects.filter(articlesets__project=self.project)
        direct, indirect = [set(manager.prefetch_related("project", "medium"))
                            for manager in (direct, indirect)]
        for article in direct | indirect:
            self.serialize_objects(article, filename="Documents/%i.rdf.xml" % article.id)
        
    def serialize_objects(self, objects, filename):
        triples = set()
        for object in objects:
            triples |= set(amcatrdf.get_triples(object))
        bytes = amcatrdf.serialize(triples)
        print bytes
        self.zipfile.writestr(filename, bytes)
    
    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
