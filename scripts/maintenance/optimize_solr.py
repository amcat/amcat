if __name__ == '__main__':
    import solr
    s = solr.SolrConnection('http://localhost:8983/solr')
    s.optimize()
