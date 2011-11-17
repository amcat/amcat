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
Definition of various input and output types.
These types can be implemented as dict, string or any other basic type.
They are defined here, so scripts can reference to them as required input or output.
"""



class ArticleIterator(object):
    """Class representing a list of articles that can be iterated over"""
    pass
    
class JsonData(object): pass
class CsvData(object): pass
class ExcelData(object): pass
class HtmlData(object): pass
class SPSSData(object): pass
class DataTableJsonData(object): pass
class ArticleidList(object): pass
class ArticleidDictPerQuery(object): pass

class ImageMap(object):
    """ contains an image map, which is used by the clustermap script"""
    def __init__(self, mapHtml, image, articleCount, table):
        self.mapHtml = mapHtml
        self.image = image
        self.articleCount = articleCount
        self.table = table

class ArticleSetStatistics(object):
    """ class representing some basic information of a search query: the number of articles and the first/last date of the matching articles """
    def __init__(self, articleCount=None, firstDate=None, lastDate=None):
        self.articleCount = articleCount
        self.firstDate = firstDate
        self.lastDate = lastDate

        
class ErrorMsg(object):
    """ class representing an error message """
    def __init__(self, message, code=None, fields=None, **kargs):
        self.message = message
        self.code = code
        self.fields = fields
        self.kargs = kargs

