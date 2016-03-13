import logging
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from django.http import Http404

def exception_handler(exc, context):
    try:
        raise
    except:
        # Log all API errors for inspection
        logging.exception("API Exception")

    try:
    # from rest_framework.views.exception_handler
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait

        if isinstance(exc, Http404):
            detail = exc.message
            exc.status_code = 404
        elif isinstance(exc, APIException):
            detail = exc.detail
        else:
            detail = str(exc)
            exc.status_code = 500
            
        data = {'exception_type': type(exc).__name__, 'detail': detail}
        return Response(data, status=exc.status_code, headers=headers)
    except:
        logging.exception("Error on rendering exception")
