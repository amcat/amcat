###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

"""
Unit tests helper class for the REST API
"""
from urllib.parse import urlencode

from django.test import TestCase
from django.test.client import Client

from amcat.tools import amcattest

import json
import collections
import logging
log = logging.getLogger(__name__)

def surlencode(query, doseq=False):
    """
    This is an improved version of urlencode, which takes the same
    arguments as urlencode. Unlike urlencode, it accounts for values
    which are sequences.
    """
    def _surlencode():
        for k,v in query.items():
            if isinstance(v, (list, tuple)):
                for vsub in v:
                    yield urlencode({ k : vsub })
            else:
                yield urlencode({ k : v })
    
    return "&".join(_surlencode())

class ApiTestCase(TestCase):
    fixtures = ['_initial_data.json',]

    def __init__(self, *args, **kargs):
        super(ApiTestCase, self).__init__(*args, **kargs)
        self._passwords = {} # user_id -> password
        
    def setUp(self):
        self.client = Client()
        self.user = amcattest.create_test_user()
        self.user.is_superuser = True
        self.user.save()
        

    def _login(self, as_user=None, password=None):
        as_user = as_user or self.user
        if not password:
            password = self._passwords.get(as_user.id)
        if not password:
            password = 'test'
            as_user.set_password(password)
            as_user.save()
            self._passwords[as_user.id] = password
        self.assertTrue(self.client.login(username=as_user.username, password=password), "Cannot log in")
        
    def _request(self, resource, as_user=None, method='get', check_status=200, request_args=[], request_options={}, **options):
        if as_user is not None:
            self._login(as_user=as_user)
        resource_url = resource if isinstance(resource, str) else resource.get_url()
        if options:
            resource_url += "?" + surlencode(options)
        log.info("{method} {resource_url} {request_args} {request_options}".format(**locals()))
        method = getattr(self.client, method)
        request = method(resource_url, *request_args, **request_options)
        if check_status:
            self.assertEqual(request.status_code, check_status,
                             "Error: request returned status {request.status_code} (required: {check_status})\n{request.content}".format(**locals()))
        return request

    def get_options(self, resource):
        self._login()
        request = self.client.options(resource.get_url() + "?format=json")
        return json.loads(request.content.decode("utf-8"))

    def get(self, resource, **options):
        result = self._request(resource, format='json', **options)
        return json.loads(result.content.decode("utf-8"))

    def post(self, resource, body, check_status=201, **options):
        result = self._request(resource, method='post', format='json', request_args=[body], check_status=check_status, **options)
        return json.loads(result.content.decode("utf-8"))

    def get_object(self, resource, pk, **options):
        result = self.get(resource, pk=pk, **options)
        result = result['results'][0]
        keys, values = zip(*result.items())
        t = collections.namedtuple(resource.model.__name__, keys)
        return t(*values)
    
    def assertDictsEqual(self, a,b):
        if a != b:
            msg = []
            for x in a:
                if x not in b:
                    msg += [">> {x} not in b".format(**locals())]
                elif a[x] != b[x]:
                    msg += ["!! a[x]={ax} != b[x]={bx}".format(ax=a[x], bx=b[x])]
            for x in b:
                if x not in a:
                    msg += ["<< {x} not in a".format(**locals())]
            self.assertEqual(a,b, "\n".join(msg))
