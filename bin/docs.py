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
Usage: python docs.py [destination]

Generates api documentation for all branches of the repositories
in REPONAMES at REPOLOC. If destination is not given, assume
that it should go to the www/api directory.
"""

import subprocess, sys, os.path, os, tempfile, datetime, shutil
from amcat.tools import hg, toolkit
from amcat.tools.logging import amcatlogging
from amcat.tools import toolkit


GRAPHSCRIPT = "{path}/create_model_graphs.py".format(path=toolkit.get_script_path())
GRAPHCMD = "PYTHONPATH=~/tmp:{tmpdir} DJANGO_SETTINGS_MODULE=amcat.settings python2.6 {GRAPHSCRIPT}"
#~/tmp = hack for old amcat!
GRAPHDEST = '{outdir}/model_{reponame}_{branch}.html'
WWWGRAPHDEST = '{wwwroot}/model_{reponame}_{branch}.html'

REPOLOC = "ssh://amcat.vu.nl:2222//home/amcat/hg/amcat3/{reponame}"
REPOLOC_NOSSH = "/home/amcat/hg/amcat3/{reponame}"
REPONAMES = ("amcat", "amcatscraping", "amcatnavigator")

OUTDIR_DEFAULT = '/home/amcat/www/api'
WWWROOT_DEFAULT = 'http://amcat.vu.nl/api'

DOCDEST = '{outdir}/{reponame}/{branch}/'
LOGFILE = '{outdir}/log_{reponame}_{branch}.txt'
INDEX = '{outdir}/index.html'
WWWDOCDEST = '{wwwroot}/{reponame}/{branch}/'
WWWLOGDEST = '{wwwroot}/log_{reponame}_{branch}.txt'

if len(sys.argv) > 1:
    outdir = sys.argv[1]
    wwwroot = 'file://{outdir}'.format(**locals())
else:
    outdir = OUTDIR_DEFAULT
    wwwroot = WWWROOT_DEFAULT
    REPOLOC = REPOLOC_NOSSH # allows cron to run 

log = amcatlogging.setup()

if not os.path.exists(outdir): os.makedirs(outdir) # make sure target exists

indexfile = open(INDEX.format(**locals()), "w")
indexfile.write("""<html><head><title>AmCAT Documentation</title></head><body><h1>AmCAT Documentation </h1>
Click on the packages / versions below to browse the inline
documentation of the AmCAT repositories:\n\n<ul>
""")


for reponame in REPONAMES:
    repolocation = REPOLOC.format(**locals())
    # clone repositorymkdtemp
    tmpdir = tempfile.mkdtemp()
    repodir = '{tmpdir}/{reponame}'.format(**locals())
    log.info("{reponame}: Cloning {repolocation} to {repodir}".format(**locals()))
    repo = hg.clone(repolocation, repodir)

    for branch in repo.listbranches():
        wwwdocdest = WWWDOCDEST.format(**locals())
        wwwlogdest = WWWLOGDEST.format(**locals())
        docdest = DOCDEST.format(**locals())
        logfile = LOGFILE.format(**locals())
        log.info("Documenting {reponame}::{branch} to {wwwdocdest}".format(**locals()))
        repo.update(revision=branch)
        if not os.path.exists(docdest): os.makedirs(docdest) # make sure target exists
        cmd = r'epydoc -v --simple-term -n "AmCAT Documentation {reponame} ({branch})"'
        cmd += r' --navlink="<a href=\"{wwwroot}/index.html\" target="_top">AmCAT Documentation Index</a>"'
        cmd += r' -o "{docdest}" "{repo.repo}" > {logfile} 2>&1'
        toolkit.execute(cmd.format(**locals()))
        indexfile.write("<li><a href='{wwwdocdest}/index.html'>{reponame} ({branch})</a>".format(**locals()))
        indexfile.write(" | <a href='{wwwdocdest}/{reponame}-module.html'>(no frames)</a>".format(**locals()))
        indexfile.write(" | <a href='{wwwlogdest}'>(log)</a>".format(**locals()))


        if reponame == 'amcat':
            log.info("Creating model graph for {reponame}".format(**locals()))
            log.info(GRAPHCMD.format(**locals()))
            html, err = toolkit.execute(GRAPHCMD.format(**locals()))
            if err: html = "Error on generating graph:<pre>{err}</pre>".format(**locals())
            open(GRAPHDEST.format(**locals()), 'w').write(html)
            wwwgraphdest = WWWGRAPHDEST.format(**locals())
            indexfile.write("| <a href='{wwwgraphdest}'>(model graph)</a>".format(**locals()))
    shutil.rmtree(tmpdir)
        
script= sys.argv[0]
stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
indexfile.write("""</ul>(Documentation generated by {script} at {stamp})</body></html>""".format(**locals()))

