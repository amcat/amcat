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

from django.shortcuts import render, redirect
from django.conf import settings
from django.db.models import Q

from settings.menu import PROJECT_MENU

from amcat.tools import toolkit
from amcat.models import Article, Project, ArticleSet, AnalysedArticle, AnalysisSentence

from navigator.utils.auth import check, check_perm
from navigator import forms

from amcat.scripts import article_upload as article_upload_scripts

import logging; log = logging.getLogger(__name__)

from amcat.nlp import syntaxtree, sbd 
from amcat.models import AnalysisSentence, RuleSet
from amcat.tools.pysoh.pysoh import SOHServer
from amcat.models import ArticleSetArticle, Sentence, Article

from django.core.urlresolvers import reverse

from api.rest.datatable import Datatable

def get_paragraphs(sentences):
    parnr = None
    for sentence in sentences:
        if sentence.sentence.parnr != parnr:
            if parnr is not None:
                paragraph.sort(key = lambda s: s.sentence.sentnr)
                yield paragraph
            parnr = sentence.sentence.parnr
            paragraph = []
        paragraph.append(sentence)
    

@check(AnalysedArticle, args='id')
@check(Project, args_map={'projectid' : 'id'}, args='projectid')
def analysedarticle(request, project, analysed_article):
    sentences = analysed_article.sentences.all()
    sentences = sentences.prefetch_related("tokens", "tokens__word", "tokens__word__lemma").select_related("sentence")

    paragraphs = list(get_paragraphs(sentences))
    
    menu = PROJECT_MENU
    context = project
    return render(request, "navigator/article/analysedarticle.html", locals())


@check(AnalysisSentence, args='id')
@check(Project, args_map={'projectid' : 'id'}, args='projectid')
def analysedsentence(request, project, sentence, rulesetid=None):

    tokens = (sentence.tokens.all().select_related("word", "word__word",  "word__lemma")
              .prefetch_related("triples", "triples__child", "triples__parent", "triples__relation"))

    soh = SOHServer(url="http://localhost:3030/x")
    tree = syntaxtree.SyntaxTree(soh, tokens)
    parsetree = tree.visualise().getHTMLObject()
    menu = PROJECT_MENU
    context = project

    rulesets = Datatable(RuleSet).rowlink_reverse("analysedsentence-ruleset", args=[project.id, sentence.id, "{id}"])#, rowlink="./upload-articles/{id}")

    if rulesetid:
        ruleset = RuleSet.objects.get(pk=rulesetid)
        trees = []
        ruleset_error = None

        tree.apply_lexicon(ruleset.lexicon_codebook, ruleset.lexicon_language)
        parsetree = tree.visualise().getHTMLObject()
        grey_rel = lambda triple : ({'color':'grey'} if 'rel_' in triple.predicate else {})
        
        for rule in ruleset.rules.all():
            try:
                tree.apply_rule(rule)
                if rule.display:
                    trees.append((rule, tree.visualise(triple_args_function=grey_rel).getHTMLObject()))
            except Exception, e:
                ruleset_error = "Exception processing rule {rule.order}: {rule.label}\n\n{e}".format(**locals())
                break

        if not ruleset_error:
            finaltree = tree.visualise(triple_args_function=grey_rel).getHTMLObject()
            

    return render(request, "navigator/article/analysedsentence.html", locals())

@check(Article, args_map={'article_id' : 'id'}, args='article_id')
@check(ArticleSet, args_map={'articleset_id' : 'id'}, args='articleset_id')
@check(Project, args_map={'project_id' : 'id'}, args='project_id')
def view(request, project, articleset, article):
    
    menu = PROJECT_MENU
    context = project

    return render(request, "navigator/article/view.html", locals())

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

