from django import forms
from actionform import ActionForm

import functools
import urllib.parse
import requests
from amcatclient.amcatclient import AmcatAPI
from django.contrib.postgres.forms import JSONField


class RemoteArticleSetImportForm(forms.Form):
    remote_host = forms.URLField()
    remote_token = forms.CharField(label="Access Token", required=False)
    articleset = forms.IntegerField()

class RemoteQuery:
    def __init__(self, host:str, token:str, start_page:int = 0, page_size: int = 100, **kwargs):
        self.api = AmcatAPI(host, token=token)
        self.start_page = start_page
        self.query_params = dict(kwargs, page_size=page_size)
        self.session = requests.Session()

    def __iter__(self):
        yield from self.api.get_scroll("search", filters=self.query_params)


class RemoteArticleSetImport(ActionForm):
    form_class = RemoteArticleSetImportForm

    @property
    def query(self) -> str:
        return None

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
