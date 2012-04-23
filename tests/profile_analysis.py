from __future__ import unicode_literals, print_function, absolute_import

from django.db import transaction
from amcat.tools import amcattest

from amcat.tools import djangotoolkit

@transaction.commit_on_success
def profile_store_triples():
    transaction.enter_transaction_management()
    transaction.managed(True)
    try:
        aa = amcattest.create_test_analysis_article()
        tokens = []
        for s in range(10):
            s = amcattest.create_test_analysis_sentence(aa)

            tokens += [amcattest.create_tokenvalue(analysis_sentence=s, word=w, lemma=w) for w in "abcdefghijklm"*3]
        print(tokens)
        with djangotoolkit.list_queries() as queries:
            aa.store_analysis(tokens=tokens)
        djangotoolkit.query_list_to_table(queries, maxqlen=200, output=print)
    finally:
        transaction.rollback()
        transaction.leave_transaction_management()


if __name__ == '__main__':
    profile_store_triples()