from __future__ import unicode_literals, print_function, absolute_import

import logging; log = logging.getLogger(__name__)

from django.db import transaction

from amcat.tools import amcattest
from amcat.tools import djangotoolkit

@transaction.commit_on_success
def profile_store_triples():
    transaction.enter_transaction_management()
    transaction.managed(True)
    try:
        aa = amcattest.create_test_analysis_article()
        log.info("Created test article %i" % aa.id)
        tokens = []
        for s in range(10):
            log.info("Creating test sentence %i" % s)
            s = amcattest.create_test_analysis_sentence(aa)
            log.info("Created test sentence %i" % s.id)

            tokens += [amcattest.create_tokenvalue(analysis_sentence=s, word=w, lemma=w) for w in "abcdefghijkl"*10]
        log.info("Storing %i tokens" % len(tokens))
        with djangotoolkit.list_queries() as queries:
            aa.store_analysis(tokens=tokens)
        djangotoolkit.query_list_to_table(queries, maxqlen=200, output=print, encoding="utf-8")
    finally:
        transaction.rollback()
        transaction.leave_transaction_management()


if __name__ == '__main__':
    from amcat.tools import amcatlogging
    amcatlogging.setup()
    profile_store_triples()
