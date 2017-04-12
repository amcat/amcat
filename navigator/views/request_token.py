from django.http import HttpResponseBadRequest
from django.shortcuts import render
import urlparse as parse
from navigator.utils.error_handlers import handler400, handler404



def request_token(request):
    # provisionary token authorization using django-rest-framework's builtin tokens.
    # This really isn't the most secure thing ever.
    # TODO: switch over to OAUTH2

    try:
        from api.rest.get_token import get_token
        token = get_token(request.user)
        return_url = str(request.GET['return'])
        remote_domain = parse.urlsplit(return_url)[1]
        url = return_url % token
    except ImportError:
        return handler404(request)
    #except:
    #    return handler400(request)

    return render(request, 'request_token.html', locals())
