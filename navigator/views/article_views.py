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
import html
from itertools import chain

from django.views.generic.detail import DetailView
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.template.defaultfilters import escape

from navigator.views.articleset_views import ArticleSetDetailsView
from amcat.models import Article, ArticleSet, Sentence
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectFormView, ProjectActionRedirectView
from amcat.tools import sbd
from amcat.models import authorisation, Project, CodingJob
from navigator.views.project_views import ProjectDetailsView
import navigator.forms


class ArticleDetailsView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, DetailView):
    model = Article

    def has_permission(self, perm):
        if perm >= authorisation.ROLE_PROJECT_WRITER:
            return False
        # permission to view/read an article can be granted through any of its sets (!)
        asets = ArticleSet.objects.filter(articles=self.get_object()).only("project")
        projects = {aset.project for aset in asets}
        projects |= set(Project.objects.filter(articlesets__id__in=asets.values_list("id", flat=True)))
        
        return any(p.has_role(self.request.user, perm)
                   for p in projects)
    
    def highlight(self):
        if not self.last_query:
            self.object.text = html.escape(self.object.text)
            self.object.title = html.escape(self.object.title)
            return None
        self.object.highlight(self.last_query)

    def get_context_data(self, **kwargs):
        context = super(ArticleDetailsView, self).get_context_data(**kwargs)

        # Highlight title / text
        self.highlight()
        context['text'] = self.object.text
        context['title'] = self.object.title

        context['articleset'] = None
        if 'articleset' in self.kwargs:
            context['articleset'] = ArticleSet.objects.get(id=self.kwargs['articleset'])

        article = self.get_object()
        context['codingjobs'] = CodingJob.objects.filter(articleset__in=article.articlesets_set.all())

        # HACK: put query back on session to allow viewing more articles
        self.request.session["query"] = self.last_query
        return context


class ArticleSetArticleDetailsView(ArticleDetailsView):
    parent = ArticleSetDetailsView
    model = Article

    def get_context_data(self, **kwargs):
        context = super(ArticleSetArticleDetailsView, self).get_context_data(**kwargs)
        context['articleset_id'] = self.kwargs['articleset']
        context['text'] = escape(self.object.text)
        return context




class ProjectArticleDetailsView(ArticleDetailsView):
    model = Article
    parent = ProjectDetailsView
    context_category = 'Articles'
    template_name = 'project/article_details.html'
    url_fragment = "articles/(?P<article>[0-9]+)"

    @classmethod
    def _get_breadcrumb_name(cls, kwargs, view):
        aid = kwargs['article']
        a = Article.objects.get(pk=aid)
        return "Article {a.id} : {a}".format(**locals())

    @classmethod
    def get_view_name(cls):
        return "project-article-details"



class ArticleRemoveFromSetView(ProjectActionRedirectView):
    parent = ProjectArticleDetailsView
    url_fragment = "removefromset"
    def action(self, **kwargs):
        remove_set = int(self.request.GET["remove_set"])
        # user needs to have writer+ on the project of the articleset
        project = ArticleSet.objects.get(pk=remove_set).project
        if not project.has_role(authorisation.ROLE_PROJECT_WRITER, self.request.user):
            raise PermissionDenied("User {self.request.user} has insufficient rights on project {project}".format(**locals()))


        articles = [int(kwargs["article"])]
        ArticleSet.objects.get(pk=remove_set).remove_articles(articles)


    def get_redirect_url(self, project, article):
        remove_set = int(self.request.GET["remove_set"])
        return_set = self.request.GET.get("return_set")
        if return_set:
            return_set = int(return_set)
            if remove_set != return_set:
                return reverse(ArticleSetArticleDetailsView.get_view_name(), args=(project, return_set, article))
        return super(ArticleRemoveFromSetView, self).get_redirect_url(project_id=project, article_id=article)

    def success_message(self, result=None):
        article = self.kwargs["article"]
        remove_set =  int(self.request.GET["remove_set"])
        return "Removed the current article ({article}) from set {remove_set}".format(**locals())


################################################################################
# Splitting. Yes, it was that much work                                        #
################################################################################

