###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Lesser General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Lesser General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################
from __future__ import unicode_literals, print_function, absolute_import

"""
Utility module for accessing the AmCAT API.

This module is designed to be used as an independent module, so you can copy
this file into your project. For that reason, this module is also licensed
under the GNU Lesser GPL rather than the Affero GPL, so feel free to use it
in non-GPL programs. 
"""

import requests, json
import logging
log = logging.getLogger(__name__)

# URLs copied to ensure independence of module
articleset_url = 'projects/{project}/sets/'
article_url = articleset_url + '{articleset}/articles/'


class AmcatAPI(object):
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password

    def request(self, url, method="get", format="json", data=None, expected_status=None, headers=None, **options):
        """
        Make an HTTP request to the given relative URL with the host, user, and password information
        Returns the deserialized json if successful, and raises an exception otherwise
        """
        if expected_status is None:
            expected_status = dict(get=200, post=201)[method]
        url = "{self.host}/api/v4/{url}".format(**locals())
        options = dict({'format' : format}, **options)
        r = requests.request(method, url, auth=(self.user, self.password), data=data, params=options, headers=headers)
        log.info("HTTP {method} {url} (options={options!r}, data={data!r}) -> {r.status_code}".format(**locals()))
        if r.status_code != expected_status:
            raise Exception("Request {url!r} returned code {r.status_code}, expected {expected_status}:\n{r.text}".format(**locals()))
        if format == 'json':
            try:
                return r.json()
            except:
                raise Exception("Cannot decode json; text={r.text!r}".format(**locals()))
        else:
            return r.text
        
    def list_sets(self, project, **filters):
        """List the articlesets in a project"""
        url = articleset_url.format(**locals())
        return self.request(url, **filters)

    def list_articles(self, project, articleset, **filters):
        """List the articles in a set"""
        url = article_url.format(**locals())
        return self.request(url, **filters)
    
    def create_set(self, project, json_data=None, **options):
        """Create a new article set. Provide the needed arguments using the post_data or with key-value pairs"""
        url = articleset_url.format(**locals())
        if json_data is None:
            # form encoded request
            return self.request(url, method="post", data=options)
        else:
            if not isinstance(json_data, (str, unicode)):
                json_data = json.dumps(json_data)
            headers = {'content-type': 'application/json'}
            return self.request(url, method='post', data=json_data, headers=headers)

    def create_articles(self, project, articleset, json_data=None, **options):
        """Create one or more articles in the set. Provide the needed arguments using the json_data or with key-value pairs

        json_data can be a dictionary or list of dictionaries. Each dict can contain a 'children' attribute which
        is another list of dictionaries. 
        """
        url = article_url.format(**locals())
        if json_data is None: #TODO duplicated from create_set, move into requests (or separate post method?)
            # form encoded request
            return self.request(url, method="post", data=options)
        else:
            if not isinstance(json_data, (str, unicode)):
                json_data = json.dumps(json_data)
            headers = {'content-type': 'application/json'}
            return self.request(url, method='post', data=json_data, headers=headers)

        
if __name__ == '__main__':
    import argparse, sys, pydoc
    logging.basicConfig(level=logging.INFO)
    
    actions = {}
    for name in dir(AmcatAPI):
        if name.startswith("_"): continue
        fn = getattr(AmcatAPI, name)
        actions[name] = fn.__doc__
    epilog = "Possible actions (use api.py help <action> for help on the chosen action):\n%s" % ("\n".join("  {name}: {desc}".format(**locals()) for (name, desc) in actions.items()))

    parser = argparse.ArgumentParser(description=__doc__, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('host')
    parser.add_argument('username')
    parser.add_argument('password')
    parser.add_argument('action', help="The action to run. Valid options: help, list_sets. Use help <action> to get help op the chosen action")
    parser.add_argument('argument', help="Additional arguments for the action. User key=value to specify keyword arguments. Actions using post_data can be given using json encoded string or by pointing to a file using post_data=@filename.", nargs="*")
    opts = parser.parse_args()
    
    if opts.action == "help":
        if opts.argument:
            action = opts.argument[0]
            fn = getattr(AmcatAPI, action)
            print(pydoc.render_doc(fn, "Help on %s"))
        else:
            parser.print_help()
    else:
        api = AmcatAPI(opts.host, opts.username, opts.password)
        action = getattr(api, opts.action)
        args, kargs = [], {}
        for arg in opts.argument:
            if "=" in arg:
                k, v = arg.split("=", 1)
                if v.startswith("@"):
                    # get post data from (json-encoded) file
                    v = open(v[1:]).read()
                kargs[k] = v
            else:
                args.append(arg)

        try:
            result = action(*args, **kargs)
        except TypeError,e :
            print("TypeError on calling {action.__name__}: {e}\n".format(**locals()))
            print(pydoc.render_doc(action, "Help on %s"), file=sys.stderr)
            sys.exit(1)
                
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        print()
