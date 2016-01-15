from amcat.scripts.script import Script
from django import forms
import logging;
import re
import requests
import itertools
import json
import csv
import time
import tempfile

from cStringIO import StringIO

log = logging.getLogger(__name__)

RE_PAGE = "(?<=[&?]page=)\d+(?=$|&)"

def get(url, max_retry=3, allowed_status=(200, 404), **opts):
    for attempt in itertools.count():
        r = requests.get(url, **opts)
        logging.debug("GET {url} {r.status_code}".format(**locals()))
        if r.status_code in allowed_status:
            return r
        logging.error("Unexpected status code {r.status_code}"
                      .format(**locals()))
        if attempt >= max_retry:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(r.content)
                raise Exception("Failed to get {url} after {attempt} tries: "
                                "{r.status_code}. Content written to {f.name}"
                                .format(**locals()))
        logging.warn("Retrying ({attempt} / {max_retry}) in 1 sec..."
                     .format(**locals()))
        time.sleep(1)

class CollectAPI(Script):
    """
    Iterate over all pages in an API call and collect them in one file
    """

    class options_form(forms.Form):
        api_url = forms.CharField()
        token = forms.CharField(required=False)
        maxpage = forms.IntegerField(required=False)
        start = forms.IntegerField(initial=1)

    def _run(self, api_url, token, maxpage, start):
        # get the page= part from the url.
        # We *could* use urlparse+parse_qs+urlencode, but that just feels more complicated

        
        api_url = (re.sub(RE_PAGE, "{page}", api_url) if re.match(RE_PAGE, api_url)
                   else "{api_url}&page={{page}}".format(**locals()))

        headers = {} if not token else {'Authorization': "Token {token}".format(**locals())}

        output = StringIO()
        handler = None
        for i in itertools.count(start):
            r = get(api_url.format(page=i), headers=headers)
            if r.status_code == 404:
                break # done!
            if handler is None:
                handler = HANDLERS[r.headers['content-type']](output)
            handler.add(r)
            if maxpage and i == maxpage:
                break
        if handler != None:
            return handler.result()

        

class CSVHandler(object):
    def __init__(self, output):
        self.header = []
        self.header_changed = False
        self.headerpos = None
        self.output = output
        self.w = csv.writer(output)
    def add(self, response):
        r = csv.reader(StringIO(response.content))
        header = r.next()
        remap_fields = None
        if self.header:
            if self.header != header:
                extra = [h for h in header if h not in self.header]
                self.header += extra
                remap_fields = [(header.index(h) if h in header else None)
                                for h in self.header]
                if extra:
                    self.header_changed = True
        else:
            self.header = header
            self.w.writerow(header)
            self.headerpos = self.output.tell()

        for row in r:
            if remap_fields:
                row = [(None if i is None else row[i]) for i in remap_fields]
            self.w.writerow(row)
    def result(self):
        if self.header_changed:
            logging.debug("Replacing header")
            output = StringIO()
            csv.writer(output).writerow(self.header)
            return output.getvalue() + self.output.getvalue()[self.headerpos:]
        else:
            return self.output.getvalue()

        
class JsonHandler(object):
    def __init__(self, output):
        self.data = None
    def add(self, response):
        data = response.json()
        assert 'results' in data
        if self.data is None:
            self.data = data
        else:
            self.data['results'] += data['results']
    def result(self):
        return json.dumps(self.data, indent=2)
        
HANDLERS = {'application/json': JsonHandler, 'text/csv; charset=utf-8' : CSVHandler}

                            
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    print cli.run_cli()
