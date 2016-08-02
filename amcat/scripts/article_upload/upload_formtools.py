from django import forms


class FileInfo:
    def __init__(self, file_name, file_fields):
        self.file_name = file_name
        self.file_fields = set(file_fields)


class BaseFieldMapFormSet(forms.BaseFormSet):
    existing_fields = frozenset()
    required_fields = frozenset()

    def __init__(self, *args, initial=None, file_info=None, **kwargs):
        self.file_info = file_info
        if not initial:
            initial = self.get_initial(file_info)
        super().__init__(*args, initial=initial, **kwargs)

    def get_initial(self, file_info: FileInfo):
        if file_info is None:
            return None

        required_fieldnames = self.required_fields
        required_fields = [{"field": field, "column": field if field in file_info.file_fields else None}
                           for field in required_fieldnames]

        matching_fields = [{"field": field, "column": field}
                           for field in self.existing_fields if field in file_info.file_fields if
                           field not in required_fieldnames]

        return required_fields + matching_fields

    def get_form_kwargs(self, i):
        kwargs = super().get_form_kwargs(i)
        kwargs['required_field'] = i < len(self.required_fields)
        kwargs['file_info'] = self.file_info

        return kwargs

    def clean(self):
        if any(self.errors):
            return

        errors = []
        required = set(self.required_fields)

        for form in self.forms:
            cleaned_data = form.cleaned_data
            if 'field' not in cleaned_data:
                continue
            required.discard(cleaned_data['field'])

        if required:
            errors.append("Field definitions for field(s) '{}' are required.".format("', '".join(required)))

        if errors:
            raise forms.ValidationError(errors)

    @property
    def cleaned_data(self):
        cleaned_data = super().cleaned_data
        field_dict = {d['field']: {k: v for k, v in d.items() if v and k != 'field'}
                      for d in cleaned_data if 'field' in d}
        return {"field_map": field_dict}

    def non_field_errors(self):
        return self.non_form_errors()


class FieldMapForm(forms.Form):
    field = forms.CharField(max_length=100, help_text="The article field")
    column = forms.CharField(max_length=100, required=False,
                             help_text="The source column or field in the uploaded file")
    value = forms.CharField(max_length=200, required=False,
                            help_text="The literal value to assign to the field")

    def __init__(self, *args, file_info=None, required_field=False, **kwargs):
        self.file_info = file_info
        super().__init__(*args, **kwargs)
        if file_info:
            self.fields['column'] = forms.ChoiceField(
                choices=[(None, "-- use single value --")] + [(field, field) for field in file_info.file_fields],
                required=False)
        if required_field:
            self.fields['field'].widget.attrs['readonly'] = 'readonly'
            self.fields['field'].widget.attrs['class'] = self.fields['field'].widget.attrs.get('class', "") + " warning"

    def clean(self):
        cleaned_data = super().clean()
        if bool(cleaned_data['value']) == bool(cleaned_data['column']):
            raise forms.ValidationError("Fill in one of 'value' or 'column'")
        if self.file_info and cleaned_data['column'] and cleaned_data['column'] not in self.file_info.file_fields:
            raise forms.ValidationError("Field {} does not exist in file {}".format(cleaned_data['column'],
                                                                                    self.file_info.file_name))
        return cleaned_data


def get_form_set(required_fields, existing_fields):
    formset = forms.formset_factory(FieldMapForm, formset=BaseFieldMapFormSet, validate_max=False, extra=2)
    formset.required_fields = required_fields
    formset.existing_fields = existing_fields
    return formset
