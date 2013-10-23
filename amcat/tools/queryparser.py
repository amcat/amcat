from pyparsing import *

class Term(object):
    def __init__(self, tokens):
        self.term = tokens['term']
        self.field = tokens.get('field', None)
    def __unicode__(self):
        field = "{self.field}:".format(**locals()) if self.field else ""
        return "{field}{self.term}".format(**locals())
    def __str__(self):
        return unicode(self).encode('utf-8')
    

class Quote(object):
    def __init__(self, tokens):
        self.quote = tokens['quote']
        self.slop = tokens.get('slop', 0)

        pass
    def __unicode__(self):
        result = u'"{self.quote}"'.format(**locals())
        if self.slop:
            result += u'~{self.slop}'.format(**locals())
        return result
    def __str__(self):
        return unicode(self).encode('utf-8')

class Boolean(object):
    def __init__(self, tokens):
        self.operator = tokens[0].operator
        self.terms = [t for t in tokens[0] if isinstance(t, (Term, Boolean))]
    def __unicode__(self):
        terms = " ".join(unicode(t) for t in self.terms)
        return '{self.operator}[{terms}]'.format(**locals())
    def __str__(self):
        return unicode(self).encode('utf-8')
    

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
    quote.setParseAction(Quote)

    field = Word(alphas).setResultsName("field")
    fterm = Optional(field + COLON) + (quote | term).setResultsName("term")
    fterm.setParseAction(Term)

    # boolean combination
    boolean_expr = operatorPrecedence(fterm, [
            (AND, 2, opAssoc.LEFT),
            (Optional(OR, default="OR"),  2, opAssoc.LEFT),
            ])
    boolean_expr.setParseAction(Boolean)

    
parser = Grammar.boolean_expr

def parse(s):
    return parser.parseString(s, parseAll=True)
