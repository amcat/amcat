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
# Based on (but mostly rewritten) 
#    https://github.com/dasmith/stanford-corenlp-python (GPL)

"""
Python interface for the Stanford CoreNLP suite.
Command line interface allows running it directly or as server/client.
"""

import os, sys, time
import re
import logging
import pexpect
from unidecode import unidecode
from jsonrpclib import SimpleJSONRPCServer, Server
from cStringIO import StringIO

log = logging.getLogger(__name__)


def _debug_lines(lines):
    for line in lines:
	log.debug("<<< {line}".format(**locals()))
	yield line

def parse_results(lines):
    """ This is the nasty bit of code to interact with the command-line
    interface of the CoreNLP tools.  Takes a string of the parser results
    and then returns a Python list of dictionaries, one for each parsed
    sentence.
    """
    lines = _debug_lines(lines)
    lines = iter(lines)
    lines.next() # skip first line (echo of sentence)
    sentences = list(parse_sentences(lines))

    coref = list(parse_coreferences(lines))
    return sentences, coref

def parse_sentences(lines):
    while True:
	try:
	    yield parse_sentence(lines)
	except StopIteration:
	    break

def parse_sentence(lines):
    """
    Parse a sentence from the lines iterator, consuming lines in the process
    Raises StopIteration if the end of the sentences is reached (explicitly or from lines.next())
    """
    nr = get_sentence_no(lines)
    text = lines.next()
    log.debug("Parsing sentence {nr}: {text!r}".format(**locals()))
    # split words line into minimal bracketed chunks and parse those
    words = [dict(parse_word(s)) for s in re.findall('\[([^\]]+)\]', lines.next())]
    parsetree = " ".join(p.strip() for p in parse_tree(lines))
    tuples = list(parse_tuples(lines))
    return dict(nr=nr, text=text, words=words, tuples=tuples, parsetree=parsetree)

def get_sentence_no(lines):
    """Return the sentence number, or raise StopIteration if EOF or Coreference Set is reached"""
    line = lines.next()
    while not line.strip(): line = lines.next() # skip leading blanks
    if line == "Coreference set:":
	raise StopIteration 
    m = re.match("Sentence #\s*(\d+)\s+", line)
    if not m: raise Exception("Cannot interpret 'sentence' line {line!r}".format(**locals()))
    return int(m.group(1))

def parse_tree(lines):
    for line in lines:
	if not line.strip():
	    break
	yield line

def parse_tuples(lines):
    for line in lines:
	if not line.strip():
	    return
	m = re.match(r"(\w+)\(.+-([0-9']+), .+-([0-9']+)\)", line)
	if not m:
	    raise Exception("Cannot interpret 'tuples' line: {line!r}".format(**locals()))
	yield m.groups()

def parse_word(s):
  '''Parse word features [abc=... def = ...]
  Also manages to parse out features that have XML within them
  @return: an iterator of key, value pairs
  '''
  # Substitute XML tags, to replace them later
  temp = {}
  for i, tag in enumerate(re.findall(r"(<[^<>]+>.*<\/[^<>]+>)", s)):
    temp["^^^%d^^^" % i] = tag
    s = s.replace(tag, "^^^%d^^^" % i)
  for attr, val in re.findall(r"([^=\s]*)=([^=\s]*)", s):
    if val in temp:
      val = temp[val]
    else:
	yield attr, val

def parse_coref_group(s):
    s = s.replace("[", "")
    s = s.replace(")", "")
    return map(int, s.split(","))

def parse_coreferences(lines):
    while True:
	coref = list(parse_coreference(lines))
	if not coref:
	    break
	yield coref

def parse_coreference(lines):
    for line in lines:
	if line == "Coreference set:":
	    return
	m = re.match(r'\s*\((\S+)\) -> \((\S+)\), that is: \".*\" -> \".*\"', line)
	yield map(parse_coref_group, m.groups())
	
