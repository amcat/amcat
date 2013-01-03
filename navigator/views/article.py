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
from django.shortcuts import render
from django.conf import settings

from settings.menu import PROJECT_MENU

from amcat.tools import toolkit
from amcat.models.article import Article
from amcat.models.project import Project
from amcat.models.articleset import ArticleSet

from navigator.utils.auth import check, check_perm
from navigator import forms

from amcat.scripts import article_upload as article_upload_scripts

import logging; log = logging.getLogger(__name__)

@check(Article)
def view(request, art, projectid=None):
    ctx = dict(article=art)

    if projectid is not None:
        ctx['menu'] = PROJECT_MENU
        ctx['context'] = Project.objects.get(id=projectid)
    
    return render(request, "navigator/article/view.html", ctx)


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