def get_articles(article, sentences):
    """
    Split `article` with `sentences` as delimeters. For each sentence the text
    before it, including itself, is copied to a new article with is yield.

    @param sentences: delimeters for splitting
    @type sentences: QuerySet

    @param article: article which contains sentences
    @type article: models.Article

    @requires: ordering of sentences ("parnr", "sentnr")
    @requires: sbd.get_or_create_sentences() called on `article`
    @requires: all(a in article.sentences.all() for a in sentences)

    @returns: generator with newly splitted articles (not saved)
    @raises: ValueError if a sentence in `sentences` is not in article.sentences
    """
    new_article = copy_article(article)

    # Get sentence, skipping the title
    all_sentences = list(article.sentences.all()[1:])

    not_in_article = set(sentences) - set(all_sentences)
    if not_in_article:
        raise ValueError(
            "Sentences specified as delimters, but not in article: {not_in_article}. Did you try to split on a title?"
            .format(**locals())
        )

    prev_parnr = 1
    for parnr, sentnr in chain(sentences.values_list("parnr", "sentnr"), ((None, None),)):
        # Skip title paragraph
        if parnr == 1: continue

        while True:
            try: sent = all_sentences.pop(0)
            except IndexError:
                new_article.text = new_article.text.strip()
                yield new_article
                break

            if sent.parnr != prev_parnr:
                new_article.text += "\n\n"

            new_article.text += sent.sentence
            new_article.text += ". "
            prev_parnr = sent.parnr

            if (sent.sentnr == sentnr and sent.parnr == parnr):
                new_article.text = new_article.text.strip()
                yield new_article
                new_article = copy_article(article)
                break


def handle_split(form, project, article, sentences):
    articles = list(get_articles(article, sentences))

    # We won't use bulk_create yet, as it bypasses save() and doesn't
    # insert ids
    Article.create_articles(articles)
    for art in articles:
        sbd.get_or_create_sentences(art)

    if not form.is_valid():
        raise ValueError("Form invalid: {form.errors}".format(**locals()))

    # Context variables for template
    form_data = form.cleaned_data
    all_sets = list(project.all_articlesets().filter(articles=article))

    # Add splitted articles to existing sets
    for aset in form_data["add_splitted_to_sets"]:
        aset.add_articles(articles)

    # Add splitted articles to sets wherin the original article live{d,s}
    if form_data["add_splitted_to_all"]:
        asets = project.all_articlesets().filter(articles=article).only("id")
        for aset in asets:
            aset.add_articles(articles)

    if form_data["remove_from_sets"]:
        for aset in form_data["remove_from_sets"]:
            aset.remove_articles([article])

    if form_data["remove_from_all_sets"]:
        for aset in ArticleSet.objects.filter(project=project, articles=article).distinct():
            aset.remove_articles([article])

    if form_data["add_splitted_to_new_set"]:
        new_splitted_set = ArticleSet.create_set(project, form_data["add_splitted_to_new_set"], articles)

    if form_data["add_to_sets"]:
        for articleset in form_data["add_to_sets"]:
            articleset.add_articles([article])

    if form_data["add_to_new_set"]:
        new_set = ArticleSet.create_set(project, form_data["add_to_new_set"], [article])

    return locals()


def copy_article(article: Article):
    new = Article(
        project_id=article.project_id,
        date=article.date,
        title=article.title,
        url=article.url,
        #text=article.text <-- purposely omit text!
        #hash=article.hash <-- purposely omit hash!
        parent_hash=article.parent_hash
    )

    new.properties.update(article.properties)

    return new

def _get_sentences(sentences, prev_parnr=1):
    """
    Yields (sentence, bool) where bool indicates whether this sentences starts
    a new paragraph.
    """
    for sentence in sentences:
        yield (sentence, prev_parnr != sentence.parnr)
        prev_parnr = sentence.parnr

def parse_sentence_name(name):
    if not name.startswith("sentence-"): return

    try:
        return int(name.split("-")[1])
    except (IndexError, ValueError):
        pass

def get_sentence_ids(post):
    for name, checked in post.items():
        if checked != "on": continue
        yield parse_sentence_name(name)

class ArticleSplitView(ProjectFormView):
    parent = ProjectArticleDetailsView
    url_fragment = "split"
    template_name = "project/article_split.html"
    form_class = navigator.forms.SplitArticleForm

    @classmethod
    def _get_breadcrumb_name(cls, kwargs, view):
         return cls.url_fragment

    def get_form(self, form_class):
        return form_class(data=self.request.POST, project=self.project, article=self.article)

    @property
    def article(self):
        return Article.objects.get(pk=self.kwargs['article'])

    def form_valid(self, form):
        selected_sentence_ids = set(get_sentence_ids(self.request.POST)) - {None,}
        if selected_sentence_ids:
            sentences = Sentence.objects.filter(id__in=selected_sentence_ids)
            context = handle_split(form, self.project, self.article, sentences)
            context = dict(self.get_context_data(**context))
            return render(self.request, "project/article_split_done.html", context)
        return render(self.request, "project/article_split_empty.html", self.get_context_data())

    def get_context_data(self, **kwargs):
        ctx = super(ArticleSplitView, self).get_context_data(**kwargs)
        sentences = sbd.get_or_create_sentences(self.article).only("sentence", "parnr")
        ctx["sentences"] = _get_sentences(sentences)
        next(ctx["sentences"]) # skip title
        return ctx

