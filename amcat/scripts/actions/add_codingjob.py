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

import logging; log = logging.getLogger(__name__)

from django import forms
from amcat.scripts.script import Script
from amcat.models import CodingJob, User, ArticleSet
from amcat.scripts.actions.split_articles import SplitArticles

class AddCodingJob(Script):
    class options_form(forms.ModelForm):
        job_size = forms.IntegerField(help_text="If job size is given, multiple jobs of this size are created until all articles are assigned", required=False)
        
        class Meta:
            model = CodingJob
            
        def __init__(self, *args, **kargs):
            project = kargs.pop("project", None)
            forms.ModelForm.__init__(self, *args, **kargs)
            if project:
                schema_qs = project.get_codingschemas()
                self.fields["project"].initial = project
                self.fields["project"].widget = forms.HiddenInput()
                self.fields["coder"].queryset = User.objects.filter(projectrole__project=project)
                self.fields["articleset"].queryset = project.all_articlesets()
            else:
                schema_qs = self.fields["unitschema"].queryset
            
            self.fields['unitschema'].queryset = schema_qs.filter(isarticleschema=False)
            self.fields['articleschema'].queryset = schema_qs.filter(isarticleschema=True)

            
    def _run(self, job_size, articleset, name, project, **args):
        SplitArticles(dict(articlesets=[articleset.id])).run()
        job = self.bound_form.save(commit=False)
        
        if not job_size:
            job.articleset = ArticleSet.create_set(project=project, name=name, articles=articleset.articles.all())
            job.save()
            return job

        n = articleset.articles.count()
        result = []
        for i, start in enumerate(range(0, n, job_size)):
            job.pk = None
            job.articleset = ArticleSet.create_set(project=project, articles=articleset.articles.all()[start : start + job_size],
                                                   name="{name} - {j}".format(j=i+1, **locals()))
            job.name = "{name} - {j}".format(j=i+1, **locals())
            job.save()
            result.append(CodingJob.objects.get(pk=job.pk))
        return result
                          

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()

    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAddJob(amcattest.PolicyTestCase):
    def _get_args(self, n_articles):
        s = amcattest.create_test_set(articles=n_articles)
        u = amcattest.create_test_user()
        uschema = amcattest.create_test_schema()
        aschema = amcattest.create_test_schema(isarticleschema=True)
        return dict(project=s.project.id, articleset=s.id, coder=u.id, articleschema=aschema.id, unitschema=uschema.id, insertuser=u.id)
    
    def test_add(self):
        j = AddCodingJob.run_script(name="test", **self._get_args(10))
        self.assertEqual(j.articleset.articles.count(), 10)
        a = j.articleset.articles.all()[0]
        self.assertTrue(a.sentences.exists(), "No sentences have been created")

    def test_job_size(self):
        jobs = AddCodingJob.run_script(name="test", job_size=4, **self._get_args(10))
        self.assertEqual(len(jobs), 3)
        self.assertEqual(sorted(j.articleset.articles.count() for j in jobs), sorted([4, 4, 2]))
        self.assertEqual({j.name for j in jobs}, {"test - 1", "test - 2", "test - 3"})
        