class StanfordCoreNLP(object):
    """ 
    Command-line interaction with Stanford's CoreNLP java utilities.

    Can be run as a JSON-RPC server or imported as a module.
    """
    
    def __init__(self, corenlp_path=".", corenlp_version="2012-07-09", models_version=None, timeout=600):
        """
	Start the CoreNLP server as a java process. Arguments are used to locate the correct jar files.

	@param corenlp_path: the directory containing the jar files
	@param corenlp_version: the yyyy-mm-dd version listed in the jar name
	@param models_version: if different from the main version, the version date of the models jar
	@param timeout: Time to wait for a parse before giving up
        """
	self.timeout = timeout
	
	classpath = self._get_classpath(corenlp_path, corenlp_version, models_version)
	
        classname = "edu.stanford.nlp.pipeline.StanfordCoreNLP"
        cmd = "java -Xmx3000m -cp {classpath} {classname}".format(**locals())

        log.info("Starting the Stanford Core NLP parser.")
	log.debug("Command: {cmd}".format(**locals()))
        self._corenlp_process = pexpect.spawn(cmd)	
        self._wait_for_corenlp_init()

    def _get_classpath(self, corenlp_path, corenlp_version, models_version=None):
	"""
	Construct the classpath from jar names, base path, and version number.
	Raises an Exception if any of the jars cannot be found
	"""
	if models_version is None: models_version = corenlp_version

        jars = ["stanford-corenlp-{corenlp_version}.jar".format(**locals()),
                "stanford-corenlp-{models_version}-models.jar".format(**locals()),
                "joda-time.jar",
                "xom.jar"]
        
        jars = [os.path.join(corenlp_path, jar) for jar in jars]
        for jar in jars:
            if not os.path.exists(jar):
                raise Exception("Error! Cannot locate {jar}".format(**locals()))
        return ":".join(jars)

    def _wait_for_corenlp_init(self):
	"""Give some progress feedback while waiting for server to initialize"""
	for module in ["Pos tagger", "NER-all", "NER-muc", "ConLL", "PCFG"]:
	    log.debug("Loading {module}".format(**locals()))
	    self._corenlp_process.expect("done.", timeout=600)
	log.debug(" ..  Finished loading modules...")
        self._corenlp_process.expect("Entering interactive shell.")
        log.info("NLP tools loaded.")


    def _get_results(self):
	"""
	Get the raw results from the corenlp process
	"""
	copy = open("/tmp/parse_log", "w")
	buff = StringIO()
	while True: 
            try:
		incoming = self._corenlp_process.read_nonblocking (2000, 1)
            except pexpect.TIMEOUT:
		log.debug("Waiting for CoreNLP process; buffer: {!r} ".format(buff.getvalue()))
		continue
	    # original broke out of loop on EOF, but EOF is unexpected so rather raise exception
		
	    for ch in incoming:
		copy.write(ch)
		if ch == "\n": # return a found line
		    yield buff.getvalue()
		    buff.seek(0)
		    buff.truncate()
		elif ch not in "\r\x07":
		    buff.write(ch)
		    if ch == ">" and buff.getvalue().startswith("NLP>"):
			return

    def _parse(self, text):
        """
	Call the server and parse the results.
	@return: (sentences, coref)
        """
        # clean up anything leftover, ie wait until server says nothing in 0.3 seconds
        while True:
            try:
                ch = self._corenlp_process.read_nonblocking(4000, 0.3)
            except pexpect.TIMEOUT:
                break

        self._corenlp_process.sendline(text)

        return parse_results(self._get_results())

    def parse(self, text):
        """ 
        This function parses a text string, sends it to the Stanford parser,
        @return: (sentences, coref)
        """
        log.debug("Request: {text}".format(**locals()))
        results = self._parse(text)	
	log.debug("Result: {results}".format(**locals()))
	return results

def serve(host="localhost", port=8080, **kargs):
    server = SimpleJSONRPCServer.SimpleJSONRPCServer((host, port))
    nlp = StanfordCoreNLP(**kargs)
    server.register_function(nlp.parse)
    print 'Serving on http://{host}:{port}/'.format(**locals())
    server.serve_forever()
    
def parse_remote(text, host="localhost", port=8080):
    uri = 'http://{host}:{port}/'.format(**locals())
    server = Server(uri)
    result = server.parse(text)
    if "error" in result:
        raise Exception("Error from remote parser: {result[error]}".format(**locals()))
    if "sentences" not in result:
        print `result`
        raise Exception("Cannot parse result")
    return result["sentences"], result.get("coref", [])

def parse_text(text, **kargs):
    nlp = StanfordCoreNLP(**kargs)
    return nlp.parse(text)

class CoreNLPStarter(object):
    def __init__(self, hostname, port, **corenlp_options):
	self.corenlp_options = corenlp_options
    def _read_text(self):
	if os.isatty(0):
	    log.info("Reading text from stdin, press EOF (^D) when ready")
	return sys.stdin.read()
	
    def parse(self):
	text = self._read_text()
	nlp = StanfordCoreNLP(**self.corenlp_options)
        sentences, coref = nlp.parse(text)
	
        print "Parsed {} sentences".format(len(sentences))
        for i, sentence in enumerate(sentences):
            print " #{i}: {sentence[text]!r}".format(**locals())
            print "   Words: ", sentence["words"]
            print "   Parse: ", sentence["tuples"]
        
        print "\nCoreference structure:\n", coref

if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    
    actions = [name for name in dir(CoreNLPStarter) if not name.startswith('_')]
    parser.add_argument('action', help='Action to take', choices=actions)
    
    parser.add_argument('--port', '-p', type=int, help='Port number for the server', default=9001)
    parser.add_argument('--hostname', '-H', help='Server host name', default='localhost')

    parser.add_argument('--corenlp_path', '-c', dest="corenlp_path", help='Path to CoreNLP jar files')
    parser.add_argument('--corenlp_version', '-V', help='Version (ie 2012-01-01) of the corenlp jar')
    parser.add_argument( '--models_version', '-m',
			help='Version (ie 2012-01-01) of the models jar, if different from corenlp_version')

    parser.add_argument('--verbose', '-v', help='Print debug messages', action='store_true')
    args = parser.parse_args()

    log_level = logging.DEBUG if args.__dict__.pop('verbose', False) else logging.INFO
    logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s', level=log_level)
        
    # create starter and run requested action
    action = args.__dict__.pop('action')
    options = {k:v for (k,v) in args.__dict__.iteritems() if v is not None}
    log.debug("Calling action {action!r} with options {options!r}".format(**locals()))
    s = CoreNLPStarter(**options)
    getattr(s, action)()
