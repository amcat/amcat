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

class Rest(object):
    def __init__(self, host="http://localhost:8000", username=None, password=None, root="api/v3"):
        self.host = host
        self.root = root
        if username is None:
            import amcat.settings
            db = amcat.settings.DATABASES['default']
            self.username = db['USER']
            self.password = db['PASSWORD']
        else:
            self.username = username
            self.password = password

    def get(self, resource, format='json', filters=None):
        params = dict(format=format)
        if filters: params.update(filters)
        uri = '{self.host}/{self.root}/{resource}/'.format(**locals())
        r = requests.get(uri, params=params, auth=(self.username, self.password))
        if format == 'json':
            return json.loads(r.text)
        else:
            return r.text

    def get_objects(self, *args, **kargs):
        result = self.get(*args, **kargs)
        return result['objects']

if __name__ == '__main__':
    r = Rest()
    print r.get_objects("sentence")