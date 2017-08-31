from copy import deepcopy

from django import template
from django import forms
from django.shortcuts import render
from django.template.loader import render_to_string

register = template.Library()

# todo: django 1.11 should make this a lot easier with the introduction of widget templates.

def _form_control_default(field):
    field.field.widget.attrs.setdefault("class", 'form-control')
    field.field.widget.attrs.setdefault("placeholder", field.label)
    classes = field.field.widget.attrs['class'].split(" ")
    if 'form-control' not in classes:
        field.field.widget.attrs['class'] += " form-control"

def bootstrapFileInput(widget):
    def _render(name, value, attrs=None):
        template = ('<label for="{id}" class="btn btn-default control-label">{input} Browse...</label> '
                    '<span id="{id}_files" class="control-label"></span>'
                    )
        onchange = 'document.getElementById("{id}_files").innerText = Array.from(this.files).map(x => x.name)'
        if not attrs:
            attrs = {"class": "hidden"}
        elif not attrs.get("class"):
            attrs["class"] = "hidden"
        elif "hidden" not in attrs["class"].split(" "):
            attrs["class"] += " hidden"
        attrs["onchange"] = onchange.format(id=attrs['id'])
        input = widget.__class__.render(widget, name, value, attrs)

        return template.format(id=attrs['id'], input=input)
    return _render



def _form_control_file(field):
    field.field.widget.attrs['hidden'] = 'hidden'
    field.field.widget.render = bootstrapFileInput(field.field.widget)

@register.filter(name="bootstrap_form_controls")
def bootstrap_form_controls(form: forms.Form):
    """
    Add the bootstrap form-control class to each form widget
    @param form:
    @return:
    """
    newform = deepcopy(form)
    for field in newform:

        if isinstance(field.field.widget, forms.FileInput):
            _form_control_file(field)
        elif isinstance(field.field.widget, (forms.CheckboxInput, forms.RadioSelect)):
            pass
        else:
            _form_control_default(field)

    return newform
