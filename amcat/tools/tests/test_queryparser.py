from amcat.tools import amcattest
from amcat.tools.queryparser import parse_to_terms, QueryParseError, parse


class TestQueryParser(amcattest.AmCATTestCase):
    def test_parse(self):
        q = lambda s: unicode(parse_to_terms(s))

        self.assertEqual(q('a'), '_all::a')
        self.assertEqual(q('a b'), 'OR[_all::a _all::b]')
        self.assertEqual(q('a OR b'), 'OR[_all::a _all::b]')
        self.assertEqual(q('a AND b'), 'AND[_all::a _all::b]')
        self.assertEqual(q('a NOT b'), 'NOT[_all::a _all::b]')
        self.assertEqual(q('a AND (b c)'), 'AND[_all::a OR[_all::b _all::c]]')
        self.assertEqual(q('(a AND b) c'), 'OR[AND[_all::a _all::b] _all::c]')

        # starting with NOT
        self.assertEqual(q('NOT a'), 'NOT[_all::a]')

        # quotes
        self.assertEqual(q('"a b"'), '_all::QUOTE[a b]')
        self.assertEqual(q('"a b" c'), 'OR[_all::QUOTE[a b] _all::c]')

        # proximity queries
        self.assertEqual(q('a W/10 b'), '_all::PROX/10[a b]')
        self.assertEqual(q('(a b) W/10 c'), '_all::PROX/10[OR[a b] c]')
        self.assertEqual(q('(x:a b) W/10 c'), 'x::PROX/10[OR[a b] c]')

        # proximity queries must have unique field and can only contain wildcards and disjunctions
        self.assertRaises(QueryParseError, q, 'a W/10 (b OR (c OR d))')
        self.assertRaises(QueryParseError, q, 'x:a W/10 y:b')
        self.assertRaises(QueryParseError, q, 'a W/10 (b AND c)')
        self.assertRaises(QueryParseError, q, 'a W/10 (b W/5 c)')

        # lucene notation
        self.assertEqual(q('"a b"~5'), '_all::PROX/5[a b]')
        self.assertEqual(q('x:"a b"~5'), 'x::PROX/5[a b]')
        self.assertEqual(q('"a (b c)"~5'), '_all::PROX/5[a OR[b c]]')

        # disallow AND in lucene notation
        self.assertRaises(QueryParseError, q, '"a (b AND c)"~5')
        
        # disallow matchall wildcards anywhere but at the beginning
        self.assertRaises(QueryParseError, q, '"a * b"~5')
        self.assertRaises(QueryParseError, q, 'a AND *')
        
        self.assertEqual(q('* NOT a'), 'NOT[_all::* _all::a]')
        self.assertEqual(q('*'), '_all::*')

    def test_dsl(self):
        q = parse

        self.assertEqual(q('a'), {'match': {'_all': 'a'}})
        self.assertEqual(q('a*'), {'wildcard': {'_all': 'a*'}})
        self.assertEqual(q('a!'), {'wildcard': {'_all': 'a*'}})

        self.assertEqual(q('a AND b'), {'bool': {'must': [{'match': {'_all': 'a'}},
                                                          {'match': {'_all': 'b'}},
        ]}})

        self.assertEqual(q('a W/10 b'), {"span_near": {"clauses": [
            {"span_term": {"_all": "a"}},
            {"span_term": {"_all": "b"}},
        ], "slop": "10", "in_order": False}})
        self.assertEqual(q('a* W/10 b'), {"span_near": {"clauses": [
            {"span_multi": {"match": {"prefix": {"_all": {"value": "a"}}}}},
            {"span_term": {"_all": "b"}},
        ], "slop": "10", "in_order": False}})

        expected = {u'bool': {u'should': [
            {u'span_near': {u'in_order': False, u'clauses': [
                {u'span_term': {u'_all': u'a'}},
                {u'span_term': {u'_all': u'b'}}
            ], u'slop': u'10'}},
            {u'span_near': {u'in_order': False, u'clauses': [
                {u'span_term': {u'_all': u'a'}},
                {u'span_term': {u'_all': u'c'}}
            ], u'slop': u'10'}}
        ]}}

        self.assertEqual(q('a W/10 (b c)'), expected)
