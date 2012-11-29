#!/usr/bin/env python
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
Toolkit with useful methods for mercurial

Uses subprocess to run hg as external process

See http://mercurial.selenic.com/wiki/MercurialApi: For the vast
majority of third party code, the best approach is to use Mercurial's
published, documented, and stable API: the command line interface
"""

import subprocess
import os.path

def get_repo(fn):
    """
    Get the repository to which file/folder fn belongs
    by recursing up the folder tree until the root is found
    """
    if os.path.exists(os.path.join(fn, ".hg")): return fn
    parent = os.path.dirname(fn) #dirname("/") == "/"
    if parent != fn: return get_repo(parent) 

def get_version_name(fn=None):
    r = Repository(fn)
    b = r.active_branch()
    if b in ('default', 'trunk'):
        return 'development'
    else:
        return b

class Repository(object):

    def __init__(self, repo=None):
        """
        Get the given repository, or the amcat repository if repo is None
        """
        if repo is None:
            import amcat
            repo = amcat.__file__
        self.repo = get_repo(repo)
        
    def list_branches(self):
        cmd = ['hg', 'branches','-R',self.repo]
        for line in self._run_hg('branches').split('\n'):
            yield line.split(' ')[0]

    def active_branch(self):
        return self._run_hg("branch")

    def current_tag(self):
        try:
            return list(self.list_tags())[-1]
        except IndexError:
            return None

    def list_tags(self):
        """
        Lists tags according to .hgtags

        @yield: (checksum, tag)
        """
        try:
            tags = open(os.path.join(self.repo, ".hgtags"))
        except IOError:
            pass
        else:
            for tag in tags:
                yield tag.strip().split(" ", 1)

    def _run_hg(self, cmd):
        cmd = ['hg', cmd, '-R', self.repo]
        return subprocess.check_output(cmd).strip()
        


if __name__ == '__main__':
    import sys
    fn = sys.argv[1] if len(sys.argv) > 1 else None
    print get_version_name(fn)

