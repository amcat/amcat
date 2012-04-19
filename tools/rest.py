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
    def __init__(self, host="localhost:8000", schema='http', username=None, password=None, root="api/v3"):
        self.host = host
        self.root = root
        self.schema = schema
        if username is None:
            import amcat.settings
            db = amcat.settings.DATABASES['default']
            self.username = db['USER']
            self.password = db['PASSWORD']
        else:
            self.username = username
            self.password = password

    def get(self, resource, format='json', **filters):
        params = dict(format=format)
        if filters: params.update(filters)
        uri = '{self.schema}://{self.host}/{self.root}/{resource}/'.format(**locals())
        log.debug("Querying REST {uri} with params {params}".format(**locals()))
        r = requests.get(uri, params=params, auth=(self.username, self.password))
        if r.status_code != 200:
            raise Exception("Remote server returned status {r.status_code}\n{r.text}".format(**locals()))
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
        if len(result) > 1: raise Exception("Query {resource} id={id} returned {n} objects".format(n=len(result), **locals()))
        return result[0]

if __name__ == '__main__':
    r = Rest()
    print r.get_objects("sentence")