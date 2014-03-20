from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions
from datetime import timedelta, datetime
# Inspired by
# http://stackoverflow.com/questions/14567586/token-authentication-for-restful-api-should-the-token-be-periodically-changed
class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super(ExpiringTokenAuthentication, self).authenticate_credentials(key)

        valid_until = token.created + timedelta(hours=24)
        print token.created, valid_until, datetime.now()
        if valid_until < datetime.now():
            raise exceptions.AuthenticationFailed('The token expired on {valid_until}. Please request a new token.'.format(**locals()))

        return token.user, token
