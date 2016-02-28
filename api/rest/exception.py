from rest_framework import views
from rest_framework import exceptions
import logging

def exception_handler(exc, context):
    try:
        raise
    except:
        logging.exception("API Exception")
        
    return views.exception_handler(exc, context)
    
