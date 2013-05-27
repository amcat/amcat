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

from django.test import TestCase
from django.test.client import Client

from amcat.tools import amcattest

from django.contrib.auth.hashers import make_password
from urllib import urlencode

import json
import collections

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
    def __init__(self, *args, **kargs):
        super(ApiTestCase, self).__init__(*args, **kargs)

    def setUp(self):
        self.client = Client()

        hashed_password = make_password("geheim hoor")
        self.user = amcattest.create_test_user(password=hashed_password)
        self.user.get_profile().hashed_password = hashed_password    
        self.user.is_superuser = True
        self.user.save()
        

    def _login(self, as_user=None):
        as_user = as_user or self.user
        pwd = as_user.get_profile().hashed_password
        self.assertTrue(self.client.login(username=as_user.username, password=pwd), "Cannot log in")
        
    def _get(self, resource, as_user=None, format='json', **options):
        self._login(as_user=as_user)
        request_options = options.pop("request_options", {})
        options = "&{}".format(surlencode(options), True) if options else ""
        resource_url = resource.get_url()
        resource_url += "?format={}{}".format(format, options)
        request = self.client.get(resource_url, **request_options)
        return request.content

    def get_options(self, resource):
        self._login()
        request = self.client.options(resource.get_url() + "?format=json")
        return json.loads(request.content)

    def get(self, resource, **options):
        result = self._get(resource, format='json', **options)
        return json.loads(result)
    
    def get_object(self, resource, pk, **options):
        result = self.get(resource, pk=pk, **options)
        result = result['results'][0]
        keys, values = zip(*result.iteritems())
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
    