def copy_article(article):
    new = Article.objects.get(id=article.id)
    new.id = None
    new.uuid = None
    new.text = ""
    new.length = None
    new.byline = None
    return new

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
    if not form.is_valid():
        raise ValueError("Non-valid form passed: {form.errors}".format(**locals()))

    articles = list(get_articles(article, sentences))

    # We won't use bulk_create yet, as it bypasses save() and doesn't
    # insert ids
    for art in articles:
        art.save()
        sbd.create_sentences(art)

    # Context variables for template
    form_data = form.cleaned_data 
    all_sets = list(project.all_articlesets().filter(articles=article))

    # Keep a list of touched sets, so we can invalidate their indices
    dirty_sets = ArticleSet.objects.none()

    # Add splitted articles to existing sets
    ArticleSet.articles.through.objects.bulk_create([
        ArticleSet.articles.through(articleset=aset, article=art) for
            art in articles for aset in form_data["add_splitted_to_sets"]
    ])

    # Collect changed sets
    for field in ("add_splitted_to_sets", "remove_from_sets", "add_to_sets"):
        dirty_sets |= form_data[field]

    # Add splitted articles to sets wherin the original article live{d,s}
    if form_data["add_splitted_to_all"]:
        articlesetarts = ArticleSet.articles.through.objects.filter(article=article, articleset__project=project)

        ArticleSet.articles.through.objects.bulk_create([
            ArticleSet.articles.through(articleset=asetart.articleset, article=art)
                for art in articles for asetart in articlesetarts
        ])

        dirty_sets |= project.all_articlesets().filter(articles=article).only("id")

    if form_data["remove_from_sets"]:
        ArticleSet.articles.through.objects.filter(article=article, articleset=form_data["remove_from_sets"]).delete()
        
    if form_data["remove_from_all_sets"]:
        ArticleSet.articles.through.objects.filter(article=article, articleset__project=project).delete()
        dirty_sets |= ArticleSet.objects.filter(project=project, articles=article).distinct().only("id")

    if form_data["add_splitted_to_new_set"]:
        new_splitted_set = ArticleSet.create_set(project, form_data["add_splitted_to_new_set"], articles)

    if form_data["add_to_sets"]:
        ArticleSet.articles.through.objects.bulk_create(ArticleSet.articles
            .through(articleset=a, article=article) for a in form_data["add_to_sets"]
        )

    if form_data["add_to_new_set"]:
        new_set = ArticleSet.create_set(project, form_data["add_to_new_set"], [article])

    dirty_sets.update(index_dirty=True)
    return locals()

    
@check(Article, args_map={'article_id' : 'id'}, args='article_id')
@check(Project, args_map={'project_id' : 'id'}, args='project_id')
def split(request, project, article):
    sentences = sbd.get_or_create_sentences(article).only("sentence", "parnr")
    form = forms.SplitArticleForm(project, article, data=request.POST or None)

    if form.is_valid():
        selected_sentence_ids = set(get_sentence_ids(request.POST)) - {None,}
        if selected_sentence_ids:
            sentences = Sentence.objects.filter(id__in=selected_sentence_ids)
            context = handle_split(form, project, article, sentences)
            return render(request, "navigator/article/split-done.html", context)

    # Get sentences, skip headline
    sentences = _get_sentences(sentences)
    sentences.next()
    return render(request, "navigator/article/split.html", locals())

@check(ArticleSet, args_map={'remove_articleset_id' : 'id'}, args='remove_articleset_id', action='update')
@check(Article, args_map={'article_id' : 'id'}, args='article_id')
@check(Project, args_map={'project_id' : 'id'}, args='project_id')
def remove_from(request, project, article, remove_articleset):
    """
    Remove given article from given articleset. Does not error when it does not exist.
    """
    ArticleSetArticle.objects.filter(articleset=remove_articleset, article=article).delete()
    return redirect(reverse("article", args=[project.id, article.id]))


### UPLOAD ARTICLES ###
def _save_articles(request, arts, project, cldata):
    """
    Save articles to database.

    @param arts: articles to save
    @param project: project to save articles to
    @param cldata: django cleaned formdata
    """
    for a in arts:
        a.project = project
        a.save()

    # Set logic
    if cldata['new_set']:
       nset = ArticleSet(name=cldata['new_set'], project=project)
       nset.save()
    elif cldata['exi_set']:
        nset = ArticleSet.objects.using(request.user.db).get(name=cldata['exi_set'].name,
                                                             project=project)

    for a in arts:
        nset.articles.add(a)

    return nset, arts

@toolkit.dictionary
def _build_option_forms(request, choices):
    """
    Build options forms based on available scripts.

    @type return: dict
    @return: {
        'script_name_1' : DjangoForm,
        ...
    }
    """
    for script in choices:
        # Extract form from upload script
        frm = getattr(article_upload_scripts, script[0]).options_form 

        if frm is None:
            # Upload script has no form
            yield (script[0], None)
            continue

        if request.POST.get('script') == script[0]:
           # If script is selected..
           yield (script[0], frm(request.POST or None))
           continue

        # Form does exist but not selected
        yield (script[0], frm())


