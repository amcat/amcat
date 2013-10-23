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

"""
Parser to generate a elastic DSL from a lucene-style query string

Decided to roll my own parser since elastic does not support complex phrases
Also paves the way for more customization, i.e. allowing Lexis style queries
"""

from __future__ import unicode_literals, print_function, absolute_import
from pyparsing import *

class BaseTerm(object):
    def __init__(self, text, field):
        self.text = text
        self.field = field
    @property
    def qfield(self):
        return self.field or "_all"
    def __str__(self):
        return unicode(self).encode('utf-8')

class Term(BaseTerm):
    def __unicode__(self):
        return "{self.qfield}::{self.text}".format(**locals())
    def __str__(self):
        return unicode(self).encode('utf-8')
    def get_dsl(self):
        qtype = "wildcard" if '*' in self.text else "term"
        return {qtype : {self.qfield : self.text}}

class Quote(BaseTerm):
    def __unicode__(self):
        return u'{self.qfield}::"{self.text}"'.format(**locals())
    def __str__(self):
        return unicode(self).encode('utf-8')
    def get_dsl(self):
        if self.text.endswith("*"):
            return {"match_phrase_prefix" : {self.qfield : self.text[:-1]}}
        else:
            return {"match_phrase" : {self.qfield : self.text}}

class Span(BaseTerm):
    def __init__(self, text, field, slop, in_order=False):
        super(Span, self).__init__(text, field)
        self.slop = slop
        self.in_order=in_order
    def __unicode__(self):
        return u'{self.qfield}::"{self.text}"~{self.slop}'.format(**locals())
    def __str__(self):
        return unicode(self).encode('utf-8')

    def get_dsl(self):
        qfield = self.field if self.field else '_all'
        # we should parse this a second time for internal structure...
        
        clauses = [get_span_term(c, self.qfield) for c in self.text.split()]
        return {"span_near" : {"slop": self.slop, "in_order" : self.in_order,
                               "clauses" : clauses}}

def get_span_term(text, field):
    if text.endswith("*"):
        text = text[:-1]
        return {"span_multi":{"match":{"prefix" : { field :  { "value" : text } }}}}
    else:
        return {"span_term" : {field : text}}
    
class Boolean(object):
    def __init__(self, tokens):
        self.operator = tokens.operator
        self.terms = [parse_nested(t) for t in tokens if t != self.operator]
        
    def __unicode__(self):
        terms = " ".join(unicode(t) for t in self.terms)
        return '{self.operator}[{terms}]'.format(**locals())
    def __str__(self):
        return unicode(self).encode('utf-8')
    def get_dsl(self):
        op = dict(OR="should", AND="must")[self.operator]
        return {"bool" : {op : [term.get_dsl() for term in self.terms]}}
    
def parse_nested(token):
    if isinstance(token, ParseResults):
        token = Boolean(token)
    return token

def get_term(tokens):
    if 'slop' in tokens:
        return Span(tokens.quote, tokens.field, tokens.slop)
    elif 'quote' in tokens:
        # this is where it gets weird: phrase queries don't support general
        # prefixes, but span (=slop) queries do. So, make a span query
        # with slop=0 and in_order=True if a non-final wildcard is present
        if "*" in tokens.quote[:-1]:
            return Span(tokens.quote, tokens.field, 0, in_order=True)
        else:
            return Quote(tokens.quote, tokens.field)
    else:
        t = Term(tokens.term, tokens.field)
        return t

def get_boolean_or_term(tokens):
    token = tokens[0]
    if isinstance(token, BaseTerm):
        return token
    else:
        return Boolean(token)
    

def pprint(q, indent=0):
    i = "  "*indent
    if isinstance(q, Boolean):
        print (i, "Boolean", q.operator, "[")
        for t in q.terms:
            pprint(t, indent+1)
        print (i, "]")
    else:
        print (i, type(q).__name__, q)

        
class Grammar:
    # literals
    AND = Literal("AND").setResultsName("operator")
    OR = Literal("OR").setResultsName("operator")
    NOT = Literal("NOT").setResultsName("operator")
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
            (AND, 2, opAssoc.LEFT),
            (Optional(OR, default="OR"),  2, opAssoc.LEFT),
            ])
    boolean_expr.setParseAction(get_boolean_or_term)

    
parser = Grammar.boolean_expr

def parse(s):
    return parser.parseString(s, parseAll=True)[0].get_dsl()

