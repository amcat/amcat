import datetime
from amcat.models import Language
from amcat.scripts.forms.selection import DAY_DELTA, SelectionForm
from amcat.tools import amcattest
from amcat.tools.toolkit import to_datetime


class TestSelectionForm(amcattest.AmCATTestCase):
    def get_form(self, **kwargs):
        codebook = None

        if "project" in kwargs:
            project = kwargs.pop("project")
        else:
            codebook = amcattest.create_test_codebook_with_codes()[0]
            project = codebook.project

        return project, codebook, SelectionForm(project, data=kwargs)

    def test_hash(self):
        aset1 = amcattest.create_test_set(2)
        aset2 = amcattest.create_test_set(2, project=aset1.project)
        project = aset1.project
        _, _, form1 = self.get_form(
            project=project,
            articlesets=[aset1.id, aset2.id],
            article_ids="1\n2\n3",
            query="abc\ndefg"
        )

        _, _, form2 = self.get_form(
            project=project,
            articlesets=[aset2.id, aset1.id],
            article_ids="1\n3\n2",
            query="abc\ndifferent\nquery"
        )

        form1.full_clean()
        form2.full_clean()

        self.assertEqual(
            form1.get_hash(ignore_fields=("query",)),
            form2.get_hash(ignore_fields=("query",))
        )

        self.assertNotEqual(
            form1.get_hash(),
            form2.get_hash()
        )

    def test_date_formats(self):
        dates = (
            "2006-10-25", "2006/10/25", "25-10-2006", "25/10/2006",
            "Oct 25 2006", "Oct 25, 2006", "25 Oct 2006", "25 Oct, 2006",
            "October 25 2006", "October 25, 2006", "25 October 2006",
            "25 October, 2006"
        )

        project = amcattest.create_test_project()

        for date in dates:
            form = SelectionForm(data={"start_date":date}, project=project)
            form.full_clean()
            self.assertFormValid(form, "Date: {}".format(repr(date)))
            self.assertEqual(datetime.date(2006, 10, 25), form.cleaned_data["start_date"].date())

        for date in dates:
            form = SelectionForm(data={"on_date":date, "datetype": "on"}, project=project)
            form.full_clean()
            self.assertFormValid(form, "Date: {}".format(repr(date)))
            self.assertEqual(datetime.date(2006, 10, 25), form.cleaned_data["start_date"].date())
            self.assertEqual(datetime.date(2006, 10, 25), form.cleaned_data["end_date"].date())

        for date in dates:
            form = SelectionForm(data={"end_date":date}, project=project)
            form.full_clean()
            self.assertFormValid(form, "Date: {}".format(repr(date)))
            self.assertEqual(datetime.date(2006, 10, 25), form.cleaned_data["end_date"].date())

    def assertFormValid(self, form, msg):
        if not form.is_valid():
            stdmsg = "Form errors: {}".format(form.errors.as_data())
            msg = self._formatMessage(msg, stdmsg)
            raise self.failureException(msg)

    @amcattest.use_elastic
    def test_clean_article_ids(self):
        p, _, form = self.get_form()
        aset = amcattest.create_test_set(1)
        article = aset.articles.all()[0]
        p.articlesets.add(aset)

        self.assertTrue(form.is_valid())
        _, _, form = self.get_form(project=p, article_ids=str(article.id))
        self.assertTrue(form.is_valid())
        _, _, form = self.get_form(project=p, article_ids=str(article.id + 1))
        self.assertTrue(form.is_valid())

        article2 = amcattest.create_test_set(1).articles.all()[0]
        _, _, form = self.get_form(project=p, article_ids=str(article2.id))
        self.assertFalse(form.is_valid())


    def test_field_ordering(self):
        """Test if fields are defined in correct order (imported for
        *_clean methods on form."""
        orders = (
            ("start_date", "end_date", "datetype", "on_date"),
            ("include_all", "articlesets", "query"),
            ("codebook_replacement_language", "codebook_label_language", "codebook"),
            ("articlesets", "article_ids")
        )

        for order in orders:
            fields = [SelectionForm.base_fields[f].creation_counter for f in order]
            self.assertEquals(sorted(fields), fields)

    @amcattest.use_elastic
    def test_clean_on_date(self):
        now = datetime.datetime.now().date()
        p, c, form = self.get_form(datetype="on", on_date=now)

        self.assertTrue(form.is_valid())

        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]

        self.assertEquals(form.cleaned_data["datetype"], "between")
        self.assertEquals(form.cleaned_data["start_date"], to_datetime(now))
        self.assertEquals(end_date - start_date, DAY_DELTA)
        self.assertTrue(end_date != start_date)

        p, c, form = self.get_form(datetype="on")
        self.assertFalse(form.is_valid())


    @amcattest.use_elastic
    def test_clean_datetype(self):
        now = datetime.datetime.now().date()

        # Test 'between'
        p, c, form = self.get_form(datetype="between")
        self.assertFalse(form.is_valid())
        p, c, form = self.get_form(datetype="between", start_date=now)
        self.assertFalse(form.is_valid())
        p, c, form = self.get_form(datetype="between", end_date=now)
        self.assertFalse(form.is_valid())
        p, c, form = self.get_form(datetype="between", end_date=now, start_date=now)
        self.assertFalse(form.is_valid())
        p, c, form = self.get_form(datetype="between", end_date=now - datetime.timedelta(days=1), start_date=now)
        self.assertFalse(form.is_valid())
        p, c, form = self.get_form(datetype="between", end_date=now + datetime.timedelta(days=1), start_date=now)
        self.assertTrue(form.is_valid())

        # Test 'after'
        p, c, form = self.get_form(datetype="after")
        self.assertFalse(form.is_valid())
        p, c, form = self.get_form(datetype="after", end_date=now)
        self.assertFalse(form.is_valid())
        p, c, form = self.get_form(datetype="after", start_date=now)
        self.assertTrue(form.is_valid())

        # Test 'before'
        p, c, form = self.get_form(datetype="before")
        self.assertFalse(form.is_valid())
        p, c, form = self.get_form(datetype="before", start_date=now)
        self.assertFalse(form.is_valid())
        p, c, form = self.get_form(datetype="before", end_date=now)
        self.assertTrue(form.is_valid())


    @amcattest.skip_TODO("moved functionality to keywordsearch, move tests there as well")
    def test_clean_query(self):
        import functools

        p, c, form = self.get_form(query="  Bla   #  Balkenende")
        self.assertTrue(form.is_valid())
        self.assertEquals(len(list(form.queries)), 1)
        self.assertEquals(next(form.queries).declared_label, "Bla")
        self.assertEquals(next(form.queries).query, "Balkenende")

        # clean_query should ignore whitespace / tabs
        p, c, form = self.get_form(query="Bla#Balkenende\n\t\nBla2#Balkie")
        self.assertTrue(form.is_valid())
        self.assertEquals(len(list(form.queries)), 2)

        # Label can't be defined twice
        p, c, form = self.get_form(query="Bla#Balkenende\nBla#Balkie")
        self.assertFalse(form.is_valid())

        p, c, form = self.get_form(query="Bla#Balkenende\nBla#Balkie")

        code = c.get_codes()[0]
        lan0 = code.labels.all()[0].language
        lan1 = Language.objects.create(label="lan1")
        lan2 = Language.objects.create(label="lan2")
        code.add_label(lan1, "Referral")
        code.add_label(lan2, "Replacement")

        _form = functools.partial(self.get_form,
                                  codebook=c.id, codebook_label_language=lan1.id,
                                  codebook_replacement_language=lan2.id, project=p
        )

        p, _, form = _form(query="<Referral>")
        self.assertTrue(form.is_valid())
        self.assertTrue("Replacement" in form.keyword_query)

        # Shouldn't crash at multiple (same) referals
        p, _, form = _form(query="<Referral>_<Referral>")
        self.assertTrue(form.is_valid())
        self.assertTrue("Replacement_Replacement" in form.keyword_query)

        _form = functools.partial(
            _form, codebook_label_language=lan0.id,
            codebook_replacement_language=lan0.id
        )

        root = next(c for c in c.get_codes() if c.get_label(lan0.id) == "A")


        # Should be able to handle recursion when defined on label
        p, _, form = _form(query="<{}+>".format(root.get_label(lan0.id)))
        self.assertTrue(form.is_valid())
        self.assertEquals(3, form.keyword_query.count("("))  # Three levels of nesting
        for label in ["A", "A2", "A1", "A1b", "A1a"]:
            self.assertTrue(label in form.keyword_query)

        # Should be able to handle recursion when defined on id
        p, _, form = _form(query="<{}+>".format(root.id))
        self.assertTrue(form.is_valid())
        self.assertEquals(3, form.keyword_query.count("("))  # Three levels of nesting
        for label in ["A", "A2", "A1", "A1b", "A1a"]:
            self.assertTrue(label in form.keyword_query)

        # Should raise error when not all nodes have a label in lan0
        a1b = next(c for c in c.get_codes() if c.get_label(lan0.id) == "A1b")
        a1b.labels.all().delete()
        p, _, form = _form(query="<{}+>".format(root.id))
        self.assertFalse(form.is_valid())

        # Test refering to previously defined label
        p, _, form = _form(query="lbl#foo\n<lbl>".format(root.id))
        self.assertTrue(form.is_valid())
        self.assertEquals("(foo)\n(foo)", form.keyword_query)

        # test initial tabs and accents

        p, c, form = self.get_form(query=u"\t\t\tBl\u00e2\tBalk\u00ebnende")
        self.assertTrue(form.is_valid())
        self.assertEquals(len(list(form.queries)), 1)
        self.assertEquals(next(form.queries).declared_label, "Bla")
        self.assertEquals(next(form.queries).query, "Balkenende")

        p, c, form = self.get_form(query=u"piet NOT jan\nbla#jan NOT piet")
        self.assertTrue(form.is_valid())
        self.assertEquals(form.cleaned_data['query'], "(piet NOT jan)\n(jan NOT piet)")