from django.core.urlresolvers import reverse
from django.test import Client
from amcat.models import ArticleSet, Sentence, Article
from amcat.tools import amcattest, sbd
import navigator.forms
from navigator.views.article_views import ArticleSplitView, handle_split, get_articles


class TestSplitArticles(amcattest.AmCATTestCase):
    def create_test_sentences(self):
        article = amcattest.create_test_article(byline="foo", text="Dit is. Tekst.\n\n"*3 + "Einde.")
        sbd.create_sentences(article)
        return article, article.sentences.all()

    @amcattest.use_elastic
    def test_article_split_view(self):
        from amcat.models import Role, ProjectRole

        article, sentences = self.create_test_sentences()
        aset = amcattest.create_test_set(0)
        aset.add_articles([article])

        user = amcattest.create_test_user(username="fred", password="secret")
        ProjectRole.objects.create(user=user, project=aset.project, role=Role.objects.get(label="admin", projectlevel=True))

        # Only test the very basic; if a simple split works we trust the view
        # to use handle_split(), which is tested more extensively below.
        url = reverse("navigator:" + ArticleSplitView.get_view_name(), args=[aset.project.id, article.id])

        client = Client()
        client.login(username="fred", password="secret")

        response = client.post(url, {
            "add_to_new_set": "test_article_split_view_set",
            "remove_from_all_sets": "on",
            "add_splitted_to_new_set": "",
            "sentence-%s" % sentences[1].id: "on"
        })

        new_set = ArticleSet.objects.filter(name="test_article_split_view_set")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(new_set.exists())
        self.assertEqual(article, new_set[0].articles.all()[0])

    @amcattest.use_elastic
    def test_handle_split(self):
        from amcat.tools import amcattest
        from functools import partial

        article, sentences = self.create_test_sentences()
        project = amcattest.create_test_project()
        aset1 = amcattest.create_test_set(4, project=project)
        aset2 = amcattest.create_test_set(5, project=project)
        aset3 = amcattest.create_test_set(0)

        # Creates a codingjob for each articleset, as handle_split should account
        # for "codedarticlesets" as well.
        cj1 = amcattest.create_test_job(articleset=aset1)
        cj2 = amcattest.create_test_job(articleset=aset2)
        cj3 = amcattest.create_test_job(articleset=aset3)

        for _set in [aset1, aset2]:
            for _article in _set.articles.all():
                sbd.create_sentences(_article)

        a1, a2 = aset1.articles.all()[0], aset2.articles.all()[0]

        aset1.add_articles([article])
        aset3.add_articles([a1])

        form = partial(navigator.forms.SplitArticleForm, project, article, initial={
            "remove_from_sets": False
        })

        # Test form defaults (should do nothing!)
        f = form(dict())
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())

        self.assertEquals(5, aset1.articles.all().count())
        self.assertEquals(5, aset2.articles.all().count())
        self.assertEquals(1, aset3.articles.all().count())

        self.assertTrue(self.article_in(cj1, aset1, article))
        self.assertFalse(self.article_in(cj2, aset2, article))
        self.assertFalse(self.article_in(cj3, aset3, article))

        # Passing invalid form should raise exception
        f = form(dict(add_to_sets=[-1]))
        self.assertFalse(f.is_valid())
        self.assertRaises(ValueError, handle_split, f, project, article, Sentence.objects.none())

        # Test add_to_new_set
        f = form(dict(add_to_new_set="New Set 1"))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())
        aset = project.all_articlesets().filter(name="New Set 1")
        self.assertTrue(aset.exists())
        self.assertEquals(project, aset[0].project)

        # Test add_to_sets
        f = form(dict(add_to_sets=[aset3.id]))
        self.assertFalse(f.is_valid())
        f = form(dict(add_to_sets=[aset2.id]))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())
        self.assertTrue(self.article_in(cj2, aset2, article))

        # Test add_splitted_to_new_set
        f = form(dict(add_splitted_to_new_set="New Set 2"))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())
        aset = project.all_articlesets().filter(name="New Set 2")
        self.assertTrue(aset.exists())
        self.assertEquals(project, aset[0].project)
        self.assertEquals(1, aset[0].articles.count())
        self.assertFalse(self.article_in(None, aset[0], article))

        # Test add_splitted_to_sets
        f = form(dict(add_splitted_to_sets=[aset2.id]))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())
        self.assertTrue(article in aset2.articles.all())

        # Test remove_from_sets
        f = form(dict(remove_from_sets=[aset1.id]))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())
        self.assertTrue(article not in aset1.articles.all())

        # Test remove_from_all_sets
        aset1.add_articles([article])
        aset2.add_articles([article])
        aset3.add_articles([article])

        f = form(dict(remove_from_all_sets=True))
        self.assertTrue(f.is_valid())
        handle_split(f, project, article, Sentence.objects.none())

        self.assertTrue(aset1 in project.all_articlesets())
        self.assertTrue(aset2 in project.all_articlesets())
        self.assertFalse(aset3 in project.all_articlesets())

        self.assertFalse(self.article_in(cj1, aset1, article))
        self.assertFalse(self.article_in(cj2, aset2, article))
        self.assertTrue(self.article_in(cj3, aset3, article))



    def article_in(self, codingjob, articleset, article):
        from amcat.tools.amcates import ES
        ES().flush()

        if codingjob is not None:
            if not codingjob.coded_articles.filter(article=article):
                return False

        return article.id in (articleset.get_article_ids() | articleset.get_article_ids(use_elastic=True))


class TestArticleViews(amcattest.AmCATTestCase):
    def create_test_sentences(self):
        article = amcattest.create_test_article(byline="foo", text="Dit is. Tekst.\n\n"*3 + "Einde.")
        sbd.create_sentences(article)
        return article, article.sentences.all()

    @amcattest.use_elastic
    def test_get_articles(self):
        from amcat.models import Sentence
        _get_articles = lambda a,s : list(get_articles(a,s))

        # Should raise exception if sentences not in article
        article, sentences = self.create_test_sentences()
        s1 = Sentence.objects.filter(id=amcattest.create_test_sentence().id)
        self.assertRaises(ValueError, _get_articles, article, s1)

        # Should raise an exception if we try to split on headline
        self.assertRaises(ValueError, _get_articles, article, sentences.filter(parnr=1))

        # Should return a "copy", with byline in "text" property
        arts = _get_articles(article, Sentence.objects.none())
        Article.create_articles(arts)

        self.assertEquals(len(arts), 1)
        sbd.create_sentences(arts[0])

        self.assertEquals(
            [s.sentence for s in sentences[1:]],
            [s.sentence for s in arts[0].sentences.all()[1:]]
        )

        self.assertTrue("foo" in arts[0].text)

        # Should be able to split on byline
        self.assertEquals(2, len(_get_articles(article, sentences[1:2])))
        a, b = _get_articles(article, sentences[4:5])

        # Check if text on splitted articles contains expected
        self.assertTrue("Einde" not in a.text)
        self.assertTrue("Einde" in b.text)