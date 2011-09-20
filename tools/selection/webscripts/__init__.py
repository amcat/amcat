from webscript import WebScript

from showSummary import ShowSummary
from showAggregation import ShowAggregation 
from saveAsSet import SaveAsSet
from showArticleTable import ShowArticleTable

mainScripts = [ShowSummary, ShowArticleTable, ShowAggregation]
actionScripts = [SaveAsSet]
allScripts = mainScripts + actionScripts

