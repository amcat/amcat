
try:
    from urllib import parse # Python 3
except ImportError:
    import urlparse as parse # Python 2

from django.http import HttpResponseRedirect
from django.views.generic import TemplateView

from navigator.utils.error_handlers import handler400


def validate_url(url):
    """
    Checks if the URL is a http(s) URL with a non-empty domain.
    """
    components = parse.urlsplit(url)
    if not components.scheme.startswith("http"):
        raise ValueError("Scheme must be http(s)")
    if not components.netloc:
        raise ValueError("URL has no domain")


class RequestTokenView(TemplateView):
    """
    This view is for a client application requesting an access token to the API. It will use
    the user's session authentication to provide an authorization token to the client.
    After the user gives permission, the user will be redirected to the given client URL.

    GET params:
        'return': the return URL to redirect to. A %-formattable string, that contains
                  exactly one %s parameter, which be substituted with the token.
                  When formatted, it should be a valid URL to the client requesting the token.
                  NB.: in an URL, '%' characters should be escaped as '%25'.

    Example request:
        'https://amcat.nl/request_token?return=http://myclient.com/use_token/?token=%25s'

    """
    template_name = "request_token.html"

    def get(self, request, *args, **kwargs):
        response = super(RequestTokenView, self).get(request, *args, **kwargs)
        try:
            validate_url(request.GET['return'])
        except (KeyError, ValueError):
            return handler400(self.request)
        return response

    def post(self, request, *args, **kwargs):
        from api.rest.get_token import get_token

        try:
            token = get_token(self.request.user)
            return_url = str(self.request.GET['return'])
            url = return_url % token
            validate_url(url)
        except (TypeError, ValueError, KeyError):
            return handler400(self.request)  # The given URL is not given or invalid

        return HttpResponseRedirect(url)  # use HTTPResponseRedirect directly, don't try to resolve view URLs.

    def get_context_data(self, **kwargs):
        ctx = super(RequestTokenView, self).get_context_data(**kwargs)
        return_url = str(self.request.GET['return'])
        ctx['remote_domain'] = parse.urlsplit(return_url)[1]
        return ctx
