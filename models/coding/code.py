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
Model module representing codebook Codes and Labels

A Code is a concept that can be found in a text, e.g. an actor, issue, etc. 
Codes can have multiple labels in different languages, and they can 
be included in different Codebooks.
"""

from __future__ import unicode_literals, print_function, absolute_import
import logging; log = logging.getLogger(__name__)

from django.db import models

from amcat.tools.model import AmcatModel
from amcat.models.language import Language

PARTYMEMBER_FUNCTIONID = 0

class Code(AmcatModel):
    """Model class for table codes"""

    id = models.AutoField(primary_key=True, db_column='code_id')
    
    class Meta():
        db_table = 'codes'
        app_label = 'amcat'


    def __init__(self, *args, **kargs):
        super(Code, self).__init__(*args, **kargs)
        self._labelcache = {}
        
    @property
    def label(self):
        """Get the (cached) label with the lowest language id, or a repr-like string"""
        repr_like_string = '<{0.__class__.__name__}: {0.id}>'.format(self)
        if self._labelcache:
            key = sorted(self._labelcache)[0]
            l = self.get_label(key)
            if l == None:
               return repr_like_string
            return l
        try:
            return self.labels.all().order_by('language__id')[0].label
        except IndexError:
            return repr_like_string
        
    def _get_label(self, language):
        """Get the label (string) for the given language object, or raise label.DoesNotExist"""
        if type(language) != int: language = language.id
        try:
            lbl = self._labelcache[language]
            if lbl is None: raise Label.DoesNotExist()
            return lbl
        except KeyError:
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
            
    def get_label(self, *languages, **kargs):
        """
        @param lan: language to get label for
        @type lan: Language object or int
        @param fallback: If True, return another label if language not found
        @return: string or None
        """
        for lan in languages:
            try:
                return self._get_label(language=lan)
            except Label.DoesNotExist:
                pass

        fallback = kargs.get("fallback", True)
        if fallback:
            try:
                return self.labels.all().order_by('language__id')[0].label
            except IndexError:
                pass

    def add_label(self, language, label):
        """Add the label in the given language"""
	if isinstance(language, int):
	    language = Language.objects.get(pk=language)
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
    language = models.ForeignKey(Language, db_index=True, related_name="+")

    class Meta():
        db_table = 'codes_labels'
        app_label = 'amcat'
        unique_together = ('code','language')
        ordering = ("language__id",)


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCode(amcattest.PolicyTestCase):
    PYLINT_IGNORE_EXTRA = 'W0212', #  'protected' member access
    
    def test_label(self):
        """Can we create objects and assign labels?"""
        # simple label
        o = amcattest.create_test_code(label="bla")
        self.assertEqual(o.label, "bla")
        self.assertEqual(unicode(o), o.label)
        # fallback with 'unknown' language
        l2 = Language.objects.create(label='zzz')
        self.assertEqual(o.get_label(l2), "bla")
        # second label
        o.add_label(l2, "blx")
        self.assertEqual(o.get_label(l2), "blx")
        self.assertEqual(o.get_label(Language.objects.create()), "bla")
        self.assertEqual(o.label, "bla")

        # does .label return something sensible on objects without labels?
        o2 = Code.objects.create()
        self.assertIsInstance(o2.label, unicode)
        self.assertRegexpMatches(o2.label, r'^<Code: \d+>$')
        self.assertIsNone(o2.get_label(l2))

        # does .label and .get_label return a unicode object under all circumstances
        self.assertIsInstance(o.label, unicode)
        self.assertIsInstance(o.get_label(l2), unicode)
        self.assertIsInstance(o2.label, unicode)

    def test_cache(self):
        """Are label lookups cached?"""
        l = Language.objects.create(label='zzz')
        o = amcattest.create_test_code(label="bla", language=l)
        with self.checkMaxQueries(0, "Get cached label"):
            self.assertEqual(o.get_label(l), "bla")
        o = Code.objects.get(pk=o.id)
        with self.checkMaxQueries(1, "Get new label"):
            self.assertEqual(o.get_label(l), "bla")
        with self.checkMaxQueries(0, "Get cached label"):
            self.assertEqual(o.get_label(l), "bla")
        o = Code.objects.get(pk=o.id)
        o._cache_label(l, "onzin")
        with self.checkMaxQueries(0, "Get manually cached label"):
            self.assertEqual(o.get_label(l), "onzin")
            
            
