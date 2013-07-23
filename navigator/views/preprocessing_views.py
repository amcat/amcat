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

from django.core.urlresolvers import reverse

from amcat.scripts.actions.process_parsing import CheckParsing
from navigator.views.scriptview import ProjectScriptView
from amcat.models import ArticleSet, AnalysedArticle

from django.db.models import Count
from django_boolean_sum import BooleanSum

    
class ProcessParsingView(ProjectScriptView):
    script = CheckParsing
    success_template_name = "navigator/project/process_parsing.html"
    
    def get_template_names(self):
        if getattr(self, 'success', None):
            return [self.success_template_name]
        else:
            return [self.template_name]
        
    def get_context_data(self, **kwargs):
        context = super(ProcessParsingView, self).get_context_data(**kwargs)
        aset, plugin = [self.form.cleaned_data[x] for x in ("articleset", "plugin")]
        
        context["set"] = aset
        context["plugin"] = plugin
        context["totaln"] = aset.articles.count()

        q = (AnalysedArticle.objects.filter(article__articlesets_set=aset, plugin=plugin)
             .values("article__articlesets_set__project", "plugin_id", "article__articlesets_set")
             .annotate(assigned=Count("id"), done=BooleanSum("done"), error=BooleanSum("error")))

        context.update(q[0])
        print context

        
        return context
        
    def form_valid(self, form):
        result = self.run_form(form)
        return self.render_to_response(self.get_context_data(form=form, result=result, success=True))
        
    def get_form(self, form_class):
        form = super(ProcessParsingView, self).get_form(form_class)
        if self.request.method == 'GET':
            #form.fields['target_project'].queryset = qs
            # only show favourites
            qs = ArticleSet.objects.filter(favourite_of_projects=self.project.id)
            form.fields['articleset'].queryset=qs
            del form.fields['analysed_articles']
        return form
            
