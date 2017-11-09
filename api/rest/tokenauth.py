from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions
from datetime import timedelta, datetime

# Inspired by
# http://stackoverflow.com/questions/14567586/token-authentication-for-restful-api-should-the-token-be-periodically-changed

EXPIRY_TIME = timedelta(hours=48)

class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super(ExpiringTokenAuthentication, self).authenticate_credentials(key)

        valid_until = token.created + EXPIRY_TIME
        if valid_until < datetime.now():
            err_msg = 'The token expired on {valid_until}. Please request a new token.'
            raise exceptions.AuthenticationFailed(err_msg.format(valid_until=valid_until))

        token.created = datetime.now()
        token.save()

        return token.user, token
