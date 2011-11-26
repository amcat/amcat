# -*- coding: utf-8 -*-
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

"""
This module contains a (semi-machine readable) lexisnexis parser.
"""

from __future__ import unicode_literals

from django import forms

from amcat.scripts import script
from amcat.scripts.types  import ArticleIterator
from amcat.tools import toolkit

from amcat.model.article import Article
from amcat.model.medium import Medium

class TextForm(forms.Form):
    medium = forms.ModelChoiceField(queryset=Medium.objects.all())
    headline = forms.CharField()
    date = forms.DateField()

class Text(script.Script):
    input_type = unicode
    output_type = ArticleIterator
    options_form = TextForm

    def run(self, input):
        return (Article(text=input, **self.options),)
