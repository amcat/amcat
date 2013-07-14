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
from amcat.scripts.actions.split_articles import SplitArticles

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
    return new

def get_articles(article, sentences):
    prev_parnr = 1 

    new_article = copy_article(article)
    all_sentences = list(article.sentences.all())
    sentences = sentences.values_list("parnr", "sentnr")

    for parnr, sentnr in chain(sentences, ((None, None),)):
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

def handle_split(request, form, project, article, sentences):
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
    dirty_sets |= ArticleSet.objects.filter(id__in=[s.id for s in form_data["add_splitted_to_sets"]])

    # Add splitted articles to sets wherin the original article live{d,s}
    if form_data["add_splitted_to_all"]:
        articlesetarts = ArticleSet.articles.through.objects.filter(article=article, articleset__project=project)

        ArticleSet.articles.through.objects.bulk_create([
            ArticleSet.articles.through(articleset=asetart.articleset, article=art)
                for art in articles for asetart in articlesetarts
        ])

        dirty_sets |= ArticleSet.objects.filter(Q(project=project)|Q(projects_set=project)).filter(articles=article)

    if form_data["remove_from_sets"]:
        ArticleSet.articles.through.objects.filter(article=article, articleset=form_data["remove_from_sets"]).delete()
        dirty_sets |= ArticleSet.objects.filter(id__in=[aset.id for aset in form_data["remove_from_sets"]])
        
    if form_data["remove_from_all_sets"]:
        ArticleSet.articles.through.objects.filter(article=article, articleset__project=project).delete()
        dirty_sets |= ArticleSet.objects.filter(project=project, articles=article)

    if form_data["add_splitted_to_new_set"]:
        new_set = ArticleSet.create_set(project, form_data["add_splitted_to_new_set"], articles)

    dirty_sets.update(index_dirty=True)
    return render(request, "navigator/article/split-done.html", locals())

    
@check(Article, args_map={'article_id' : 'id'}, args='article_id')
@check(Project, args_map={'project_id' : 'id'}, args='project_id')
def split(request, project, article):
    sentences = article.sentences.all().only("sentence", "parnr")
    form = forms.SplitArticleForm(project, article, data=request.POST or None)

    if form.is_valid():
        # Check whether all selected sentences are really in this article
        sentence_ids = sentences.values_list("id", flat=True)
        selected_sentence_ids = set(get_sentence_ids(request.POST)) - {None,}
        if not all(sid in sentence_ids for sid in selected_sentence_ids):
            return HttpResponseBadRequest()

        if selected_sentence_ids:
            sentences = Sentence.objects.filter(id__in=selected_sentence_ids)
            return handle_split(request, form, project, article, sentences)

    sentences = _get_sentences(sentences)
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

