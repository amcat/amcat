import requests
import logging
import rdflib

log = logging.getLogger(__name__)

class SOHServer(object):
    def __init__(self, url):
        self.url = url

    def get_triples(self, format="text/turtle", parse=True):
        url = "{self.url}/data?default".format(**locals())
        r = requests.get(url, headers=dict(Accept=format))
        if r.status_code != 200:
            raise Exception(r.text)
        result = r.text
        if parse:
            g = rdflib.Graph()
            result = g.parse(data=result, format="turtle")
        return result

    def add_triples(self, rdf, format="text/turtle", clear=False):
        method = "put" if clear else "post"
        url = "{self.url}/data?default".format(**locals())
        if isinstance(rdf, rdflib.Graph):
            rdf = rdf.serialize(format="turtle")
        r = requests.request(method, url, headers={'Content-Type' : format}, data=rdf)
        if r.status_code != 204:
            raise Exception(r.text)

    def update(self, sparql):
        url = "{self.url}/update".format(**locals())
        r = requests.post(url, data=dict(update=sparql))
        if r.status_code != 200:
            print r.status_code
            raise Exception(r.text)
        
