import subprocess, sys, os.path, os, tempfile
from amcat.tools import hg, toolkit
from amcat.tools.logging import amcatlogging


REPOLOC = "ssh://amcat.vu.nl:2222//home/amcat/hg/amcat3/{reponame}"
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

log = amcatlogging.setup()

if not os.path.exists(outdir): os.makedirs(outdir) # make sure target exists

indexfile = open(INDEX.format(**locals()), "w")
indexfile.write("""<html><body><h1>AmCAT Documentation </h1>
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
        log.info("Documenting {repo}::{branch} to {wwwdocdest}".format(**locals()))
        repo.update(revision=branch)
        if not os.path.exists(docdest): os.makedirs(docdest) # make sure target exists
        cmd = r'epydoc -v --simple-term -n "AmCAT Documentation {reponame} ({branch})"'
        cmd += r' --navlink="<a href=\"{wwwdroot}/index.html\" target="_top">AmCAT Documentation Index</a>"'
        cmd += r' -o "{docdest}" "{repo.repo}" > {logfile} 2>&1'
        toolkit.execute(cmd.format(**locals()))
        indexfile.write("<li><a href='{wwwdocdest}/index.html'>{reponame} ({branch})</a>".format(**locals()))
        indexfile.write("<a href='{wwwdocdest}/{reponame}-module.html'>(no frames)</a>".format(**locals()))
        indexfile.write("<a href='{wwwlogdest}'>(log)</a>".format(**locals()))
        
indexfile.write("""</ul></body></html>""")

