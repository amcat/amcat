from amcat.tools import amcatlogging
amcatlogging.setup()

from amcat.tools.dot import dot2img
from amcat.tools import djangotoolkit
from django_extensions.management.modelviz import generate_dot

import sys, os.path

dest = sys.argv[1]
imgdir = os.path.join(os.path.dirname(dest), "img")

HTMLHEAD='''<html>
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
    <div class="content">'''
HTMLFOOT = '''</div>
  </body>
</html>
'''

out = open(dest, 'w')
out.write(HTMLHEAD)

for name, models, stoplist in [
    ('Projects & Authorisation', ('ProjectRole', 'Privilege'), ()),
    ('Articles', ['Sentence', 'Articleset'], ('Project',)),
    ('Coding Jobs', ['CodingJob', 'CodingSchemaField', 'ArticleSet'],('CodingJob','Project','User', 'Codebook')),
    ('Codebook', ['Codebook', 'CodebookCode', 'Code', 'Label', 'CodebookBase'], ['Project']),
    ('Codings', ['CodingValue'], ('Project', 'User','Article', 'CodingJob', 'CodingSchemaField')),
    ]:

    out.write("<h1>Model graph for %s</h1>" % name)

    models = djangotoolkit.get_related_models(models, stoplist)
    modelnames = [m.__name__ for m in models]

    dot = generate_dot(['amcat'], include_models=",".join(modelnames))
    dot = dot.replace("digraph name {", "digraph name {\ngraph [rankdir=LR];")
    
    imgfn = name.lower().replace("&","").replace(" ","_") + ".png"
    out.write("<img src='img/{imgfn}' title='{name}' alt='Model graph for {name}' />".format(**locals()))
    
    open(os.path.join(imgdir, imgfn), 'w').write(dot2img(dot, format='png'))



