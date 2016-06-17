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
import json

from amcat.models import Article
from amcat.tools import amcattest
from api5.view import QuerySetAPIView
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory


class HeadersDict(dict):
    def __getitem__(self, item: str):
        header, value = super().get(item.lower())
        return value

    def __repr__(self):
        case_sensitive_dict = {super(HeadersDict, self).__getitem__(k.lower())[0]: self[k] for k in self.keys()}
        return "<HeadersDict({})>".format(repr(case_sensitive_dict))


class SimpleQuerySetAPIView(QuerySetAPIView):
    model = Article
    filters = ()


class FilteredQuerySetAPIView(QuerySetAPIView):
    model = Article


class TestQuerySetAPIView(amcattest.AmCATTestCase):
    view = None

    def _get(self, url):
        request = RequestFactory().get(url)
        request.user = AnonymousUser()
        result = self.view.as_view()(request)

        if hasattr(result, "streaming_content"):
            bytes = b"".join(result.streaming_content)
        else:
            bytes = result.content

        try:
            return result, HeadersDict(result._headers), json.loads(bytes.decode())
        except ValueError:
            return result, HeadersDict(result._headers), bytes.decode()


class TestSimpleQuerySetAPIView(TestQuerySetAPIView):
    view = SimpleQuerySetAPIView

    def test_illegal_filter(self):
        response, headers, value = self._get("/?foo=bar")
        self.assertEqual(value, {
            "type": "known",
            "error": "Did not recognize filter: 'foo'"
        })

    def test_multiple_queries(self):
        response, headers, value = self._get("/?_format=json&_format=xls")
        self.assertEqual(value["type"], "known")
        self.assertEqual(value["error"], "Param '_format' was given multiple times. This is ambiguous. Bug?")

    def test_unkown_parameter(self):
        response, headers, value = self._get("/?_foo=bar")
        self.assertEqual(value["type"], "known")
        self.assertEqual(value["error"], "Did not recognize parameter(s): '_foo'")

    def test_include(self):
        amcattest.create_test_set(1)
        response, headers, articles = self._get("/?_include=headline")

        self.assertEqual(
            Article.objects.first().headline,
            articles[0]["headline"]
        )

    def test_exclude(self):
        amcattest.create_test_set(1)
        response, headers, articles = self._get("/?_exclude=text")

        self.assertEqual(sorted(articles[0].keys()), sorted([
            'url', 'byline', 'medium', 'length', 'parent', 'id', 'externalid',
            'headline', 'uuid', 'date', 'section', 'author', 'addressee',
            'project', 'metastring', 'pagenr', 'insertdate', 'insertscript'
        ]))


class TestFilteredQuerySetAPIView(TestQuerySetAPIView):
    view = FilteredQuerySetAPIView

    def test_pk_filter(self):
        amcattest.create_test_set(2)

        self.assertEqual(2, Article.objects.all().count())
        first_article = Article.objects.all().first()
        url = "/?pk={}".format(first_article.id)
        response, headers, articles = self._get(url)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["id"], first_article.id)
