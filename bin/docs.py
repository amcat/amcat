HGFILE = '/home/amcat/www/hg/hgweb.config'
OUT = '/home/amcat/www/api/'
WWWROOT = 'http://amcat.vu.nl/api/'

import subprocess, sys, os.path

indexfile = open(OUT+"index.html", "w")

indexfile.write("""
<html><body><h1>AmCAT Documentation </h1>
Click on the packages / versions below to browse the inline documentation of the AmCAT repositories:

<ul>
""")

for line in open(HGFILE):
    if '=' in line:
        name, path = line.split('=')
        package = path.strip() + "/"
        # can we find a package?
        if not os.path.exists(package + '__init__.py'):
            sys.stderr.write("Skipping %s, not a package\n" % package)
            continue
        
        name = name.strip()
        lname = name.replace("/","_")
        output = OUT + lname
        errname = "err_"+lname + ".txt"
        error = OUT + errname
        cmd = r'epydoc -v --simple-term -n "AmCAT Documentation %s" --navlink="<a href=\"%s\" target="_top">AmCAT Documentation Index</a>"  -o "%s" "%s" > %s 2>&1' % (name, WWWROOT, output, package, error)
        sys.stderr.write("Running %r\n" % cmd)
        subprocess.Popen(cmd, shell=True).wait()
        indexfile.write("<li><a href='%s%s'>%s</a> (<a href='%s%s'>log</a>)" % (WWWROOT, lname, name, WWWROOT, errname))
        

indexfile.write("""</ul></body></html>""")
