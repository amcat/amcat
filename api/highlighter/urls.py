##########################################################################
from django.conf.urls import patterns, url, include

urlpatterns = patterns('',
    
    url(r'^articleschema$', 'api.highlighter.highlighter.articleschema'),
    url(r'^unitschema$', 'api.highlighter.highlighter.unitschema')
)