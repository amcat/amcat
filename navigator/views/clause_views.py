
from django.views.generic.edit import FormView
from django import forms

from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin
from navigator.views.project_views import ProjectDetailsView
from amcat.tools.amcatxtas import get_adhoc_result

class ClauseView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, FormView):
    class form_class(forms.Form):
        sentence = forms.CharField(label='Sentence', max_length=255)

    parent = ProjectDetailsView
    url_fragment = "clauses"

    def form_valid(self, form):
        # Get parse
        sent = form.cleaned_data['sentence']
        parse = get_adhoc_result('clauses_en', sent)
        return self.render_to_response(self.get_context_data(form=form, test=parse))
