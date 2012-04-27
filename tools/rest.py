#! /usr/bin/python
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
Useful methods to interact with the REST api
"""

import requests, json
import logging; log = logging.getLogger(__name__)

class Rest(object):
    def __init__(self, host="localhost:8000", schema='http', username=None,
                 password=None, root="api/v3", action_root="api/action", verify=False):
        if "://" in host:
            schema, host = host.split("://")
        self.host = host
        self.root = root
        self.action_root = action_root
        self.schema = schema
        self.verify = verify
        if username is None:
            import amcat.settings
            db = amcat.settings.DATABASES['default']
            self.username = db['USER']
            self.password = db['PASSWORD']
        else:
            self.username = username
            self.password = password
    @property
    def _request_args(self):
        return dict(auth=(self.username, self.password), verify=self.verify)
    def get(self, resource, format='json', **filters):
        params = dict(format=format)
        if filters: params.update(filters)
        uri = '{self.schema}://{self.host}/{self.root}/{resource}/'.format(**locals())
        log.debug("Querying REST {uri} with params {params}".format(**locals()))
        r = requests.get(uri, params=params, **self._request_args)
        _check_status(r)

        if format == 'json':
            return json.loads(r.text)
        else:
            return r.text

    def get_objects(self, *args, **kargs):
        result = self.get(*args, **kargs)
        return result['objects']

    def get_object(self, resource, id, **kargs):
        result = self.get_objects(resource, id=id, **kargs)
        if not result: raise Exception("Object {resource} id={id} not found!".format(**locals()))
        if len(result) > 1:
            raise Exception("Query {resource} id={id} returned {n} objects"
                            .format(n=len(result), **locals()))
        return result[0]

    def call_action(self, action, decode_json=True, **kargs):
        if isinstance(action, type): action = action.__name__
        uri = '{self.schema}://{self.host}/{self.action_root}/{action}'.format(**locals())
        log.debug("Posting action {uri} with data {kargs}".format(**locals()))
        
        r = requests.post(uri, data=kargs, **self._request_args)
        _check_status(r)
        if decode_json:
            try:
                return json.loads(r.content)
            except:
                log.error("Error on loading {r.content!r}".format(**locals()))
        return r.content
    
def _check_status(response):
    """Check whether the response is 2xx (http success), Exception otherwise"""
    if response.status_code // 100 != 2:
        log.error("Remote Server returned status {response.status_code}".format(**locals()))
        try:
            content = json.loads(rcontent)
            log.error("Server error:{}: {}\n-------\nRemote traceback:\n{}\n-------".
                      format(content["error-class"], content["error-message"].strip(),
                             content["error-traceback"].strip()))
        except:
            log.exception("Error on decoding content:\n{response.content}".format(**locals()))
        raise Exception("Remote server returned status {response.status_code}"
                        .format(**locals()))

if __name__ == '__main__':
    r = Rest()
    print r.get_objects("sentence")
