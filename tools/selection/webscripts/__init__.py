from webscript import WebScript

from showSummary import ShowSummary
from showAggregation import ShowAggregation 
from saveAsSet import SaveAsSet
from exportArticles import ExportArticles
from showArticleTable import ShowArticleTable

mainScripts = [ShowSummary, ShowArticleTable, ShowAggregation]
actionScripts = [SaveAsSet, ExportArticles]
allScripts = mainScripts + actionScripts

