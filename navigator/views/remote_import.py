import urllib.parse

from django.core.urlresolvers import reverse

from amcat.scripts.actions.remote_import import RemoteArticleSetImport
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import ProjectScriptView
from navigator.views.scriptview import ScriptHandler


class RemoteImportHandler(ScriptHandler):
    def get_redirect(self):
        aset_id = self.task._get_raw_result()
        return reverse("navigator:articleset-details", args=[self.task.project.id, aset_id]), "View set"


class RemoteArticleSetImportView(ProjectScriptView):
    script = RemoteArticleSetImport
    parent = ProjectDetailsView
    url_fragment = "remote-import-set"
    view_name = "articleset-remote-import"
    template_name = "remote_import.html"

    def _get_return_url(self):
        return_query = urllib.parse.urlencode({"remote_token": "%s", "remote_host": "REMOTE_HOST"})
        return_path = reverse("navigator:" + self.view_name, args=[self.project.id])
        return_url = urllib.parse.urlunsplit((self.request.scheme,
                                              self.request.get_host(),
                                              return_path,
                                              return_query,
                                              None))
        return return_url

    def _get_request_url(self):
        request_query = urllib.parse.urlencode({"return": "RETURN_URL"})
        request_path = reverse("navigator:request_token")
        request_url = "REQUEST_ORIGIN{}?{}".format(request_path, request_query)
        return request_url

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['local_project'].initial = self.project

        token = form.fields['remote_token']
        token.widget.attrs['data-return-url'] = self._get_return_url()
        token.widget.attrs['data-request-url'] = self._get_request_url()
        return form

    def get_initial(self):
        initial = super().get_initial()
        get = self.request.GET
        if 'remote_host' in get and 'remote_token' in get:
            initial['remote_host'] = get['remote_host']
            initial['remote_token'] = get['remote_token']
        return initial

    def form_valid(self, form):
        return self.run_form_delayed(self.project, RemoteImportHandler)
