# ##########################################################################
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

"""
Parser to generate a elastic DSL from a lucene-style query string

Decided to roll my own parser since elastic does not support complex phrases
Also paves the way for more customization, i.e. allowing Lexis style queries
"""

from __future__ import unicode_literals, print_function, absolute_import
import itertools
import collections

from django.core.exceptions import ValidationError
from pyparsing import ParserElement, ParseException

from amcat.tools.toolkit import stripAccents


ParserElement.enablePackrat()


def c(s):
    """Clean ('analyze') the provided string"""
    return s.lower()


def query_filter(dsl, cache=False):
    if cache:
        return {"fquery": {"query": dsl, "_cache": True}}
    else:
        return {"query": dsl}


class ParseError(ValueError):
    pass


class FieldTerm(object):
    def __init__(self, field):
        self.field = field

    @property
    def qfield(self):
        return self.field or "_all"

    def __str__(self):
        return unicode(self).encode('utf-8')


class BaseTerm(FieldTerm):
    def __init__(self, text, field):
        super(BaseTerm, self).__init__(field=field)
        self.text = text.replace("!", "*")

    def get_filter_dsl(self):
        return query_filter(self.get_dsl())


class Term(BaseTerm):
    def __unicode__(self):
        return "{self.qfield}::{self.text}".format(**locals())

    def __str__(self):
        return unicode(self).encode('utf-8')

    def get_dsl(self):
        if self.text == "*":
            return {"constant_score": {"filter": {"match_all": {}}}}
        qtype = "wildcard" if ('*' in self.text or '?' in self.text) else "match"
        return {qtype: {self.qfield: self.text.lower()}}

    def get_filter_dsl(self):
        if "?" in self.text:
            return query_filter(self.get_dsl())
        if "*" in self.text:
            if self.text == "*":
                return {"match_all": {}}
            elif "*" in self.text[:-1]:
                return query_filter(self.get_dsl())
            else:  # last must be *
                return {"prefix": {self.qfield: c(self.text[:-1])}}
        else:
            return {"term": {self.qfield: c(self.text)}}


class Quote(BaseTerm):
    def __unicode__(self):
        return u'{self.qfield}::QUOTE[{self.text}]'.format(**locals())

    def __str__(self):
        return unicode(self).encode('utf-8')

    def get_dsl(self):
        return {"match_phrase": {self.qfield: self.text}}


class Boolean(object):
    def __init__(self, operator, terms, implicit=False):
        self.operator = operator
        self.terms = terms
        self.implicit = implicit

    def __unicode__(self):
        terms = " ".join(unicode(t) for t in self.terms)
        return '{self.operator}[{terms}]'.format(**locals())

    def __str__(self):
        return unicode(self).encode('utf-8')

    def _get_not_dsl(self, func="get_dsl"):
        if len(self.terms) == 1:
            # This is an unary operation, meaning it was used at the start of
            # a term. For example: NOT (foo OR bar).
            return {"bool": {"must_not": getattr(self.terms[0], func)()}}

        return {
            # In lucene, NOT is binary rather than unary, so x NOT y
            # means x AND (NOT y) or +x -y. We interpret x NOT y NOT z
            # as x AND (NOT y) AND (NOT z) or +x -y -z
            "bool": {
                "must": [getattr(self.terms[0], func)()],
                "must_not": [getattr(t, func)() for t in self.terms[1:]]
            }
        }

    def get_dsl(self):
        if self.operator == "NOT":
            return self._get_not_dsl("get_dsl")
        else:
            op = dict(OR="should", AND="must", NOT="must_not")[self.operator]
            return {"bool": {op: [term.get_dsl() for term in self.terms]}}

    def get_filter_dsl(self):
        if self.operator == "OR":
            simple_terms = collections.defaultdict(list)  # field : termlist
            clauses = []  # OR clauses
            for t in self.terms:
                if isinstance(t, Term) and "*" not in t.text and "?" not in t.text:
                    simple_terms[t.qfield].append(c(t.text))
                else:
                    clauses.append(t.get_filter_dsl())
            for field, terms in simple_terms.iteritems():
                clauses.append({"terms": {field: terms}})

            return {"bool": {"should": clauses}}

        if self.operator == "NOT":
            return self._get_not_dsl("get_filter_dsl")
        else:
            op = dict(OR="should", AND="must", NOT="must_not")[self.operator]
            return {"bool": {op: [term.get_filter_dsl() for term in self.terms]}}


