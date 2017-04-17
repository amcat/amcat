from django.shortcuts import render
from django.http import HttpResponse

import urllib
import sys
import json

def _build_response(request, context):
    if 'uri' not in context: context['uri'] = request.build_absolute_uri()
    if 'subheader' not in context: context['subheader'] = request.path
    if 'comment' not in context:
        context['comment'] = ("\n\n------ Issue details -----\n{status} error on accessing:\n{uri}"
                              .format(**context))
    if 'issue_title' not in context:
        context['issue_title'] = context['header']

    #TODO: should check http accept
    if request.path.startswith("/api"):
        content = json.dumps({"error": True,
                             "status" : context['status'],
                             "message" : context['header'],
                             "details" : context['subheader'],
                              "description" : context['description']}, indent=2)
        content_type = "application/json"
    else:
        content = render(request, "error.html", context)
        content_type = "text/html"

    return HttpResponse(content, status=context['status'], content_type=content_type)

def handler500(request):
    """
    500 error handler which includes a normal request context and some extra info.
    """
    status = 500
    title = header = "500 : An Error has occurred"
    exc_type, exc_value, exc_tb = sys.exc_info()
    subheader = issue_title = "{exc_type.__name__}: {exc_value}".format(**locals())
    description = """The server encountered an internal error or misconfiguration and
                     was unable to complete your request."""

    return _build_response(request, locals())

def handler400(request):
    """
    400 error handler which includes a normal request context.
    """
    status = 400
    title = header = "400 : Bad Request"
    description = """The request was malformed."""
    issue_title = """Bad request: {}""".format(request.path)
    return _build_response(request, locals())

def handler404(request):
    """
    404 error handler which includes a normal request context.
    """
    status = 404
    title = header = "404 : Page not Found"
    description = """The requested location could not be found"""
    issue_title = """Page not found: {}""".format(request.path)
    return _build_response(request, locals())


def handler503(request):
    """
    503 error handler which includes a normal request context.
    """
    status = 503
    title = header = "AmCAT is down for maintenance"
    subheader = "We are working on the problem and hopefully AmCAT will be available again soon!"
    description = """The server is temporarily down for maintenance. Please check back later or contact the administrator"""

    return _build_response(request, locals())

def handler403(request):
    """
    403 Forbidden handler which includes a normal request context.
    """
    status = 403
    title = header = "403 : Forbidden"
    exc_type, exc_value, exc_tb = sys.exc_info()
    if exc_value:
        subheader = "{request.path}: {exc_value}".format(**locals())
    issue_title = "Forbidden: {request.path}".format(**locals())
    description = """You have insufficient rights to accesss the requested resource.
                     To gain rights, please contact an administrator of the project you
                     are trying to use (for project-related resources). For global
                     permissions, please contact the server administrator"""

    return _build_response(request, locals())
