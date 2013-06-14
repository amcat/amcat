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

from django.core.urlresolvers import reverse


from amcat.scripts.actions.import_codebook import ImportCodebook
from amcat.scripts.actions.export_codebook import ExportCodebook
from navigator.views.scriptview import ProjectScriptView, TableExportMixin

class ImportCodebook(ProjectScriptView):
    script = ImportCodebook
    def get_success_url(self):
        return reverse("project-codebooks", kwargs=dict(id=self.project.id))
    
class ExportCodebook(TableExportMixin, ProjectScriptView):
    script = ExportCodebook
    
    def get_initial(self):
        return dict(codebook=self.url_data["codebookid"])

    def get_success_url(self):
        return reverse("project-codebook", kwargs=dict(project=self.project.id, codebook=self.url_data["codebookid"]))