def _check_span(terms, field=None, allow_boolean=True):
    """
    Checks whether a span contains terms using the same field and
    consists of a single implcit list of terms or simple disjunctions
    @param field: if given and 'True', all terms must use this field
    @return: the shared field
    """
    f = field
    for term in terms:
        if isinstance(term, Term):
            fld = term.field
            term.field = None
        elif allow_boolean and isinstance(term, Boolean) and term.operator == "OR":
            fld = _check_span(term.terms, allow_boolean=False)
        else:
            raise ParseError(
                "Proximity queries cannot contain: {term!r} (allow_boolean={allow_boolean})".format(**locals()))

        if fld:
            if not f:
                f = fld
            elif f != fld:
                raise ParseError("Proximity queries should refer to a unique field, found {f!r} and {fld!r}"
                                 .format(**locals()))
    return f


class Span(Boolean, FieldTerm):
    def __init__(self, terms, slop, field=None, in_order=False):
        Boolean.__init__(self, "SPAN", terms)
        FieldTerm.__init__(self, _check_span(terms, field))
        self.slop = slop
        self.in_order = in_order

    def __unicode__(self):
        terms = " ".join(unicode(t) for t in self.terms)
        terms = terms.replace("_all::", "")
        return u'{self.qfield}::PROX/{self.slop}[{terms}]'.format(**locals())

    def __str__(self):
        return unicode(self).encode('utf-8')

    def get_dsl(self):
        # we cannot directly use disjunctions in a span query, but we can put the disjunction outside the span
        # e.g. (a OR b) w/10 c is the same as (a w/10 c) OR (b w/10 c)
        # So, the get_clause returns a list of clauses, and we take the product of those lists as a disjunction

        def get_clause(term, field):
            if isinstance(term, Term):
                if term.text.endswith("*"):
                    text = term.text[:-1]
                    return [{"span_multi": {"match": {"prefix": {field: {"value": text}}}}}]
                elif "?" in term.text:
                    text = term.text.replace("?", ".")
                    return [{"span_multi": {"match": {"regexp": {field: text}}}}]
                else:
                    return [{"span_term": {field: term.text.lower()}}]
            else:
                # term is a disjunction: return a list of clauses
                # index [0] because get_clause returns a list again, which we don't want here
                return [get_clause(t, field)[0] for t in term.terms]

        clauses = [get_clause(t, self.qfield) for t in self.terms]
        clauses = list(itertools.product(*clauses))
        if len(clauses) > 20:
            raise ParseError("Query too complex: please reduce the number of disjunctions in span queries (max: 20, your query: {}".format(len(clauses)))
        clauses = [{"span_near": {"slop": self.slop, "in_order": self.in_order, "clauses": list(c)}}
                   for c in clauses]
        if len(clauses) == 1:
            return clauses[0]
        else:
            return {"bool": {"should": clauses}}

    def get_filter_dsl(self):
        return query_filter(self.get_dsl())


def lucene_span(quote, field, slop):
    """Create a span query from a lucene style string, i.e. "terms"~10"""
    clause = parse_to_terms(quote, simplify_terms=False)
    if not (isinstance(clause, Boolean) and clause.operator == "OR" and clause.implicit):
        raise ParseError("Lucene-style proximity queries must contain a list of terms, not {clause!r}"
                         .format(**locals()))
    return Span(clause.terms, slop, field)


