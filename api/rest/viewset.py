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
To make specifying viewsets less tedious and repetitive an extra property
`model_key` is introduced, which can be defined on a ModelViewSetMixin. A
ViewSet can then inherit from mixins, which can be used to automatically
generate an url pattern. This eliminates the need for writing them manually
and multiple times for viewsets with the same model, but a different scope.
"""

__all__ = ("AmCATViewSetMixin", "get_url_pattern", "AmCATViewSetMixinTest")

from collections import OrderedDict, namedtuple
from . import tablerenderer

ModelKey = namedtuple("ModelKey", ("key", "viewset"))


class AmCATViewSetMixin(object):
    """
    All ViewSet used in the AmCAT API should inherit from this class, or at least
    define a classmethod get_url_pattern(), which returns the pattern for the
    mixin. A default implementation is given for this superclass.
    """
    model_key = None
    ordering_fields = ("id",)

    def __init__(self, *args, **kwargs):
        super(AmCATViewSetMixin, self).__init__(*args, **kwargs)

        # TODO: Remove this hack. Djangorestframework uses serializer_class to determine
        # TODO: the fields a resource has, but does not bother to call get_serializer_class,
        # TODO: resulting in errors.
        if self.serializer_class is None:
            self.serializer_class = self.get_serializer_class()

    def __getattr__(self, item):
        checked = []
        for model_key, viewset in self._get_model_keys():
            checked.append(model_key)
            if model_key is item:
                return viewset.model.objects.get(pk=self.kwargs.get(model_key, self.kwargs.get("pk")))
        raise AttributeError("Cannot find attribute {item} in keys {checked}".format(**locals()))

    @classmethod
    def get_url_pattern(cls):
        """
        Get an url pattern (ready to be inserted in urlpatterns()) for `viewset`.

        @type cls: must inherit from at least one AmCATViewSetMixin
        @rtype: string
        """
        return "/".join(cls._get_url_pattern())

    @classmethod
    def get_basename(cls):
        return getattr(cls, "base_name", None)

    def finalize_response(self, request, response, *args, **kargs):
        response = super(AmCATViewSetMixin, self).finalize_response(request, response, *args, **kargs)
        response = tablerenderer.set_response_content(response)
        return response
    
    @classmethod    
    def _get_model_keys(cls):
        """
        Get an iterator of all model_key properties in superclasses. This function
        yields an ordered list, working up the inheritance tree according to Pythons
        MRO algorithm.

        @rtype: ModelKey
        """
        model_key = getattr(cls, "model_key", None)
        if model_key is None:
            return

        for base in cls.__bases__:
            if not hasattr(base, '_get_model_keys'): continue
            for basekey in base._get_model_keys():
                yield basekey

        yield ModelKey(model_key, cls)

    @classmethod
    def _get_url_pattern_listname(cls):
        return r"{model_key}s"
        
    @classmethod
    def _get_url_pattern(cls):
        # Deduplicate (while keeping ordering) with OrderedDict
        model_keys = (mk.key for mk in cls._get_model_keys())
        model_keys = tuple(OrderedDict.fromkeys(model_keys))

        for model_key in model_keys[:-1]:
            yield r"{model_key}s/(?P<{model_key}>\d+)".format(**locals())
        yield r"{model_key}s".format(model_key=model_keys[-1])


######################
##### UNIT TESTS #####
######################
from amcat.tools import amcattest
from django.test import Client
import json

class AmCATViewSetMixinTest(amcattest.AmCATTestCase):
    def test_get_url_pattern(self):
        class AMixin(AmCATViewSetMixin):
            model_key = "project"

        class BMixin(AmCATViewSetMixin):
            model_key = "codebook"

        class CMixin(BMixin):
            pass

        class AViewSet(AMixin, BMixin): pass
        class BViewSet(AMixin, CMixin): pass
        class CViewSet(BMixin, AMixin): pass
            
        self.assertEquals(r"projects", AMixin.get_url_pattern())
        self.assertEquals(r"codebooks", BMixin.get_url_pattern())
        self.assertEquals(r"projects/(?P<project>\d+)/codebooks", AViewSet.get_url_pattern())
        self.assertEquals(r"projects/(?P<project>\d+)/codebooks", BViewSet.get_url_pattern())
        self.assertEquals(r"codebooks/(?P<codebook>\d+)/projects", CViewSet.get_url_pattern())


class TestSearchViewSetMixin(amcattest.AmCATTestCase):
    def setUp(self):
        project = amcattest.create_test_project()
        amcattest.create_test_set(name="foo", project=project)
        amcattest.create_test_set(name="bar", project=project)

        self.url = "/api/v4/projects/{project.id}/articlesets/?format=json"
        self.url = self.url.format(**locals())

    def _get_json(self, url):
        c = Client()
        return json.loads(c.get(url).content)

    def test_basic(self):
        # No search parameter
        results = self._get_json(self.url)
        self.assertEqual(2, results['total'])

        # Foo parameter
        results = self._get_json(self.url + "&search=foo")
        self.assertEqual(1, results['total'])
        self.assertEqual("foo", results["results"][0]["name"])

        # Bar paramter
        results = self._get_json(self.url + "&search=bar")
        self.assertEqual(1, results['total'])
        self.assertEqual("bar", results["results"][0]["name"])

    def test_case_insensitivity(self):
        results = self._get_json(self.url + "&search=BaR")
        self.assertEqual(1, results['total'])
        self.assertEqual("bar", results["results"][0]["name"])

    def test_partial(self):
        results = self._get_json(self.url + "&search=fo")
        self.assertEqual(1, results['total'])
        self.assertEqual("foo", results["results"][0]["name"])

        results = self._get_json(self.url + "&search=oo")
        self.assertEqual(1, results['total'])
        self.assertEqual("foo", results["results"][0]["name"])

        results = self._get_json(self.url + "&search=a")
        self.assertEqual(1, results['total'])
        self.assertEqual("bar", results["results"][0]["name"])