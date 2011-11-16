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

from amcat.tools.table import table3, tableoutput


HTML="""<html>
  <head>
   <link rel="stylesheet" href="/amcat.css" type="text/css" />
   <title>AmCAT Documentation</title>
  </head>
  <body>
    <div class="header"> </div>  
    <div class="sidebar"><h3>Links</h3>
     <ul>
     <li> <a href="http://amcat.vu.nl/api">Documentation</a></li>
     <li> <a href="http://amcat.vu.nl/api">Unit tests</a></li>
     <li><a href="http://amcat.vu.nl/api/model_amcat_trunk.html">Object model</a></li>
      <li><a href="http://code.google.com/p/amcat/w">Wiki</a></li>
      <li><a href="http://code.google.com/p/amcat/source/list">Source</a></li>
     </ul>
    </div>
    <div class="content">{content}</div>
  </body>
</html>
"""

GRAPHSCRIPT = "{path}/create_model_graphs.py".format(path=toolkit.get_script_path())
GRAPHCMD = "PYTHONPATH={tmpdir} DJANGO_SETTINGS_MODULE=amcat.settings python {GRAPHSCRIPT}"
GRAPHDEST = '{outdir}/model_{reponame}_{branch}.html'
WWWGRAPHDEST = '{wwwroot}/model_{reponame}_{branch}.html'

SOURCE = "http://code.google.com/p/amcat/source/browse?name={branch}&repo={reponame2}"

REPOLOC = "https://code.google.com/p/{reponame}"
REPONAMES = ["amcat", "amcat.scraping", "amcat.navigator"]

    
OUTDIR_DEFAULT = '/var/www/api'
WWWROOT_DEFAULT = 'http://amcat.vu.nl/api'

EPYDOCCMD = ('epydoc -v --simple-term -n "AmCAT Documentation {reponame} ({branch}) --show-sourcecode'
             +' --navlink="<a href=\"{wwwroot}/index.html\" target="_top">AmCAT Documentation Index</a>'
             +' -o "{docdest}" "{repo.repo}" ')

DOCDEST = '{outdir}/{reponame}/{branch}/'
LOGFILE = '{outdir}/log_{reponame}_{branch}.txt'
INDEX = '{outdir}/index.html'
WWWDOCDEST = '{wwwroot}/{reponame}/{branch}/'
WWWLOGDEST = '{wwwroot}/log_{reponame}_{branch}.txt'


TESTFILE = '{outdir}/test_{reponame}_{branch}.txt'
WWWTESTDEST = '{wwwroot}/test_{reponame}_{branch}.txt'
COVERAGEFILE = '{outdir}/cov_{reponame}_{branch}.txt'
WWWCOVERAGEDEST = '{wwwroot}/cov_{reponame}_{branch}.txt'

TESTCMD = ("PYTHONPATH={tmpdir} DJANGO_SETTINGS_MODULE=amcat.settings python-coverage run"
           +" manage.py test --noinput {testapp}")
COVERAGECMD = "python-coverage report --omit=/usr" 

if len(sys.argv) > 1:
    outdir = sys.argv[1]
    wwwroot = 'file://{outdir}'.format(**locals())
else:
    outdir = OUTDIR_DEFAULT
    wwwroot = WWWROOT_DEFAULT

log = amcatlogging.setup()

if not os.path.exists(outdir): os.makedirs(outdir) # make sure target exists

doc = table3.ObjectTable()
test = table3.ObjectTable()