def get_term(tokens):
    if 'slop' in tokens:
        return lucene_span(tokens.quote, tokens.field, tokens.slop)
    elif 'quote' in tokens:
        # this is where it gets weird: phrase queries don't support general
        # prefixes, but span (=slop) queries do. So, make a span query
        # with slop=0 and in_order=True if a non-final wildcard is present
        if "*" in tokens.quote or "?" in tokens.quote:
            return lucene_span(tokens.quote, tokens.field, 0)
        else:
            return Quote(tokens.quote, tokens.field)
    else:
        t = Term(tokens.term, tokens.field)
        return t


def get_boolean_or_term(tokens):
    token = tokens[0]
    if isinstance(token, (Boolean, BaseTerm)):
        return token
    else:
        op = token['operator']
        terms = [t for t in token if isinstance(t, (Boolean, BaseTerm))]
        if op == 'W/':
            # create span query
            return Span(terms, token['slop'])
        else:
            implicit = op.startswith("implicit_")
            if implicit: op = op.replace("implicit_", "")
            return Boolean(op, terms, implicit)


def pprint(q, indent=0):
    i = "  " * indent
    if isinstance(q, Boolean):
        print(i, "Boolean", q.operator, "[")
        for t in q.terms:
            pprint(t, indent + 1)
        print(i, "]")
    else:
        print(i, type(q).__name__, q)


_grammar = None


def get_grammar():
    global _grammar
    if _grammar is None:
        from pyparsing import (Literal, Word, QuotedString, Optional, operatorPrecedence,
                               nums, alphas, opAssoc)

        # literals
        AND = Literal("AND")
        OR = Literal("OR")
        NOT = Literal("NOT").setResultsName("operator")
        SPAN = (Literal("W/") + Word(nums).setResultsName("slop"))
        OP = Optional(AND | OR | NOT | SPAN, default="implicit_OR").setResultsName("operator")

        COLON = Literal(":").suppress()
        TILDE = Literal("~").suppress()
        LETTERS = u''.join(unichr(c) for c in xrange(65536)
                           if not unichr(c).isspace() and unichr(c) not in '":()~')

        # terms
        term = Word(LETTERS)
        slop = Word(nums).setResultsName("slop")
        quote = QuotedString('"').setResultsName("quote") + Optional(TILDE + slop)
        #quote.setParseAction(Quote)

        field = Word(alphas).setResultsName("field")
        fterm = Optional(field + COLON) + (quote | term).setResultsName("term")
        fterm.setParseAction(get_term)

        # boolean combination
        boolean_expr = operatorPrecedence(fterm, [
            (NOT, 1, opAssoc.RIGHT),
            (OP, 2, opAssoc.LEFT)
        ])
        boolean_expr.setParseAction(get_boolean_or_term)
        _grammar = boolean_expr
    return _grammar


def simplify(term):
    if isinstance(term, Boolean):
        new_terms = []
        for t in term.terms:
            t = simplify(t)
            if isinstance(t, Boolean) and term.operator in ("OR", "AND") and t.operator == term.operator:
                new_terms += t.terms
            else:
                new_terms.append(t)
        term.terms = new_terms
    return term

# validationerror changes the message into a list (probably per field?), so raise a valueerror here
class QueryParseError(ValueError):
    pass

def parse_to_terms(s, simplify_terms=True, strip_accents=True, context=""):
    if strip_accents:
        s = stripAccents(s)
    if " *" in s.strip():
        raise QueryParseError("Error in query '{context}': Can only use wildcard (*) as suffix or at beginning of query".format(**locals()))
    try:
        terms = get_grammar().parseString(s, parseAll=True)[0]
    except ParseException as e:
        msg = "Error in query '{context}': {e}\n{s}".format(**locals())
        if hasattr(e, "loc"):
            msg += "\n{space}^".format(space=" "*e.loc)
        raise QueryParseError(msg) 
    except Exception as e:
        raise QueryParseError("Error parsing query '{context}': {e.__class__.__name__}: {e}\n{s}".format(**locals()))

    if simplify_terms:
        terms = simplify(terms)
    return terms


def parse(s):
    terms = parse_to_terms(s)
    dsl = terms.get_dsl()
    return dsl