@check_perm("add_articles", True)
def upload_article(request, id):
    """
    This view gives users the ability to upload articles in various formats,
    using upload-scripts located in amcat.scripts.article_upload.

    For every script, it generates a form and uses javascript to automatically
    hide / show it based on the selected one.
    """
    error = False 

    project = Project.objects.get(id=id)
    form = forms.UploadScriptForm(project, request.POST or None, request.FILES or None)

    # Build forms for all scripts
    option_forms = _build_option_forms(request, form.fields['script'].choices)

    # Only process when submitted
    if request.POST.get('submit', None) and form.is_valid():
        # Get script bases on given id
        script = getattr(article_upload_scripts, form.cleaned_data['script'])
        script_form = option_forms[form.cleaned_data['script']]

        if script_form is None or script_form.is_valid():
            # Option form is valid, try saving articles to database
            for fn, bytes in form.cleaned_data['file']:
                uni = bytes.decode(form.cleaned_data['encoding'])

                try:
                    articles = script(request.POST).run(uni)
                    nset, articles = _save_articles(request, articles,
                                                    project, form.cleaned_data)

                except Exception as error:
                    if settings.DEBUG: 
                        raise
                else:
                    return render(request, "navigator/project/upload_article_success.html",
                                  dict(context=project, set=nset, articles=articles))


    return render(request, "navigator/project/upload_article.html", dict(context=project,
                                                                        form=form,
                                                                        error=error,
                                                                        option_forms=option_forms,
                                                                        menu=PROJECT_MENU))


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestArticleViews(amcattest.PolicyTestCase):
    def create_test_sentences(self):
        article = amcattest.create_test_article(byline="foo", text="Dit is. Tekst.\n\n"*3 + "Einde.")
        sbd.create_sentences(article)
        return article, article.sentences.all()

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
        map(lambda a : a.save(), arts)

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
        
    def test_handle_split(self):
        from amcat.tools import amcattest
        from functools import partial

        article, sentences = self.create_test_sentences()
        project = amcattest.create_test_project()
        aset1 = amcattest.create_test_set(4, project=project)
        aset2 = amcattest.create_test_set(5, project=project)
        aset3 = amcattest.create_test_set(0)

        for _set in [aset1, aset2]:
            for _article in _set.articles.all():
                sbd.create_sentences(_article)

        a1, a2 = aset1.articles.all()[0], aset2.articles.all()[0]
        
        aset1.articles.through.objects.create(articleset=aset1, article=article)
        aset3.articles.through.objects.create(articleset=aset3, article=a1)

        form = partial(forms.SplitArticleForm, project, article, initial={
            "remove_from_sets" : False 
        })

        # Test form defaults (should do nothing!)
        f = form(dict())
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())

        self.assertEquals(5, aset1.articles.all().count())
        self.assertEquals(5, aset2.articles.all().count())
        self.assertEquals(1, aset3.articles.all().count())
        self.assertTrue(article in aset1.articles.all())
        self.assertTrue(article not in aset2.articles.all())
        self.assertTrue(article not in aset3.articles.all())

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
        self.assertTrue(article in aset2.articles.all())

        # Test add_splitted_to_new_set
        f = form(dict(add_splitted_to_new_set="New Set 2"))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())
        aset = project.all_articlesets().filter(name="New Set 2")
        self.assertTrue(aset.exists())
        self.assertEquals(project, aset[0].project)
        self.assertEquals(1, aset[0].articles.count())
        self.assertTrue(article not in aset[0].articles.all())

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
        aset1.articles.through.objects.create(articleset=aset1, article=article)
        aset1.articles.through.objects.create(articleset=aset3, article=article)
        # Note: already in aset2 due to previous tests

        f = form(dict(remove_from_all_sets=True))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())

        self.assertTrue(aset1 in project.all_articlesets())
        self.assertTrue(aset2 in project.all_articlesets())
        self.assertFalse(aset3 in project.all_articlesets())

        self.assertFalse(article in aset1.articles.all())
        self.assertFalse(article in aset2.articles.all())
        self.assertTrue(article in aset3.articles.all())

        # Are articlesets set to index_dirty=True?
        project = amcattest.create_test_project()
        aset = amcattest.create_test_set(5, project=project)
        aset.index_dirty = False
        aset.save()

        f = forms.SplitArticleForm(aset.project, aset.articles.all()[0], dict(add_splitted_to_sets=[aset.id]))
        handle_split(f, aset.project, aset.articles.all()[0], Sentence.objects.none())
        self.assertTrue(ArticleSet.objects.get(id=aset.id).index_dirty)

        
