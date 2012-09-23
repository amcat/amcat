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
Abstract the AmCAT API so that actions and objects can be called/retrieved via the
rest/actions api or locally.
"""

import requests
import logging
from collections import namedtuple
import itertools
import json

from amcat.tools.toolkit import csvreader
from amcat.tools import classtools

log = logging.getLogger(__name__)

class API(object):

    def __init__(self, base_uri, username=None, password=None, client=requests):
        """
        @param requests: module to use for http requests, useful for unit testing
        """
        self.base_uri = base_uri
        if username is None:
            import amcat.settings
            db = amcat.settings.DATABASES['default']
            self.username = db['USER']
            self.password = db['PASSWORD']
        else:
            self.username = username
            self.password = password
        self.client = client

    def get_object(self, klass, pk):
        objects = list(self.get_objects(klass, pk=pk))
        if len(objects) != 1:
            raise Exception("get_object(%r, %r) returned %i results"
                    % (klass, pk, len(objects)))
        return objects[0]

    def get_objects(self, klass, batch_size = 1000, **filters):
        if isinstance(klass, type):
            klass = klass.__name__.lower()

        return_type = None

        for page in itertools.count(1):
            uri = ("{self.base_uri}/api/v4/{klass}?format=json&limit={batch_size}&page={page}"
                   .format(**locals()))

            
            r = self.client.get(uri, params=filters, auth=(self.username, self.password))

            _check_status(r)
            
            o = json.loads(_get_content(r))
            if o['total'] == 0: return

            if return_type is None:
                return_type = namedtuple(klass, o['results'][0].keys())
            for row in o['results']:
                yield return_type(**row)

            if page == o['pages']: break

    def call_action(self, action, **kargs):
        if isinstance(action, type): action = action.__name__

        uri = '{self.base_uri}/api/action/{action}'.format(**locals())
        log.debug("Posting action {uri} with data {kargs}".format(**locals()))

        r = self.client.post(uri, data=kargs, auth=(self.username, self.password))
        _check_status(r)
        return json.loads(_get_content(r))

def _get_content(response):
    result = response.text
    if not result:
        result = response.content
        if result:
            result = result.decode(response.encoding or "utf-8")
    return result

def _check_status(response):
    """Check whether the response is 2xx (http success), Exception otherwise"""
    if response.status_code // 100 != 2:
        log.error("Remote Server returned status {response.status_code}".format(**locals()))
        try:
            content = json.loads(response.content)
            log.error("Server error:{}: {}\n-------\nRemote traceback:\n{}\n-------".
                      format(content["error-class"], content["error-message"].strip(),
                             content["error-traceback"].strip()))
        except:
            log.exception("Error on decoding content:\n{response.content!r}".format(**locals()))
        raise Exception("Remote server returned status {response.status_code}"
                        .format(**locals()))


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

# see amcatnavigator.api.tests.test_api_module

