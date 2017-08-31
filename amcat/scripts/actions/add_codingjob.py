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
Script add a project
"""

import logging;

from amcat.forms.fields import StaticModelChoiceField

log = logging.getLogger(__name__)

from django import forms
from amcat.scripts.script import Script
from amcat.models import CodingJob, User, ArticleSet, create_codingjob_batches


class AddCodingJob(Script):
    class options_form(forms.ModelForm):
        job_size = forms.IntegerField(help_text="If job size is given, multiple jobs of this size are created until all articles are assigned", required=False)
        
        class Meta:
            model = CodingJob
            exclude = ("archived", "insertdate")
            
        def __init__(self, *args, **kargs):
            project = kargs.pop("project", None)
            forms.ModelForm.__init__(self, *args, **kargs)

            if project:
                schema_qs = project.get_codingschemas()
                self.fields["project"] = StaticModelChoiceField(project)
                self.fields["coder"].queryset = User.objects.filter(projectrole__project=project)
                self.fields["articleset"].queryset = project.all_articlesets()
            else:
                schema_qs = self.fields["unitschema"].queryset
            
            self.fields['unitschema'].queryset = schema_qs.filter(isarticleschema=False)
            self.fields['articleschema'].queryset = schema_qs.filter(isarticleschema=True)

            
    def _run(self, job_size, articleset, name, project, **args):
        article_ids = articleset.articles.all().values_list("id", flat=True)
        job = self.bound_form.save(commit=False)
        
        if not job_size:
            job.articleset = ArticleSet.create_set(project=project, name=name, articles=article_ids, favourite=False)
            job.save()
            return job

        return create_codingjob_batches(job, article_ids, job_size)


if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()

