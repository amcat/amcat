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
import os
import time

from unittest import skipIf
from django.core.urlresolvers import reverse

from amcat.models import ProjectArticleSet
from amcat.tools import amcattest
from amcat.tools.amcattest import AmCATLiveServerTestCase


class TestQueryView(AmCATLiveServerTestCase):
    def set_up(self):
        super(TestQueryView, self).setUp()

        self.project = amcattest.create_test_project()
        self.user = self.project.insert_user
        self.aset1 = amcattest.create_test_set(2, project=self.project)
        self.aset2 = amcattest.create_test_set(3, project=self.project)
        ProjectArticleSet.objects.update_or_create(project=self.project, articleset=self.aset1,
                                                   defaults={'is_favourite': True})
        ProjectArticleSet.objects.update_or_create(project=self.project, articleset=self.aset2,
                                                   defaults={'is_favourite': True})

    @amcattest.use_elastic
    @skipIf(os.environ.get("TRAVIS") == "true", "Not yet supported on Travis :(")
    def test_summary(self):
        self.set_up()

        
        self.login(username=self.user.username, password="test")
        self.browser.visit(self.get_url(reverse("navigator:query", args=[self.project.id])))

        try:
            self.browser.find_by_css("#active-articlesets tbody tr")[1].click()
        except:
            time.sleep(10)
            self.browser.find_by_css("#active-articlesets tbody tr")[1].click()

        self.browser.find_by_css("#id_aggregations")
        self.browser.find_by_css("#run-query")[0].click()
        self.browser.find_by_css("#results.summary")
