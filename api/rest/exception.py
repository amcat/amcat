import logging
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework import views
from django.http import Http404
from django.core.exceptions import PermissionDenied


def exception_handler(exc, context):
    try:
        raise
    except:
        # Log all API errors for inspection
        logging.exception("API Exception")

    try:
    # from rest_framework.views.exception_handler
        headers = {}
        data = {'exception_type': type(exc).__name__}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait
            
        if isinstance(exc, Http404):
            data['detail'] = str(exc)
            status_code = 404
            
        elif isinstance(exc, PermissionDenied):
            status_code = 403
            data['detail'] = str(exc)
        elif isinstance(exc, APIException):
            status_code = exc.status_code
            if isinstance(exc.detail, dict):
                data.update(exc.detail)
            else:
                data['detail'] = exc.detail
        else:
            data['detail'] = str(exc)
            status_code = 500
            

        return Response(data, status=status_code, headers=headers)
    except:
        logging.exception("Error on rendering exception")
        
    return views.exception_handler(exc, context)
