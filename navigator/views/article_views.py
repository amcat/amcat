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

from itertools import chain

from django.test import Client
from django.views.generic.detail import DetailView
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.template.defaultfilters import escape

from navigator.views.articleset_views import ArticleSetDetailsView
from amcat.models import Article, ArticleSet, Sentence
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectFormView, ProjectActionRedirectView
from amcat.tools import sbd
from amcat.models import authorisation
from navigator.views.project_views import ProjectDetailsView
import navigator.forms


class ArticleDetailsView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, DetailView):
    model = Article

    def can_view_text(self):
        """Checks if the user has the right to edit this project"""
        return self.request.user.get_profile().has_role(authorisation.ROLE_PROJECT_READER, self.object.project)

    def highlight(self):
        if not self.last_query:
            return None
        self.object.highlight(self.last_query)

    def get_context_data(self, **kwargs):
        context = super(ArticleDetailsView, self).get_context_data(**kwargs)

        # Highlight headline / text
        self.highlight()
        context['text'] = self.object.text
        context['headline'] = self.object.headline

        context['articleset'] = None
        if 'articleset_id' in self.kwargs:
            context['articleset'] = ArticleSet.objects.get(id=self.kwargs['articleset_id'])

        tree = self.object.get_tree()
        if tree.children:
            context['tree'] = tree.get_html(active=self.object, articleset=context['articleset'])

        # HACK: put query back on session to allow viewing more articles
        self.request.session["query"] = self.last_query
        return context


class ArticleSetArticleDetailsView(ArticleDetailsView):
    parent = ArticleSetDetailsView
    model = Article

    def get_context_data(self, **kwargs):
        context = super(ArticleSetArticleDetailsView, self).get_context_data(**kwargs)
        context['articleset_id'] = self.kwargs['articleset_id']
        context['text'] = escape(self.object.text)
        return context




class ProjectArticleDetailsView(ArticleDetailsView):
    model = Article
    parent = ProjectDetailsView
    context_category = 'Articles'
    template_name = 'project/article_details.html'
    url_fragment = "articles/(?P<article_id>[0-9]+)"

    @classmethod
    def _get_breadcrumb_name(cls, kwargs, view):
        aid = kwargs['article_id']
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
        if not self.request.user.get_profile().has_role(authorisation.ROLE_PROJECT_WRITER, project):
            raise PermissionDenied("User {self.request.user} has insufficient rights on project {project}".format(**locals()))


        articles = [int(kwargs["article_id"])]
        ArticleSet.objects.get(pk=remove_set).remove_articles(articles)


    def get_redirect_url(self, project_id, article_id):
        remove_set = int(self.request.GET["remove_set"])
        return_set = self.request.GET.get("return_set")
        if return_set:
            return_set = int(return_set)
            if remove_set != return_set:
                return reverse(ArticleSetArticleDetailsView.get_view_name(), args=(project_id, return_set, article_id))
        return super(ArticleRemoveFromSetView, self).get_redirect_url(project_id=project_id, article_id=article_id)

    def success_message(self, result=None):
        article = self.kwargs["article_id"]
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

    # Get sentence, skipping the headline
    all_sentences = list(article.sentences.all()[1:])

    not_in_article = set(sentences) - set(all_sentences)
    if not_in_article:
        raise ValueError(
            "Sentences specified as delimters, but not in article: {not_in_article}. Did you try to split on a headline?"
            .format(**locals())
        )

    prev_parnr = 1
    for parnr, sentnr in chain(sentences.values_list("parnr", "sentnr"), ((None, None),)):
        # Skip headline paragraph
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

