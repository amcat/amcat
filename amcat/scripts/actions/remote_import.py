import requests
from amcatclient.amcatclient import AmcatAPI, APIError
from django import forms
from django.utils.html import format_html

from amcat.forms.widgets import add_bootstrap_classes as bt
from amcat.models import Article, ArticleSet, Project
from amcat.scripts.script import Script

API_ERRORS = {
    401: "You are not authorized to access the remote server. Incorrect token?",
    403: "You are not authorized to access the requested articleset.",
    404: "The requested articleset was not found.",
    500: "An internal error occured while accessing the remote server.",
    -1: "An error occured while accessing the remote server.",
}

COPY_SET_FIELDS = {"name", "provenance", "featured"}

# article fields to be retrieved from the server
ARTICLE_FIELDS = {"date", "title", "url", "text", "hash", "parent_hash", "properties"}

# 3.4-style article fields
LEGACY_ARTICLE_FIELDS = {"metastring", "byline", "uuid", "author", "headline", "section",
                         "length", "addressee", "externalid", "insertdate", "pagenr", "medium", "parent"}

#
COPY_ARTICLE_FIELDS = {"date", "title", "url", "text", "parent_hash", "properties"} | LEGACY_ARTICLE_FIELDS


class TokenWidget(forms.TextInput):
    """
    A TextInput with a "request token" button.
    """

    def render(self, name, value, attrs=None):
        input_group = '<div class="input-group">{}</div>'
        input = super().render(name, value, attrs)
        button = format_html(
            '<span class="input-group-btn">'
            '<a id="{0}-request-token" class="btn btn-default">Request token</a>'
            '</span>'
            , name)
        return format_html(input_group, input + button)


class RemoteArticleSetImportForm(forms.Form):
    remote_host = bt(forms.URLField())
    remote_token = bt(forms.CharField(label="Access token", widget=TokenWidget))
    remote_project_id = bt(forms.IntegerField())
    remote_articleset_id = bt(forms.IntegerField())
    local_project = forms.ModelChoiceField(queryset=Project.objects.all(), widget=forms.HiddenInput)


class RemoteQuery:
    def __init__(self, host: str, token: str, project: int, articleset: int, page_size: int = 100):
        self.api = AmcatAPI(host, token=token)
        self.project = project
        self.page_size = page_size
        self.session = requests.Session()
        self.articleset = articleset

    def __iter__(self):
        yield from self.api.get_articles(project=self.project,
                                         articleset=self.articleset,
                                         page_size=self.page_size,
                                         columns=",".join(ARTICLE_FIELDS | LEGACY_ARTICLE_FIELDS),
                                         yield_pages=True)

    def get_articleset(self):
        return self.api.get_set(self.project, self.articleset)


class RemoteArticleSetImport(Script):
    options_form = RemoteArticleSetImportForm

    def handleError(self, error: APIError):
        s = error.http_status
        msg = API_ERRORS.get(s, API_ERRORS[-1])
        raise Exception(msg + " (status code: {})".format(s))

    def _run(self, local_project, remote_host, remote_token, remote_project_id, remote_articleset_id):
        try:
            page_size = 1000
            query = RemoteQuery(remote_host, remote_token, remote_project_id, remote_articleset_id, page_size=page_size)
            set = {k: v for k, v in query.get_articleset().items() if k in COPY_SET_FIELDS}
            set.update(project=local_project)
            set = ArticleSet.objects.create(**set)
            for page in query:
                articles_hashes = [(self.create_article(x, local_project), x["hash"]) for x in page]
                hashmap = {old_hash: article.hash for article, old_hash in articles_hashes}
                articles, _ = zip(*articles_hashes)
                articles = list(articles)
                for article in articles:
                    if article.parent_hash in hashmap:
                        article.parent_hash = hashmap[article.parent_hash]

                Article.create_articles(articles, articleset=set)
            return set.id
        except APIError as e:
            self.handleError(e)

    def _map_es_type(self, key, value):
        if key in ARTICLE_FIELDS:
            return key, value
        t = type(value)
        if t is int:
            return "{}_int".format(key), value
        if t is float:
            return "{}_num".format(key), value
        return key, value

    def create_article(self, art_dict, project):
        art_dict = {k: v for k, v in art_dict.items() if k in COPY_ARTICLE_FIELDS}
        art_dict["project"] = project
        if 'headline' in art_dict and 'title' not in art_dict:
            art_dict['title'] = art_dict.pop('headline')

        art_dict = dict(self._map_es_type(k, v) for k, v in art_dict.items())
        art = Article(**art_dict)
        return art


if __name__ == '__main__':
    from amcat.scripts.tools import cli

    cli.run_cli()
