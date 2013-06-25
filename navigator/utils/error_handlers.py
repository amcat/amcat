from django.shortcuts import render
from django.http import HttpResponseServerError, HttpResponseNotFound
    
import urllib
import sys

def handler500(request):
    """
    500 error handler which includes a normal request context and some extra info.
    """
    uri = request.build_absolute_uri()
    try:
        sentry_id = request.sentry['id'].split("$")[0]
        comment = ("\n\n------ Issue details -----\n500 on accessing:\n{uri}\nSentry ID: {sentry_id}"
                   .format(**locals()))
    except AttributeError, KeyError:
        comment = ""
        pass
    title = header = "500 : An Error has occurred"
    exc_type, exc_value, exc_tb = sys.exc_info()
    subheader = "{exc_type.__name__}: {exc_value}".format(**locals())
    description = """The server encountered an internal error or misconfiguration and
                     was unable to complete your request."""
    
    issue_query = urllib.urlencode(dict(comment = comment))
    
    return HttpResponseServerError(render(request, 'error.html', locals()))

def handler404(request):
    """
    404 error handler which includes a normal request context.
    """
    uri = request.build_absolute_uri()
    comment = ("\n\n------ Issue details -----\n404 error on accessing:\n{uri}"
               .format(**locals()))
    issue_query = urllib.urlencode(dict(comment = comment))
    title = header = "404 : Page not Found"
    subheader = request.path
    description = """The requested location could not be found"""

    return HttpResponseNotFound(render(request, 'error.html', locals()))

def handler503(request):
    """
    503 error handler which includes a normal request context.
    """
    uri = request.build_absolute_uri()
    comment = ("\n\n------ Issue details -----\n503 error on accessing:\n{uri}"
               .format(**locals()))
    issue_query = urllib.urlencode(dict(comment = comment))
    title = header = "AmCAT is down for maintenance"
    subheader = "We are working on the problem and hopefully AmCAT will be available again soon!"
    description = """The server is temporarily down for maintenance. Please check back later or contact the administrator"""

    return HttpResponseNotFound(render(request, 'error.html', locals()))

def handler403(request):
    """
    403 Forbidden handler which includes a normal request context.
    """
    uri = request.build_absolute_uri()
    comment = ("\n\n------ Issue details -----\n403 error on accessing:\n{uri}"
               .format(**locals()))
    issue_query = urllib.urlencode(dict(comment = comment))
    title = header = "403 : Forbidden"
    exc_type, exc_value, exc_tb = sys.exc_info()
    if exc_value:
        subheader = "{request.path}: {exc_value}".format(**locals())
    else:
        subheader = request.path

    description = """You have insufficient rights to accesss the requested resource.
                     To gain rights, please contact an administrator of the project you
                     are trying to use (for project-related resources). For global
                     permissions, please contact the server administrator"""
    return HttpResponseNotFound(render(request, 'error.html', locals()))
