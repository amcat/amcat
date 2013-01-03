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


from webscript import WebScript


from amcat.scripts.searchscripts.statistics import ArticleSetStatisticsScript



    
class ShowArticleSetStatistics(WebScript):
    name = "Article Set Statistics"
    form_template = None
    form = None
    output_template = "api/webscripts/articlesetStats.html" 
    displayLocation = []
    
    
    def run(self):
        stats = ArticleSetStatisticsScript(self.formData).run()
        return self.outputResponse(stats, ArticleSetStatisticsScript.output_type)

        