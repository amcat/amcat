from rest_framework import views
from rest_framework import exceptions
import logging

def exception_handler(exc, context):
    if isinstance(exc, exceptions.APIException):
        try:
            raise
        except:
            logging.exception("API Exception")
        
    return views.exception_handler(exc, context)
    
