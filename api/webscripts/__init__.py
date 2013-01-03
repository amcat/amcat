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


#from webscript import WebScript

from show_summary import ShowSummary
from show_aggregation import ShowAggregation 
from show_articlelist import ShowArticleList
from show_articlesetstats import ShowArticleSetStatistics
from save_set import SaveAsSet
from export_articles import ExportArticles
from export_aggregation import ExportAggregation
from assign_codingjob import AssignCodingJob
from export_codingjobs import ExportCodingjobs
from clustermap import ShowClusterMap
from associations import ShowAssociations
from viewmodel import ViewModel

mainScripts = [ShowSummary, ShowArticleList, ShowAggregation]
actionScripts = [AssignCodingJob, ShowArticleSetStatistics, ExportArticles, ExportAggregation, ShowClusterMap, ShowAssociations, SaveAsSet, ViewModel, ExportCodingjobs]
allScripts = mainScripts + actionScripts

webscriptNames = [cls.__name__ for cls in allScripts]
