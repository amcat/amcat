from typing import Any, Mapping, Tuple, Sequence

from django.core.exceptions import ValidationError

from amcat.models import CodingRule, CodingSchemaField, CodingRuleAction, CodedArticle
from amcat.models.coding import codingruletoolkit


class CodingValidationError(ValidationError):
    def __init__(self, arg0, *args, fields: Sequence[Tuple[int, int]] = None, **kwargs):
        super.__init__(arg0, *args, **kwargs)
        if isinstance(arg0, list) and all(isinstance(x, CodingValidationError) for x in arg0):
            self.fields = sum([err.fields for err in arg0], [])
        self.fields = fields


comparators = {
    codingruletoolkit.EQUALS: lambda x, y: x == y,
    codingruletoolkit.GREATER_THAN: lambda x, y: x > y,
    codingruletoolkit.GREATER_THAN_OR_EQUAL_TO: lambda x, y: x >= y,
    codingruletoolkit.LESSER_THAN: lambda x, y: x < y,
    codingruletoolkit.LESSER_THAN_OR_EQUAL_TO: lambda x, y: x <= y
}


def resolve_value(val, codingContext: Mapping[CodingSchemaField, Any]):
    if isinstance(val, CodingSchemaField):
        return codingContext[val]
    if type(val) in (int, str):
        return val


def evaluate_condition(condition: dict, codingContext: Mapping[CodingSchemaField, Any]) -> bool:
    """
    Evaluate a rule condition, given a mapping of field-value pairs.
    """

    if isinstance(condition, CodingSchemaField):
        return bool(codingContext[condition])

    if condition['type'] == codingruletoolkit.NOT:
        return not evaluate_condition(condition['value'], codingContext)

    if condition['type'] == codingruletoolkit.AND:
        return all(evaluate_condition(v, codingContext) for v in condition['values'])

    if condition['type'] == codingruletoolkit.OR:
        return any(evaluate_condition(v, codingContext) for v in condition['values'])

    if condition['type'] in comparators:
        values = (resolve_value(v, codingContext) for v in condition['values'])
        try:
            return comparators[condition['type']](*values)
        except ValueError:
            # Catch any incomparable types.
            return False


def apply_action(action: CodingRuleAction, field: CodingSchemaField, context) -> bool:
    if action.id == 3:
        return field in context and context[field] is not None

    return True


def get_rule_fn(codingrule: CodingRule):
    def rule(context):
        condition = evaluate_condition(codingruletoolkit.parse(codingrule), context)
        if not condition:
            return
        success = apply_action(codingrule.action, codingrule.field, context)
        if not success:
            raise CodingValidationError("Validation failed for rule {}: {}".format(codingrule.id, codingrule.label))

    return rule


def apply_rules(codedarticle: CodedArticle):
    rules = {}
    errors = []
    for coding, values in codedarticle.get_codings():
        if not coding.schema:
            continue
        context = {v.field: v.intval if v.strval is None else v.strval for v in values}
        if coding.schema not in rules:
            rules[coding.schema] = [get_rule_fn(rule) for rule in coding.schema.rules.all()]
        for rule in rules[coding.schema]:
            try:
                rule(context)
            except CodingValidationError:



def apply_schema_requirements(codedarticle: CodedArticle):
    schemas = (codedarticle.codingjob.articleschema, codedarticle.codingjob.unitschema)
    required_fields = set(CodingSchemaField.objects.filter(codingschema__in=schemas, required=True))

    for coding, values in codedarticle.get_codings():
        required_fields -= {v.field for v in values}

    if required_fields:
        raise CodingValidationError(["Missing required field: {}".format(f.label) for f in required_fields])


def validate(codedarticle: CodedArticle) -> None:
    """
    Validates a coded article against the rules and schema requirements.
    Raises a CodingValidationError on failure.
    """
    apply_schema_requirements(codedarticle)
    apply_rules(codedarticle)
