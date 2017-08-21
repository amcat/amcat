###########################################################################
# (C) Vrije Universiteit, Amsterdam (the Netherlands)                     #
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
Model module representing codebook Codes and Labels

A Code is a concept that can be found in a text, e.g. an actor, issue, etc. 
Codes can have multiple labels in different languages, and they can 
be included in different Codebooks.
"""

from __future__ import unicode_literals, print_function, absolute_import
import logging

log = logging.getLogger(__name__)

from django.db import models

from amcat.tools.model import AmcatModel, PostgresNativeUUIDField
from amcat.models.language import Language

PARTYMEMBER_FUNCTIONID = 0


class Code(AmcatModel):
    """
    Model class for table codes
    
    @property _labelcache: is a dictionary mapping a languageid to a label (string)
    @property _all_labels_cached: can be set to True by a caller to indicate all
                existing labels are cached. This prevents get_label with fallback=True
                from quering the database, if no label is found in cache.

    """

    id = models.AutoField(primary_key=True, db_column='code_id')
    label = models.TextField(blank=False, null=False)
    uuid = PostgresNativeUUIDField(db_index=True, unique=True)

    class Meta():
        db_table = 'codes'
        app_label = 'amcat'


    def __init__(self, *args, **kargs):
        super(Code, self).__init__(*args, **kargs)
        self._labelcache = {}
        self._all_labels_cached = False

    def natural_key(self):
        return (unicode(self.uuid), )
        
    def get_label(self, language):
        """Get the label (string) for the given language object, or raise label.DoesNotExist"""
        if type(language) != int: language = language.id
        try:
            lbl = self._labelcache[language]
            if lbl is None: raise Label.DoesNotExist()
            return lbl
        except KeyError:
            if self._all_labels_cached:
                raise Label.DoesNotExist()

            try:
                lbl = self.labels.get(language=language).label
                self._labelcache[language] = lbl
                return lbl
            except Label.DoesNotExist:
                self._labelcache[language] = None
                raise

    def label_is_cached(self, language):
        if type(language) != int: language = language.id
        return language in self._labelcache

    def add_label(self, language, label, replace=True):
        """
        Add the label in the given language
        @param replace: if this code already has a label in that language, replace it?
        """
        if isinstance(language, int):
            language = Language.objects.get(pk=language)
        try:
            l = Label.objects.get(code=self, language=language)
            if replace:
                l.label = label
                l.save()
            else:
                raise ValueError("Code {self} already has label in language {language} and replace is set to False"
                                 .format(**locals()))
        except Label.DoesNotExist:
            Label.objects.create(language=language, label=label, code=self)
        self._cache_label(language, label)

    def _cache_label(self, language, label):
        """Cache the given label (string) for the given language object"""
        if type(language) != int: language = language.id
        self._labelcache[language] = label

    @classmethod
    def create(cls, label, language):
        code = cls.objects.create()
        Label.objects.create(label=label, language=language, code=code)
        return code


class Label(AmcatModel):
    """Model class for table labels. Essentially a many-to-many relation
    between codes and langauges with a label attribute"""

    id = models.AutoField(primary_key=True, db_column='label_id')
    label = models.TextField(blank=False, null=False)

    code = models.ForeignKey(Code, db_index=True, related_name="labels")
    language = models.ForeignKey(Language, db_index=True, related_name="labels")

    class Meta():
        db_table = 'codes_labels'
        app_label = 'amcat'
        unique_together = ('code', 'language')
        ordering = ("language__id",)

    def natural_key(self):
        return self.code.natural_key() + self.language.natural_key()
