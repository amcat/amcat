import json

from django.core.cache import cache
from django.core.urlresolvers import reverse
from rest_framework.test import APITestCase

from amcat.tools import amcattest
from amcat.tools.amcates import ES
from amcat.tools.amcattest import use_elastic, clear_cache


class TestTokens(APITestCase):

    @use_elastic
    @clear_cache
    def test_estoken(self):
        aset = amcattest.create_test_set()
        a1 = amcattest.create_test_article(title="dit is de titel", text="En dit, dit is de tekst",
                                          articleset=aset, project=aset.project)
        a2 = amcattest.create_test_article(title="dit is nog een kop", text="Van je een, van je twee, van je drie!",
                                          articleset=aset, project=aset.project)

        ES().refresh()
        #     url(r'^projects/(?P<project_id>[0-9]+)/articlesets/(?P<articleset_id>[0-9]+)/tokens/?$', TokensView.as_view(), name="tokens"),

        url = reverse("api:tokens", kwargs=dict(project_id=aset.project.id, articleset_id=aset.id)) + "?format=json"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        tokens = json.loads(r.content.decode(r.charset))['results']

        words1 = " ".join(t["word"] for t in tokens if t['id'] == a1.id)
        words2 = " ".join(t["word"] for t in tokens if t['id'] == a2.id)

        self.assertEqual(words1, "dit is de titel en dit dit is de tekst")
        self.assertEqual(words2, "dit is nog een kop van je een van je twee van je drie")
