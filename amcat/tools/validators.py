from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class DictValidator:
    """
    Validates a dictionary, and all of its items. If the key and/or value validators are not given, only the types of
    the keys and/or values are checked.
    """

    def __init__(self, key_type: type = object, value_type: type = object, key_validator=None, value_validator=None):
        self.key_type = key_type
        self.value_type = value_type
        self.key_validator = key_validator
        self.value_validator = value_validator

    def __call__(self, value):
        if not isinstance(value, dict):
            raise ValidationError("Value {} is not a dict".format(value))
        for k, v in value.items():
            if not isinstance(k, self.key_type) or not isinstance(v, self.value_type):
                raise ValidationError("Key-Value pair {} is not of type {}".format((k, v), (self.key_type,
                                                                                            self.value_type)))
            if self.key_validator:
                self.key_validator(k)
            if self.value_validator:
                self.value_validator(v)