for reponame in REPONAMES:
    repolocation = REPOLOC.format(**locals())
    # clone repositorymkdtemp
    tmpdir = tempfile.mkdtemp()
    repodir = '{tmpdir}/{reponame}'.format(**locals())
    log.info("{reponame}: Cloning {repolocation} to {repodir}".format(**locals()))
    repo = hg.clone(repolocation, repodir)

    for branch in repo.listbranches():
        row = dict(repo=reponame, branch=branch)
        doc.rows.append(row)

        # prepare variables, update to selected branch
        docdest = DOCDEST.format(**locals())
        logfile = LOGFILE.format(**locals())
        log.info("Documenting {reponame}::{branch}".format(**locals()))
        repo.update(revision=branch)

        # run epydoc
        if not os.path.exists(docdest): os.makedirs(docdest) # make sure target exists
        out, err = toolkit.execute(EPYDOCCMD.format(**locals()))
        open(LOGFILE.format(**locals()), 'w').write("{0}\n----\n{1}".format(out, err))
        
        # add entries for table
        wwwdocdest = WWWDOCDEST.format(**locals())
        row["frames"] = '{wwwdocdest}index.html'.format(**locals())
        row["noframes"] = '{wwwdocdest}{reponame}-module.html'.format(**locals())
        row["log"] = WWWLOGDEST.format(**locals())
        reponame2 = "default" if reponame=="amcat" else reponame.replace("amcat.","")
        row["source"] = SOURCE.format(**locals())
                
        if reponame == 'amcat':
            # create model graph (only for repo amcat, hard hack atm..)
            log.info("Creating model graph for {reponame}".format(**locals()))
            log.info(GRAPHCMD.format(**locals()))
            html, err = toolkit.execute(GRAPHCMD.format(**locals()))
            if err: html = "Error on generating graph:<pre>{err}</pre>".format(**locals())
            open(GRAPHDEST.format(**locals()), 'w').write(HTML.format(content=html))
            wwwgraphdest = WWWGRAPHDEST.format(**locals())
            row["model"] = wwwgraphdest

            # run unit tests (only for repo amcat...)
            for testapp in ["amcat"]:
                testrow = dict(repo=reponame, branch=branch, testapp=testapp)
                test.rows.append(testrow)
                
                log.info("Running unit tests for {reponame}:{branch}:{testapp}".format(**locals()))
                appname = reponame.replace(".","")
                log.info(TESTCMD.format(**locals()))
                out, err = toolkit.execute(TESTCMD.format(**locals()))
                testrow["testresult"] = err.split("\n")[-2].strip()
                open(TESTFILE.format(**locals()), 'w').write(err)
                testrow["testreport"] = WWWTESTDEST.format(**locals())
                log.info("Determining unit test coverage for {reponame}".format(**locals()))
                log.info(COVERAGECMD.format(**locals()))
                cov = toolkit.execute(COVERAGECMD.format(**locals()), outonly=True)
                testrow["coverage"] = cov.split("\n")[-2].strip()
                open(COVERAGEFILE.format(**locals()), 'w').write(cov)
                testrow["coveragereport"] = WWWCOVERAGEDEST.format(**locals())
        
        
    shutil.rmtree(tmpdir)
        
script= sys.argv[0]
stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


content = "<h1>AmCAT Documentation </h1>"

doc.addColumn(lambda r:r["repo"], "Repository")
doc.addColumn(lambda r:r["branch"], "Branch")
doc.addColumn(lambda r:"<a href='{frames}'>frames</a> | <a href='{noframes}'>no frames</a>".format(**r), "API Documentation")
doc.addColumn(lambda r:"<a href='{log}'>(log)</a>".format(**r), "Log")
#doc.addColumn(lambda r:"<a href='{model}'>View</a>".format(**r) if r.get("model") else "-" , "Model")
doc.addColumn(lambda r:"<a href='{source}'>Source</a>".format(**r), "Source")

content += tableoutput.table2html(doc, printRowNames=False, border=False)

content += "<h1>Unit test results</h1>"


test.addColumn(lambda r:r["repo"], "Repository")
test.addColumn(lambda r:r["branch"], "Branch")
test.addColumn(lambda r:r["testapp"], "App")
test.addColumn(lambda r:"<a href='{testreport}'>{testresult}</a>".format(**r), "Unit test")
test.addColumn(lambda r:"<a href='{coveragereport}'>{coverage}</a>".format(**r), "Coverage")

content += tableoutput.table2html(test, printRowNames=False, border=False)

content += "<p></p><p><i>Documentation generated by {script} at {stamp})".format(**locals())


open(INDEX.format(**locals()), "w").write(HTML.format(content=content))