def copy_article(article):
    new = Article.objects.get(id=article.id)
    new.id = None
    new.uuid = None
    new.text = ""
    new.length = None
    new.byline = None
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
    except IndexError, ValueError:
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
        return Article.objects.get(pk=self.kwargs['article_id'])

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
        ctx["sentences"].next() # skip headline
        return ctx


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestSplitArticles(amcattest.AmCATTestCase):
    def create_test_sentences(self):
        article = amcattest.create_test_article(byline="foo", text="Dit is. Tekst.\n\n"*3 + "Einde.")
        sbd.create_sentences(article)
        return article, article.sentences.all()

    @amcattest.use_elastic
    def test_article_split_view(self):
        from amcat.models import Role, ProjectRole

        article, sentences = self.create_test_sentences()
        aset = amcattest.create_test_set(0)
        aset.add_articles([article])

        user = amcattest.create_test_user(username="fred", password="secret")
        ProjectRole.objects.create(user=user, project=aset.project, role=Role.objects.get(label="admin", projectlevel=True))

        # Only test the very basic; if a simple split works we trust the view
        # to use handle_split(), which is tested more extensively below.
        url = reverse(ArticleSplitView.get_view_name(), args=[aset.project.id, article.id])

        client = Client()
        client.login(username="fred", password="secret")

        response = client.post(url, {
            "add_to_new_set": "test_article_split_view_set",
            "remove_from_all_sets": "on",
            "add_splitted_to_new_set": "",
            "sentence-%s" % sentences[1].id: "on"
        })

        new_set = ArticleSet.objects.filter(name="test_article_split_view_set")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(new_set.exists())
        self.assertEqual(article, new_set[0].articles.all()[0])

    @amcattest.use_elastic
    def test_handle_split(self):
        from amcat.tools import amcattest
        from functools import partial

        article, sentences = self.create_test_sentences()
        project = amcattest.create_test_project()
        aset1 = amcattest.create_test_set(4, project=project)
        aset2 = amcattest.create_test_set(5, project=project)
        aset3 = amcattest.create_test_set(0)

        # Creates a codingjob for each articleset, as handle_split should account
        # for "codedarticlesets" as well.
        cj1 = amcattest.create_test_job(articleset=aset1)
        cj2 = amcattest.create_test_job(articleset=aset2)
        cj3 = amcattest.create_test_job(articleset=aset3)

        for _set in [aset1, aset2]:
            for _article in _set.articles.all():
                sbd.create_sentences(_article)

        a1, a2 = aset1.articles.all()[0], aset2.articles.all()[0]

        aset1.add_articles([article])
        aset3.add_articles([a1])

        form = partial(navigator.forms.SplitArticleForm, project, article, initial={
            "remove_from_sets": False
        })

        # Test form defaults (should do nothing!)
        f = form(dict())
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())

        self.assertEquals(5, aset1.articles.all().count())
        self.assertEquals(5, aset2.articles.all().count())
        self.assertEquals(1, aset3.articles.all().count())

        self.assertTrue(self.article_in(cj1, aset1, article))
        self.assertFalse(self.article_in(cj2, aset2, article))
        self.assertFalse(self.article_in(cj3, aset3, article))

        # Passing invalid form should raise exception
        f = form(dict(add_to_sets=[-1]))
        self.assertFalse(f.is_valid())
        self.assertRaises(ValueError, handle_split, f, project, article, Sentence.objects.none())

        # Test add_to_new_set
        f = form(dict(add_to_new_set="New Set 1"))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())
        aset = project.all_articlesets().filter(name="New Set 1")
        self.assertTrue(aset.exists())
        self.assertEquals(project, aset[0].project)

        # Test add_to_sets
        f = form(dict(add_to_sets=[aset3.id]))
        self.assertFalse(f.is_valid())
        f = form(dict(add_to_sets=[aset2.id]))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())
        self.assertTrue(self.article_in(cj2, aset2, article))

        # Test add_splitted_to_new_set
        f = form(dict(add_splitted_to_new_set="New Set 2"))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())
        aset = project.all_articlesets().filter(name="New Set 2")
        self.assertTrue(aset.exists())
        self.assertEquals(project, aset[0].project)
        self.assertEquals(1, aset[0].articles.count())
        self.assertFalse(self.article_in(None, aset[0], article))

        # Test add_splitted_to_sets
        f = form(dict(add_splitted_to_sets=[aset2.id]))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())
        self.assertTrue(article in aset2.articles.all())

        # Test remove_from_sets
        f = form(dict(remove_from_sets=[aset1.id]))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())
        self.assertTrue(article not in aset1.articles.all())

        # Test remove_from_all_sets
        aset1.add_articles([article])
        aset2.add_articles([article])
        aset3.add_articles([article])

        f = form(dict(remove_from_all_sets=True))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())

        self.assertTrue(aset1 in project.all_articlesets())
        self.assertTrue(aset2 in project.all_articlesets())
        self.assertFalse(aset3 in project.all_articlesets())

        self.assertFalse(self.article_in(cj1, aset1, article))
        self.assertFalse(self.article_in(cj2, aset2, article))
        self.assertTrue(self.article_in(cj3, aset3, article))



    def article_in(self, codingjob, articleset, article):
        from amcat.tools.amcates import ES
        ES().flush()

        if codingjob is not None:
            if not codingjob.coded_articles.filter(article=article):
                return False

        return article.id in (articleset.get_article_ids() | articleset.get_article_ids(use_elastic=True))



class TestArticleViews(amcattest.AmCATTestCase):
    def create_test_sentences(self):
        article = amcattest.create_test_article(byline="foo", text="Dit is. Tekst.\n\n"*3 + "Einde.")
        sbd.create_sentences(article)
        return article, article.sentences.all()

    @amcattest.use_elastic
    def test_get_articles(self):
        from amcat.models import Sentence
        _get_articles = lambda a,s : list(get_articles(a,s))

        # Should raise exception if sentences not in article
        article, sentences = self.create_test_sentences()
        s1 = Sentence.objects.filter(id=amcattest.create_test_sentence().id)
        self.assertRaises(ValueError, _get_articles, article, s1)

        # Should raise an exception if we try to split on headline
        self.assertRaises(ValueError, _get_articles, article, sentences.filter(parnr=1))

        # Should return a "copy", with byline in "text" property
        arts = _get_articles(article, Sentence.objects.none())
        Article.create_articles(arts)

        self.assertEquals(len(arts), 1)
        sbd.create_sentences(arts[0])

        self.assertEquals(
            [s.sentence for s in sentences[1:]],
            [s.sentence for s in arts[0].sentences.all()[1:]]
        )

        self.assertTrue("foo" in arts[0].text)

        # Should be able to split on byline
        self.assertEquals(2, len(_get_articles(article, sentences[1:2])))
        a, b = _get_articles(article, sentences[4:5])

        # Check if text on splitted articles contains expected
        self.assertTrue("Einde" not in a.text)
        self.assertTrue("Einde" in b.text)
