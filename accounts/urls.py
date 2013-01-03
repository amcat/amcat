from django.conf.urls.defaults import patterns, url
from accounts.views import login, logout, register, recover
from accounts.views import recover_confirm, recover_requested

urlpatterns = patterns('',
    url('^login/$', login, name="accounts-login"),
    url('^logout/$', logout, name="accounts-logout"),
    url('^register/$', register, name="accounts-register"),
    url('^recover/$', recover, name="accounts-recover"),
    url('^recover_requested/$', recover_requested, name="accounts-recover-requested"),
    url(r'^reset/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', recover_confirm, name="accounts-recover-confirm")
)
