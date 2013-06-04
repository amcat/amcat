import requests
import logging
import rdflib
import csv

log = logging.getLogger(__name__)

# TODO: query and update use http form instead of REST, what am I doing wrong?

class SOHServer(object):
    def __init__(self, url, prefixes=None):
        self.url = url
        self.prefixes = {} if prefixes is None else prefixes
        self.session = requests.session()

    def get_triples(self, format="text/turtle", parse=True):
        url = "{self.url}/data?default".format(**locals())
        r = self.session.get(url, headers=dict(Accept=format))
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
            #print rdf
        r = self.session.request(method, url, headers={'Content-Type' : format}, data=rdf)
        if r.status_code != 204:
            raise Exception(r.text)

    def do_update(self, sparql):
        url = "{self.url}/update".format(**locals())
        #log.debug("Updating {url}:\n{sparql}".format(**locals()))
        r = self.session.post(url, data=dict(update=sparql), prefetch=True)
        if r.status_code != 200:
            raise Exception(r.text)

    def do_query(self, sparql, format="csv", parse=True):
        url = "{self.url}/query?default".format(**locals())
        r = self.session.post(url, data=dict(query=sparql, output=format), prefetch=True)
        if r.status_code != 200:
            raise Exception(r.text)
        if parse:
            return csv.reader(r.text.strip().split("\n")[1:])
        else:
            return r.text

    def _prefix_string(self, prefixes=None):
        if prefixes is None: prefixes = self.prefixes
        if isinstance(prefixes, dict):
            prefixes = "\n".join("PREFIX {k}: <{v}>".format(**locals())
                                 for (k,v) in prefixes.iteritems())
        return prefixes

    def update(self, where, insert="", delete="", prefixes=None):
        prefixes = self._prefix_string(prefixes)
        sparql = u"""{prefixes}
                    DELETE {{ {delete} }}
                    INSERT {{ {insert} }}
                    WHERE {{ {where} }}
                 """.format(**locals())
        self.do_update(sparql)

    def query(self, select, where, orderby=None, prefixes=None, format='csv', parse=True):
        prefixes=self._prefix_string(prefixes)
        if isinstance(select, (list, tuple)): select = " ".join(select)
        sparql = """{prefixes}
                    SELECT {select}
                    WHERE {{ {where} }}
                 """.format(**locals())
        if orderby:
            if isinstance(orderby, (list, tuple)): orderby = " ".join(orderby)
            sparql += "ORDER BY {orderby}".format(**locals())
        return self.do_query(sparql, format=format, parse=parse)
