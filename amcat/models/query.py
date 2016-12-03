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



from django.contrib.auth.models import User
from django.db import models
from django.contrib.postgres.fields import JSONField
from amcat.models.articleset import ArticleSet
from amcat.models.coding.codingjob import CodingJob
from amcat.tools.model import AmcatModel

__all__ = ["Query"]


class Query(AmcatModel):
    __label__ = 'name'
    id = models.AutoField(primary_key=True, db_column="query_id")

    name = models.TextField()
    parameters = JSONField(default={})

    project = models.ForeignKey("amcat.Project")
    user = models.ForeignKey(User)

    last_saved = models.DateTimeField(auto_now=True, db_index=True)

    def get_articleset_ids(self):
        return map(int, self.parameters["articlesets"])

    def get_articlesets(self):
        return ArticleSet.objects.filter(id__in=self.get_articleset_ids())

    def get_codingjob_ids(self):
        return map(int, self.parameters.get("codingjobs", []))

    def get_codingjobs(self):
        return CodingJob.objects.filter(id__in=self.get_codingjob_ids())

    class Meta:
        app_label = 'amcat'
        db_table = 'queries'
        ordering = ("-last_saved",)
