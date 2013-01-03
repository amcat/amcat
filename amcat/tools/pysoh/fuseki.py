import os
import subprocess
import time
import logging

from pysoh import SOHServer

log = logging.getLogger(__name__)

FUSEKI_HOME="/home/amcat/resources/fuseki"

class Fuseki(SOHServer):
    def __init__(self, fuseki_home=None, port=3030, dataset="/data"):
        if fuseki_home is None:
            fuseki_home = os.environ.get('FUSEKI_HOME', FUSEKI_HOME)

        cmd = ["/bin/bash", "fuseki-server", "--port", str(port), "--mem", "--update", dataset]
        log.debug("Starting Fuseki server from {fuseki_home} with {cmd}".format(**locals()))
        self.fuseki_process = subprocess.Popen(cmd, cwd=fuseki_home,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = []
        while True:
            line = self.fuseki_process.stdout.readline()
            out.append(line.strip())
            if ":: Started " in line: break
            if "ERROR" in line or '/bin/bash' in line or self.fuseki_process.poll() is not None:
                raise Exception("\n".join(out))
        time.sleep(.1) # give the 'port in use' exception time
        if self.fuseki_process.poll() is not None:
            out.append(self.fuseki_process.stdout.read())
            raise Exception("\n".join(out))

        url = "http://localhost:{port}{dataset}".format(**locals())
        log.info("Fuseki running at {url}".format(**locals()))

        super(Fuseki, self).__init__(url=url)

    def __del__(self):
        try:
            self.fuseki_process.terminate()
            self.fuseki_process.wait()
            log.info("Terminated Fuseki process")
            del self.fuseki_process
        except:
            pass


if __name__ == '__main__':
    from amcat.tools import amcatlogging
    amcatlogging.setup()

    amcatlogging.debug_module()
    s = Fuseki()

    print s.get_triples()

    rdf = """@prefix : <http://www.example.org/#> .
             []   :Location  [:label "test";
                              :friend :bla];"""

    print "---"
    print s.add_triples(rdf, clear=True)
    print "---"
    print s.get_triples()

    update = """PREFIX : <http://www.example.org/#>
     INSERT { ?x :bla ?y }
     WHERE  { ?x :label ?y}"""

    s.update(update)
    print "---"
    print s.get_triples()
