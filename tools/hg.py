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

Uses toolkit.execute to run hg as external process
"""

import toolkit, os.path

def getRepo(fn):
    """Get the repository to which file/folder fn belongs"""
    if os.path.exists(os.path.join(fn, ".hg")): return fn
    parent = os.path.dirname(fn) #dirname("/") == "/"
    if parent != fn: return getRepo(parent) 

def getStatus(fn):
    """Get the hg status of fn"""
    repo = getRepo(fn)
    if not repo or not os.path.exists(fn): return
    cmd = 'hg -R "%s" status -A "%s"' % (repo, fn)
    st = toolkit.execute(cmd, outonly=True).strip()
    if not st: return 
    return st[0]


def getRepoStatus(fn):
    """Yield file, status tuples for all files in the repo of fn"""
    repo = getRepo(fn)
    if not repo: return
    cmd = 'hg -R "%s" status -A' % repo
    for st in toolkit.execute(cmd, outonly=True).split("\n"):
        if not st.strip(): continue
        yield st[2:], st[0]

def getLastEditUser(fn):
    """Get the username who made the last commit to this file"""
    repo = getRepo(fn)
    if not repo or not os.path.exists(fn): return
    cmd = 'hg -R "%s" log %s/%s | head -3 | tail -1' % (repo, repo, fn)
    for line in toolkit.execute(cmd, outonly=True).split("\n"):
        if line.startswith("user:"):
            return line[5:].strip()
    return "?"
