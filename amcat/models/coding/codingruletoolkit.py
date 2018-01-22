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


import ast
import json

from amcat.models import CodingSchemaField, Code, CodingRule
from amcat.models.coding.serialiser import IntSerialiser, QualitySerialiser, IntervalSerialiser
from django.core.exceptions import ValidationError

KNOWN_NODES = (
    ast.BoolOp, ast.UnaryOp, ast.And, ast.Or, ast.Not,
    ast.Eq, ast.NotEq, ast.Expr, ast.Compare, ast.Str,
    ast.Load, ast.Num, ast.Tuple, ast.Lt, ast.LtE,
    ast.Gt, ast.GtE, ast.NameConstant
)

OR = "OR"
AND = "AND"
NOT = "NOT"
EQUALS = "EQ"
NOT_EQUALS = "NEQ"
GREATER_THAN = "GT"
LESSER_THAN = "LT"
GREATER_THAN_OR_EQUAL_TO = "GTE"
LESSER_THAN_OR_EQUAL_TO = "LTE"

AST_MAP = {
    ast.Eq: EQUALS, ast.NotEq: NOT_EQUALS,
    ast.Lt: LESSER_THAN, ast.Gt: GREATER_THAN,
    ast.LtE: LESSER_THAN_OR_EQUAL_TO,
    ast.GtE: GREATER_THAN_OR_EQUAL_TO

}

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
    operator = node.ops[0]

    if not isinstance(left, ast.Num):
        raise SyntaxError("Left operand of {} must always be a Num/CodingSchemaField (col {}, line {})"
                          .format(node, node.col_offset, node.lineno))

    # Check right operand. Must be a Num/Str
    value = None
    if isinstance(right, ast.Num):
        value = right.n
    elif isinstance(right, ast.Str):
        value = right.s
    elif isinstance(right, ast.NameConstant):
        value = right.value
    print(value)
    # Check if type of right operand seems to match the type requested by its serialiser
    schemafield = CodingSchemaField.objects.get(id=left.n)
    serialiser = schemafield.serialiser

    if (not isinstance(serialiser, (IntervalSerialiser, IntSerialiser, QualitySerialiser))
        and isinstance(operator, (ast.Lt, ast.LtE, ast.Gt, ast.GtE))):
        raise SyntaxError("Cannot use greater/lesser than when comparing with {}".format(serialiser))

    if not isinstance(value, serialiser.serialised_type):
        raise SyntaxError("Right operand of {} must be of {} to deserialise to {} (col {}, line {}))"
                          .format(schemafield, serialiser.serialised_type, serialiser.deserialised_type,
                                  node.col_offset, node.lineno))

    return schemafield, serialiser.deserialise(value)


def parse_node(node, _seen=()):
    if isinstance(node, ast.BoolOp):
        # and .. or
        return {
            "type": OR if isinstance(node.op, ast.Or) else AND,
            "values": tuple(parse_node(n, _seen) for n in node.values),
        }
    if isinstance(node, ast.Compare):
        return {
            "type": AST_MAP[node.ops[0].__class__],
            "values": resolve_operands(node)
        }
    if isinstance(node, ast.Num):
        return CodingSchemaField.objects.get(pk=node.n)
    if isinstance(node, ast.NameConstant):
        if not isinstance(node.value, bool):
            raise SyntaxError("Constant {} is not a bool (col {}, line {})".format(node.value, node.col_offset, node.lineno))
        return node.value
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


def schemarules_valid(schema):
    """Checks whether all codingrules of `codingschema` are valid"""
    try:
        return all(is_valid(schema, parse(rule)) for rule in schema.rules.all())
    except (SyntaxError, Code.DoesNotExist, CodingRule.DoesNotExist, CodingSchemaField.DoesNotExist):
        return False


def _to_json(node):
    if isinstance(node, dict):
        # Shallow copy
        node = dict(node)

        if "value" in node:
            node["value"] = _to_json(node["value"])
        else:
            node["values"] = map(_to_json, node["values"])

        return node
    elif isinstance(node, Code):
        return dict(type="code", id=node.id)
    elif isinstance(node, CodingSchemaField):
        return dict(type="codingschemafield", id=node.id)

    return node


def to_json(node, serialise=True):
    """
    Serialise tree, representing ORM objects as dicts.
    
    @type node: dict
    @param node: node to serialise
    @type serialise: boolean
    @param serialise: if False, return dict which can later be serialised
                        with json.dumps().
    """
    if serialise:
        return json.dumps(_to_json(node))
    return _to_json(node)
