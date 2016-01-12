import json
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from amcat.models import Codebook
from amcat.tools import amcattest
from amcat.tools.amcattest import create_test_user


class TestCodebookViews(amcattest.AmCATTestCase):

    def setUp(self):
        if not User.objects.filter(username='amcat').exists():
            create_test_user(username='amcat', password='amcat')
        self.cb = amcattest.create_test_codebook()
        from django.test import Client
        self.client = Client()
        response = self.client.post('/accounts/login/', {'username': 'amcat', 'password': 'amcat'})
        self.assert_status(response, 302)

    def assert_status(self, response, expect=200):
        if response.status_code != expect:
            try:
                error = response.json()
            except:
                error = response.content
            self.fail("{response.status_code} Error on action:\n {error}".format(**locals()))

    def test_change_name(self):
        url = reverse("navigator:codebook-change-name", args=(self.cb.project_id, self.cb.id))
        response = self.client.post(url, {"codebook_name" : "bla"})
        self.assert_status(response)
        cb = Codebook.objects.get(pk=self.cb.id)
        self.assertEqual(cb.name, "bla")


    def test_save_changesets(self):
        # nog geen inhoudelijke test
        url = reverse("navigator:codebook-save-changesets", args=(self.cb.project_id, self.cb.id))
        data = {'moves' : json.dumps({"bla" : [1,2,{"meerbla" : "abc"}]})}
        #response = self.client.post(url, data)
        #self.assert_status(response)



    def test_save_labels(self):
        # nog geen inhoudelijke test
        url = reverse("navigator:codebook-save-labels", args=(self.cb.project_id, self.cb.id))
        data = {}
        #response = self.client.post(url, data)
        #self.assert_status(response)