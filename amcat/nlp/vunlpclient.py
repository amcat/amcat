###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of vunlp, the VU University NLP e-lab                 #
#                                                                         #
# vunlp is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# vunlp is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with vunlp.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

"""
The VU NLP eLab offers a web service to facilitate natural language preprocessing
by running the preprocessing jobs, e.g. on a computer cluster like SARA's lisa.

This module contains a class Connection to facilitate talking to the web service
for parsing files.

Command line usage:
  python client.py COMMAND argument [< text]
  
  where COMMAND is one of:
  - upload: upload the text to be parsed using the argument as parse_command,
            printing the resulting handle if successful
  - check: check the status of the file identified by the argument as handle
  - download: retrieve the parser output of the file identified by the argument as handle
"""

from __future__ import unicode_literals, print_function, absolute_import

import requests, logging

log = logging.getLogger(__name__)

DEFAULT_URL = 'http://nlp.labs.vu.nl/webservice/index.php'

# Templates for API calls, should be instantiated with .format(url=".."[,filename=".."])
REQUEST_STATUS= "{url}?filstat=status&filnam={filename}"
REQUEST_RETRIEVE = "{url}?getparse=getparse&filnam={filename}"
REQUEST_ID = "{url}?getID"

serverurl = 'http://nlp.labs.vu.nl/webservice/index.php'

class Client():
  """
  Class that communicates with the vu nlp web service to upload, check, and retrieve parses.

  Since each Connection has a unique id, use the same connection object for all actions on a file.
  """

  def __init__(self, url=DEFAULT_URL):
    """
    @param url: the url of the web service
    """
    self.url = url
    self._id = None

  def _get_filename(self):
    """Temporary method to create unique file name until the ws can do it for us"""
    if self._id is None:
      log.debug("Requesting unique ID from server")
      r = requests.get(REQUEST_ID.format(url=self.url))
      r.raise_for_status()
      self._id = r.text.strip()
      self._filename_sequence = 0
      log.debug("Initialized parser with id: {self._id}".format(**locals()))
    else:
      self._filename_sequence += 1
    return "{self._id}_{self._filename_sequence}".format(**locals())
    
  def upload(self, parsecommand, text):
    """
    Upload the given text for parsing with the given command
    @param parsecommand: the command to use for parsing
    @param text: The text to parse (as string or file object)
    @returns: the handle with which the results can be checked/retrieved
    """
    filename = self._get_filename()
    command =  "#!{parsecommand}\n{text}".format(**locals())
    log.debug("Uploading file {filename}".format(**locals()))
    r = requests.post(self.url, files=dict(infil = (filename, command)))
    r.raise_for_status()
    return filename

  def check(self, handle):
    """
    Check and return the parse status of the given file
    @param handle: a handle from a succesful upload_file call
    @returns: a string indicating the status of the file
    """
    r = requests.get(REQUEST_STATUS.format(url=self.url, filename=handle))
    r.raise_for_status()
    log.debug("Checked status for {handle}: status={r.text!r}".format(**locals()))
    return r.text.strip()

  def download(self, handle):
    """
    Retrieve the parse results for this file. Will throw an Exception if the file is not yet parsed.
    @param handle: a handle from a succesful upload_file call
    @return: a string containing the parse results
    """
    # TODO: Should the parser not return a 404 if a file is not found?
    r = requests.get(REQUEST_RETRIEVE.format(url=self.url, filename=handle))
    r.raise_for_status()
    #if r.result == "notfound\n":
    #  raise Exception('Could not retrieve {handle}'.format(**locals()))
    return r.content

if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG, format='[%(asctime)-15s %(name)s:%(lineno)d %(levelname)s] %(message)s')
  import sys
  if len(sys.argv) != 3:
    print(__doc__, file=sys.stderr)
    sys.exit(64)
  command, argument = sys.argv[1:]
  if command == "upload":
    text = sys.stdin.read()
    handle = Client().upload(argument, text)
    print(handle)
  elif command == "check":
    print(Client().check(argument))
  elif command == "download":
    print(Client().download(argument))

    
