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

from __future__ import unicode_literals

import ast
import json
import itertools

from amcat.models import CodingSchemaField, Code, CodingRule
from django.core.exceptions import ValidationError

KNOWN_NODES = (
    ast.BoolOp, ast.UnaryOp, ast.And, ast.Or, ast.Not,
    ast.Eq, ast.NotEq, ast.Expr, ast.Compare, ast.Str,
    ast.Load, ast.Num, ast.Tuple
)

OR = "OR"
AND = "AND"
NOT = "NOT"
EQUALS = "EQ"
NOT_EQUALS = "NEQ"

__all__ = (
    "OR", "AND", "NOT", "EQUALS", "NOT_EQUALS", "parse",
    "walk", "is_valid", "clean_tree"
)


def walk(node):
    """Yields all descendants of `node` plus itself.
    
    @type node: dict
    @param node: node returned by `parse`"""
    yield node

    if isinstance(node, dict):
        w = walk(node["value"]) if "value" in node else node["values"]
        for node in w: yield node

def resolve_operands(node):
    """Resolve types of operands of one of EQUALS / NOT_EQUALS"""
    left, right = node.left, node.comparators[0]

    if not isinstance(left, ast.Num):
        raise SyntaxError("Left operand of {} must always be a Num/CodingSchemaField (col {}, line {})"
                            .format(node, node.col_offset, node.lineno))

    # Check right operand. Must be a Num/Str
    value = None
    if isinstance(right, ast.Num):
        value = right.n
    elif isinstance(right, ast.Str):
        value = right.s

    # Check if type of right operand seems to match the type requested by its serialiser
    schemafield = CodingSchemaField.objects.get(id=left.n)
    serialiser = schemafield.serialiser

    if not isinstance(value, serialiser.serialised_type):
        raise SyntaxError("Right operand of {} must be of {} to deserialise to {} (col {}, line {}))"
                .format(schemafield, serialiser.serialised_type, serialiser.deserialised_type,
                            node.col_offset, node.lineno))

    return schemafield, serialiser.deserialise(value)


def parse_node(node, _seen=()):
    if isinstance(node, ast.BoolOp):
        # and .. or
        return {
            "type" : OR if isinstance(node.op, ast.Or) else AND,
            "values" : tuple(parse_node(n, _seen) for n in node.values),
        }
    if isinstance(node, ast.Compare):
        return {
            "type" : EQUALS if isinstance(node.ops[0], ast.Eq) else NOT_EQUALS,
            "values" : resolve_operands(node)
        }
    if isinstance(node, ast.Num):
        return parse(CodingRule.objects.get(id=node.n), _seen)
    if isinstance(node, ast.Str):
        raise SyntaxError("invalid syntax (col {}, line {})".format(node.col_offset, node.lineno))
    if isinstance(node, ast.Expr):
        return parse_node(node.value, _seen)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return dict(type=NOT, value=parse_node(node.operand, _seen))
    if isinstance(node, ast.Tuple):
        # We can ignore an empty tuple
        if not node.elts: return None

    raise SyntaxError("Unknown node (col {}, line {})".format(node.col_offset, node.lineno))

def parse(codingrule, _seen=()):
    """
    Parse a condition of a codingrule. Returns a dictionary with the first node of the
    AST generated from `codingrule.condition`.

    Each node represented as a dict contains a key "type", which indicates which type
    of node it is. This must be one of OR, AND, NOT, EQUALS and NOT_EQUALS. All nodes
    (excluding NOT) contain a key 'values' which is a list of operands. Not only has one
    operand, which is held in 'value'.

    Each node NOT represented as a dict must be a CodingSchemaField, Code, str or int. A
    CodingSchemaField is always on the left side of an equation and compared to either a
    Code, str or int. 

    All CodingRule's will be replaced be their condition and parsed.

    @raises: SyntaxError, CodingSchemaField.DoesNotExist, Code.DoesNotExist
    @returns: root of tree, or None if condition is empty
    """
    tree = ast.parse("({})".format(codingrule.condition)).body[0]

    # This function can be called from parse_node if the condition refers to another
    # codingrule. Keeping _seen prevents infinite loops when parsing.
    if codingrule in _seen:
        raise SyntaxError("Recursion: condition can't contain itself.")

    # Not all nodes from the Python language are supported
    for node in ast.walk(tree):
        if node.__class__ not in KNOWN_NODES or (isinstance(node, ast.Compare) and len(node.ops) > 1):
            if hasattr(node, "col_offset"):
                raise SyntaxError("invalid syntax (col {}, line {})".format(node.col_offset, node.lineno))
            raise SyntaxError("invalid syntax")

    return parse_node(tree, _seen=_seen + (codingrule,))

def clean_tree(codingschema, tree):
    """
    Checks if this tree is valid by checking if given values are valid for
    this schemafield.
    """
    fields = set(codingschema.fields.all())
    nodes = [n for n in walk(tree) if (isinstance(n, dict) and n["type"] in (EQUALS, NOT_EQUALS))]

    for node in nodes:
        schemafield, value = node["values"]

        if not schemafield in fields:
            raise ValidationError("Schemafield {} not in possible values".format(schemafield))

        possible_values = schemafield.serialiser.possible_values
        if possible_values is not None and value not in possible_values:
            raise ValidationError("Value {} not in possible values".format(value))

