
from django import forms


class FileInfo:
    def __init__(self, file_name, file_fields):
        self.file_name = file_name
        self.file_fields = set(file_fields)

class BaseFieldMapFormSet(forms.BaseFormSet):
    def __init__(self, articlesets=None, file_info=None, *args, **kwargs):
        self.articlesets = None
        initial = kwargs.pop('initial')
        if not initial:
            initial = self.get_initial(file_info)
        super().__init__(*args, initial=initial, **kwargs)
        self.file_info = file_info

    def get_initial(self, file_info: FileInfo):
        if file_info is None:
            return None
        return [{"field": field, "column": field}
                for field in self.get_fields() if field in file_info.file_fields]

    def _construct_form(self, i, **kwargs):
        return super()._construct_form(i, file_info=self.file_info, **kwargs)


    def clean(self):
        if any(self.errors):
            return

        errors = []
        existing = set(self.get_fields())
        required = set(self.get_required_fields())
        non_existent = [] #todo: allow dynamic fields

        for form in self.forms:
            cleaned_data = form.cleaned_data
            if 'field' not in cleaned_data:
                continue
            required.discard(cleaned_data['field'])
            if cleaned_data['field'] not in existing:
                non_existent.append(cleaned_data['field'])
                errors.append("Dynamic fields not supported yet. Fill in an existing field.") 

        if non_existent:
            errors.append("The following fields do not exist: '{}'.".format("', '".join(non_existent)))
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

    def get_required_fields(self):
        #TODO: get required fields
        return {"text", "date"}

    def get_fields(self):
        articlesets = self.articlesets
        #TODO: get fields
        return ("text", "date", "medium", "pagenr", "section", "headline", "byline", "url", "externalid",
          "author", "addressee", "parent_url", "parent_externalid")

    def non_field_errors(self):
        return self.non_form_errors()


class FieldMapForm(forms.Form):
    field = forms.CharField(max_length=100, help_text="The article field")
    column = forms.CharField(max_length=100, required=False,
                             help_text="The source column or field in the uploaded file")
    value = forms.CharField(max_length=200, required=False,
                            help_text="The literal value to assign to the field")

    def __init__(self, *args, file_info=None, **kwargs):
        self.file_info = file_info
        super().__init__(*args, **kwargs)
        if file_info:
            self.fields['column'] = forms.ChoiceField(choices=[(None, "-- use single value --")] + [(field, field) for field in file_info.file_fields], required=False)


    def clean(self):
        cleaned_data = super().clean()
        if bool(cleaned_data['value']) == bool(cleaned_data['column']):
            raise forms.ValidationError("Fill in one of 'value' or 'column'")
        if self.file_info and cleaned_data['column'] and cleaned_data['column'] not in self.file_info.file_fields:
            raise forms.ValidationError("Field {} does not exist in file {}".format(cleaned_data['column'],
                                                                                    self.file_info.file_name))
        return cleaned_data


FieldMapFormSet = forms.formset_factory(FieldMapForm, formset=BaseFieldMapFormSet, validate_max=False, extra=2)


