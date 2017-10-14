from tempfile import NamedTemporaryFile
from typing import Mapping

from django.core.urlresolvers import reverse
from django.test import Client
from django.views.generic import View

from amcat.models import ROLE_PROJECT_METAREADER, ROLE_PROJECT_WRITER, ROLE_PROJECT_READER, ProjectRole, \
    LITTER_PROJECT_ID, UploadedFile
from amcat.tools import amcattest


class ProjectPermissionsTestCase(amcattest.AmCATTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.order = ["noaccess", "readmeta", "read", "write", "admin"]
        cls.users = {k: amcattest.create_test_user(username="testuser-{}".format(k)) for k in cls.order}
        cls.clients = {} #type: Mapping[str, Client]
        for k, v in cls.users.items():
            client = Client()
            client.login(username=v.username, password="test")
            cls.clients[k] = client
        cls.litter = amcattest.create_test_project(id=LITTER_PROJECT_ID, owner=cls.users["admin"], guest_role=None)
        cls.project = amcattest.create_test_project(name="permission-project", owner=cls.users["admin"], guest_role=None)
        cls.articleset = amcattest.create_test_set(articles=5, project=cls.project)
        cls.article = cls.articleset.articles.all()[0]

        cls.alt_project = amcattest.create_test_project(name="alt-permission-project", guest_role_id=ROLE_PROJECT_METAREADER)
        cls.alt_articleset = amcattest.create_test_set(articles=5, project=cls.alt_project)
        cls.alt_article = cls.alt_articleset.articles.all()[0]
        cls.articleset.add_articles([art.id for art in cls.alt_articleset.articles.all()])

        ProjectRole.objects.create(project=cls.project, user=cls.users["readmeta"], role_id=ROLE_PROJECT_METAREADER)
        ProjectRole.objects.create(project=cls.project, user=cls.users["read"], role_id=ROLE_PROJECT_READER)
        ProjectRole.objects.create(project=cls.project, user=cls.users["write"], role_id=ROLE_PROJECT_WRITER)

    def _test_generic(self, method, fail_role, success_role, url):
        """Test if access is denied on role `fail_role`, and given for role `success_role`."""
        get = self.clients[fail_role].generic(method, url)
        self.assertEqual(get.status_code, 403, "Permission not denied for role '{}'. Expected minimum required role '{}'.".format(fail_role, success_role))
        get = self.clients[success_role].generic(method, url)
        self.assertNotEqual(get.status_code, 403, "Permission denied for role '{}'".format(success_role))

    def _test_get_readmeta_access(self, url):
        self._test_generic("GET", "noaccess", "readmeta", url)

    def _test_delete_write_access(self, url):
        self._test_generic("DELETE", "read", "write", url)

    def _test_get_read_access(self, url):
        self._test_generic("GET", "readmeta", "read", url)

    def _test_get_write_access(self, url):
        self._test_generic("GET", "read", "write", url)

    def _test_post_write_access(self, url):
        self._test_generic("POST", "read", "write", url)

    def _test_get_post_write_access(self, url):
        self._test_get_write_access(url)
        self._test_post_write_access(url)

class TestViewPermissions(ProjectPermissionsTestCase):
    def test_article_views(self):
        self._test_get_readmeta_access(reverse("navigator:article-details", args=[self.project.id, self.articleset.id, self.article.id]))
        self._test_get_readmeta_access(reverse("navigator:project-article-details", args=[self.project.id, self.article.id]))

        # let writer remove article from the set that originates from another project. writer has metareader access in alt_project.
        rm_art_url = "{}?remove_set={}".format(reverse("navigator:article-removefromset", args=[self.alt_project.id, self.alt_article.id]), self.articleset.id)
        self._test_get_write_access(rm_art_url)
        self._test_get_post_write_access(reverse("navigator:article-split", args=[self.project.id, self.article.id]))


    def test_articleupload_views(self):
        from amcat.scripts.article_upload.tests.test_upload import create_test_upload
        self._test_get_post_write_access(reverse("navigator:uploadedfile-list", args=[self.project.id]))
        self._test_get_post_write_access(reverse("navigator:uploadedfile-add", args=[self.project.id]))
        with NamedTemporaryFile() as fo:
            upl = create_test_upload(fo)
        self._test_get_post_write_access(reverse("navigator:articleset-upload", args=[self.project.id, upl.id]))
        self._test_get_post_write_access(reverse("navigator:articleset-upload-options", args=[self.project.id, upl.id]))


    def test_articleset_crud_views(self):
        self._test_get_readmeta_access(reverse("navigator:articleset-list", args=[self.project.id]))
        self._test_get_readmeta_access(reverse("navigator:articleset-details", args=[self.project.id, self.articleset.id]))
        self._test_delete_write_access(reverse("navigator:articleset-details", args=[self.project.id, self.articleset.id]))
        self._test_post_write_access(reverse("navigator:articleset-details", args=[self.project.id, self.articleset.id]))
        self._test_get_post_write_access(reverse("navigator:articleset-create", args=[self.project.id]))
        self._test_get_post_write_access(reverse("navigator:articleset-edit", args=[self.project.id, self.articleset.id]))
        self._test_get_post_write_access(reverse("navigator:articleset-delete", args=[self.project.id, self.articleset.id]))

    def test_articleset_action_views(self):
        self._test_get_post_write_access(reverse("navigator:articleset-deduplicate", args=[self.project.id, self.articleset.id]))
        self._test_get_post_write_access(reverse("navigator:articleset-import", args=[self.project.id, self.articleset.id]))
        self._test_get_post_write_access(reverse("navigator:articleset-sample", args=[self.project.id, self.articleset.id]))
        self._test_get_post_write_access(reverse("navigator:articleset-refresh", args=[self.project.id, self.articleset.id]))
        self._test_get_post_write_access(reverse("navigator:articleset-unlink", args=[self.project.id, self.articleset.id]))

    def test_codebook_views(self):
        codebook = amcattest.create_test_codebook(project=self.project)

        self._test_get_post_write_access(reverse("navigator:codebook-import", args=[self.project.id]))
        self._test_get_post_write_access(reverse("navigator:codebook-link", args=[self.project.id]))
        self._test_get_post_write_access(reverse("navigator:codebook-delete", args=[self.project.id, codebook.id]))
        self._test_get_post_write_access(reverse("navigator:codebook-change-name", args=[self.project.id, codebook.id]))

    # todo: codingschema tests

    def test_project_views(self):
        self._test_get_readmeta_access(reverse("navigator:project-details", args=[self.project.id]))
        self._test_post_write_access(reverse("navigator:project-details", args=[self.project.id]))