def is_valid(codingschema, tree):
    """True if tree is valid, else False."""
    try:
        clean_tree(codingschema, tree)
    except ValidationError:
        return False
    return True

def _to_json(node):
    if isinstance(node, dict):
        if "value" in node:
            node["value"] = _to_json(node["value"])
        else:
            node["values"] = map(_to_json, node["values"])
    elif isinstance(node, Code):
        return dict(type="code", id=node.id)
    elif isinstance(node, CodingSchemaField):
        return dict(type="codingschemafield", id=node.id)

    return node

def to_json(node):
    """Serialise tree, representing ORM objects as dicts."""
    return json.dumps(_to_json(node))

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodingRuleToolkit(amcattest.PolicyTestCase):
    PYLINT_IGNORE_EXTRA = 'W0212', #  'protected' member access

    def condition(self, s, c):
        return CodingRule(codingschema=s, condition=c)

    def test_to_json(self):
        import functools

        o1, o2 = amcattest.create_test_code(), amcattest.create_test_code()
        schema_with_fields = amcattest.create_test_schema_with_fields()
        code_field = schema_with_fields[4]
        c = functools.partial(self.condition, schema_with_fields[0])

        tree = to_json(parse(c("{}=={}".format(code_field.id, o1.id))))
        self.assertEquals(json.loads(tree), {"type":EQUALS, "values":[
            {"type":"codingschemafield", "id" : code_field.id},
            {"type":"code", "id" : o1.id}
        ]})


    def test_clean_tree(self):
        import functools

        o1, o2 = amcattest.create_test_code(), amcattest.create_test_code()
        codebook, codebook_codes = amcattest.create_test_codebook_with_codes()
        schema_with_fields = amcattest.create_test_schema_with_fields(codebook=codebook)

        schema = schema_with_fields[0]
        code_field = schema_with_fields[4]

        c = functools.partial(self.condition, schema)

        tree = parse(c("{code_field.id}=={o1.id}".format(**locals())))
        self.assertRaises(ValidationError, clean_tree, schema, tree)
        tree = parse(c("{code_field.id}=={code.id}".format(code_field=code_field, code=codebook.codes[0])))
        self.assertEquals(clean_tree(schema, tree), None)
        self.assertRaises(ValidationError, clean_tree, amcattest.create_test_schema_with_fields()[0], tree)

    def test_parse(self):
        import functools

        o1, o2 = amcattest.create_test_code(), amcattest.create_test_code()
        schema_with_fields = amcattest.create_test_schema_with_fields()

        schema = schema_with_fields[0]
        codebook = schema_with_fields[1]

        text_field = schema_with_fields[2]
        number_field = schema_with_fields[3]
        code_field = schema_with_fields[4]

        c = functools.partial(self.condition, schema)
        
        # Empty conditions should return None
        self.assertEquals(parse(c("")), None)
        self.assertEquals(parse(c("()")), None)
        
        # Recursion should be checked for
        cr = CodingRule.objects.create(codingschema=schema, label="foo", condition="()")
        cr.condition = str(cr.id)
        self.assertRaises(SyntaxError, parse, cr)

        # Nonexisting fields should raise an error
        cr.condition = "0==2"
        self.assertRaises(CodingSchemaField.DoesNotExist, parse, cr)
        cr.condition = "{}==0".format(code_field.id)
        self.assertRaises(Code.DoesNotExist, parse, cr)
        cr.condition = "0"
        self.assertRaises(CodingRule.DoesNotExist, parse, cr)
        cr.condition = "{}=={}".format(code_field.id, o1.id)
        self.assertTrue(parse(cr) is not None)

        # Wrong inputs for fields should raise an error
        for inp in ("'a'", "0.2", "u'a'"):
            cr.condition = "{}=={}".format(number_field.id, inp)
            self.assertRaises(SyntaxError, parse, cr)

        for inp in ("'a'", "0.2", "u'a'", repr(str(o1.id))):
            cr.condition = "{}=={}".format(code_field.id, inp)
            self.assertRaises(SyntaxError, parse, cr)

        for inp in ("'a'", "0.2", "2"):
            cr.condition = "{}=={}".format(text_field.id, inp)
            self.assertRaises(SyntaxError, parse, cr)
        
        # "Good" inputs shoudl not yield an error
        for field, inp in ((number_field, 1), (text_field, "u'a'"), (code_field, o1.id)):
            cr.condition = "{}=={}".format(field.id, inp)
            self.assertTrue(parse(cr) is not None)

        # Should accept Python-syntax (comments, etc)
        cr.condition = """{}==(
        # This should be a comment)
        {})""".format(text_field.id, "u'a'")
        self.assertTrue(parse(cr) is not None)

        ## Testing output
        tree = parse(c("not {}".format(cr.id)))
        self.assertEquals(tree["type"], NOT)
        self.assertTrue(not isinstance(tree["value"], CodingRule))

        tree = parse(c("{}=={}".format(text_field.id, "u'a'")))
        self.assertEquals(tree, {"type":EQUALS, "values":(text_field, u'a')})

        cr.save()
        tree = parse(c("{cr.id} or {cr.id}".format(cr=cr)))
        self.assertEquals(tree, {"type":OR, "values":(parse(cr), parse(cr))})
        

