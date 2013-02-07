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
from django.db import transaction

from amcat.scripts.script import Script
from amcat.models import CodingJob



PROJECT_ROLE_READER=11

class DeleteCodingJob(Script):
    """Delete the given job including all codings and article set unless the
    article set is in use somewhere else"""
    class options_form(forms.Form):
        job = forms.ModelChoiceField(queryset=CodingJob.objects.all())

    @transaction.commit_on_success
    def run(self, _input=None):
        j = self.options['job']

        # remember article set so we can delete it later
        aset = j.articleset
        j.delete()
        if not CodingJob.objects.filter(articleset=aset).exists():
            aset.delete()

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestDeleteCodingJob(amcattest.PolicyTestCase):
    def test_delete(self):
        """Simple deletion of a job"""
        from amcat.models import ArticleSet, Coding
        s = amcattest.create_test_set(articles=5)
        j = amcattest.create_test_job(articleset=s)
        c = amcattest.create_test_coding(codingjob=j)
        self.assertTrue(CodingJob.objects.filter(pk=j.id).exists())
        self.assertTrue(ArticleSet.objects.filter(pk=s.id).exists())
        self.assertTrue(Coding.objects.filter(pk=c.id).exists())
        DeleteCodingJob(job=j.id).run()
        self.assertFalse(CodingJob.objects.filter(pk=j.id).exists())
        self.assertFalse(ArticleSet.objects.filter(pk=s.id).exists())
        self.assertFalse(Coding.objects.filter(pk=c.id).exists())

    def test_delete_setinuse(self):
        """Delete a job whose set is in use somewhere else"""
        from amcat.models import ArticleSet
        s = amcattest.create_test_set(articles=5)
        j = amcattest.create_test_job(articleset=s) 
        j2 = amcattest.create_test_job(articleset=s)# use same article set
        DeleteCodingJob(job=j.id).run()
        self.assertFalse(CodingJob.objects.filter(pk=j.id).exists())
        self.assertEquals(j2.articleset, s)
        self.assertTrue(ArticleSet.objects.filter(pk=s.id).exists())
