##########################################################################
from django.conf.urls import patterns, url, include

urlpatterns = patterns('',
    
    url(r'^highlight$', 'api.highlighter.highlighter.highlight')
)

def foo(req, res):
	pass