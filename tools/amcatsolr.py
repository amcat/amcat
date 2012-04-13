import tempfile, os.path, shutil, os

import logging
log = logging.getLogger(__name__)

def start_test_solr():
    # folder for temp solr home
    temp_solr_home = tempfile.mkdtemp()
    port = 1234
    
    # find amcat solr home
    import amcat
    amcat_home = os.path.dirname(amcat.__file__)
    solr_home = os.path.abspath(os.path.join(amcat_home, "../amcatsolr"))
    if not os.path.exists(os.path.join(solr_home, "solr/solr.xml")):
        raise Exception("Solr.xml not found at {solr_home}".format(**locals()))
    
    

    cmd = ("cd {solr_home} && java -Djetty.port={port} -Dsolr.data.dir={temp_solr_home}  -jar start.jar"
           .format(**locals()))
    os.system(cmd)
    
    

from amcat.tools import amcatlogging
amcatlogging.setup()
start_test_solr()

