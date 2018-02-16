from typing import Any, Mapping, Tuple, Sequence, Optional

from django.core.exceptions import ValidationError

from amcat.models import CodingRule, CodingSchemaField, CodingRuleAction, CodedArticle, Coding
from amcat.models.coding import codingruletoolkit


class CodingValidationError(ValidationError):
    def __init__(self, arg0, *args, fields: Sequence[Tuple[Optional[int], int, str]] = None, **kwargs):
        super().__init__(arg0, *args, **kwargs)

        self.fields = None
        if isinstance(arg0, list) and all(isinstance(x, CodingValidationError) for x in arg0):
            self.fields = sum([err.fields for err in arg0 if err.fields is not None], [])

        if fields is not None:
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
    if action.label == 'not null':
        return field in context and context[field] is not None

    if action.label == 'not codable':
        return field not in context or context[field] is None

    return True


def get_rule_fn(codingrule: CodingRule):
    def rule(context, coding):
        condition = evaluate_condition(codingruletoolkit.parse(codingrule), context)
        if not condition:
            return
        success = apply_action(codingrule.action, codingrule.field, context)
        if not success:
            raise CodingValidationError("Validation failed for rule {}: {}".format(codingrule.id, codingrule.label),
                                        fields=[(coding.id, codingrule.field.id, codingrule.label)])

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
                rule(context, coding)
            except CodingValidationError as e:
                errors.append(e)
    if errors:
        raise CodingValidationError(errors)

def apply_schema_requirements(codedarticle: CodedArticle):
    schemas = (codedarticle.codingjob.articleschema, codedarticle.codingjob.unitschema)
    required_fields = set(CodingSchemaField.objects.filter(codingschema__in=schemas, required=True))

    for coding, values in codedarticle.get_codings():
        required_fields -= {v.field for v in values}

    if required_fields:
        raise CodingValidationError(["Missing required field: {}".format(f.label) for f in required_fields],
                                    fields=[(None, field.id, "This field is required") for field in required_fields])


def validate(codedarticle: CodedArticle) -> None:
    """
    Validates a coded article against the rules and schema requirements.
    Raises a CodingValidationError on failure.
    """
    errors = []
    try:
        apply_schema_requirements(codedarticle)
    except CodingValidationError as e:
        errors.append(e)

    try:
        apply_rules(codedarticle)
    except CodingValidationError as e:
        errors.append(e)

    if errors:
        raise CodingValidationError(errors)
