import base64
import csv
import json
import unittest
from io import StringIO

from amcat.models import Language, CodingSchemaField, CodingJob
from amcat.scripts.actions.get_codingjob_results import _get_field_prefix, CodingJobResultsForm, \
    GetCodingJobResults, _get_rows, CODING_LEVEL_BOTH, log, ARTICLE_FIELDS
from amcat.tools import amcattest
from amcat.tools.amcattest import create_test_coding
from amcat.tools.sbd import get_or_create_sentences


class TestGetCodingJobResults(amcattest.AmCATTestCase):
    def _get_results_script(self, jobs, options, include_uncoded_articles=False,
                            include_uncoded_sentences=False, export_level=0,
                            export_format='json'):
        """
        @param options: {field :{options}} -> include that field with those options
        """
        from django.utils.datastructures import MultiValueDict
        from amcat.forms import validate

        jobs = list(jobs)

        data = {
            "codingjobs": [str(job.id) for job in jobs],
            "export_format": [export_format],
            "export_level": [str(export_level)],
            "include_uncoded_articles": "1" if include_uncoded_articles else "",
            "include_uncoded_sentences": "1" if include_uncoded_sentences else "",
            "meta_article_fields": ARTICLE_FIELDS.copy()
        }

        for field, opts in options.items():
            prefix = _get_field_prefix(field)
            data["{prefix}_included".format(**locals())] = [True]
            for k, v in opts.items():
                data["{prefix}_{k}".format(**locals())] = [v]

        # Set default language for medium aggregation
        data["aggregation_medium_language"] = [Language.objects.all()[0].id]

        f = CodingJobResultsForm(data=MultiValueDict(data), project=jobs[0].project)
        validate(f)
        return GetCodingJobResults(f)

    def _get_results(self, *args, **kargs):
        script = self._get_results_script(*args, **kargs)
        result = script.run()
        return [tuple(x) for x in json.loads(result)]

    def test_get_rows(self):
        schema, codebook, strf, intf, codef, _, _ = amcattest.create_test_schema_with_fields()
        job = amcattest.create_test_job(unitschema=schema, articleschema=schema, narticles=5)
        articles = list(job.articleset.articles.all())
        c = amcattest.create_test_coding(codingjob=job, article=articles[0])
        ca = job.get_coded_article(articles[0])
        # simple coding
        rows = set(_get_rows([job], include_sentences=False, include_multiple=True, include_uncoded_articles=False))
        self.assertEqual(rows, {(job, ca, articles[0], None, c, None)})
        # test uncoded_articles
        rows = set(_get_rows([job], include_sentences=False, include_multiple=True, include_uncoded_articles=True))
        self.assertEqual(rows,
                         {(job, ca, articles[0], None, c, None)} | {(job, job.get_coded_article(a), a, None, None, None)
                                                                    for a in articles[1:]})
        # test sentence
        s = amcattest.create_test_sentence(article=articles[0])
        sc = amcattest.create_test_coding(codingjob=job, article=articles[0], sentence=s)
        rows = set(_get_rows([job], include_sentences=False, include_multiple=True, include_uncoded_articles=False))
        self.assertEqual(rows, {(job, ca, articles[0], None, c, None)})
        rows = set(_get_rows([job], include_sentences=True, include_multiple=True, include_uncoded_articles=False))
        self.assertEqual(rows, {(job, ca, articles[0], s, c, sc)})
        # multiple sentence codings on the same article should duplicate article(coding)
        s2 = amcattest.create_test_sentence(article=articles[0])
        sc2 = amcattest.create_test_coding(codingjob=job, article=articles[0], sentence=s2)
        rows = set(_get_rows([job], include_sentences=True, include_multiple=True, include_uncoded_articles=False))
        self.assertEqual(rows, {(job, ca, articles[0], s, c, sc), (job, ca, articles[0], s2, c, sc2)})
        # if an article contains an article coding but no sentence coding, it should still show up with sentence=True
        c2 = amcattest.create_test_coding(codingjob=job, article=articles[1])
        rows = set(_get_rows([job], include_sentences=True, include_multiple=True, include_uncoded_articles=False))
        self.assertEqual(rows, {(job, ca, articles[0], s, c, sc), (job, ca, articles[0], s2, c, sc2),
                                (job, job.get_coded_article(articles[1]), articles[1], None, c2, None)})


    def test_results(self):
        codebook, codes = amcattest.create_test_codebook_with_codes()
        schema, codebook, strf, intf, codef, _, _ = amcattest.create_test_schema_with_fields(codebook=codebook,
                                                                                       isarticleschema=True)
        sschema, codebook, sstrf, sintf, scodef, _, _ = amcattest.create_test_schema_with_fields(codebook=codebook)
        job = amcattest.create_test_job(unitschema=sschema, articleschema=schema, narticles=5)
        articles = list(job.articleset.articles.all())

        c = amcattest.create_test_coding(codingjob=job, article=articles[0])

        # test simple coding with a codebook code
        c.update_values({strf: "bla", intf: 1, codef: codes["A1b"].id})
        self.assertEqual(self._get_results([job], {strf: {}, intf: {}, codef: dict(ids=True)}),
                         [('bla', 1, codes["A1b"].id)])
        # test multiple codings and parents
        c2 = amcattest.create_test_coding(codingjob=job, article=articles[1])
        c2.update_values({strf: "blx", intf: 1, codef: codes["B1"].id})
        self.assertEqual(set(self._get_results([job], {strf: {}, intf: {}, codef: dict(labels=True, parents=2)})),
                         {('bla', 1, "A", "A1", "A1b"), ('blx', 1, "B", "B1", "B1")})


        # test sentence result
        s = amcattest.create_test_sentence(article=articles[0])
        sc = amcattest.create_test_coding(codingjob=job, article=articles[0], sentence=s)
        sc.update_values({sstrf: "z", sintf: -1, scodef: codes["A"].id})

        self.assertEqual(set(self._get_results([job], {strf: {}, sstrf: {}, sintf: {}}, export_level=2)),
                         {('bla', 'z', -1), ('blx', None, None)})


    def test_unicode(self):
        """Test whether the export can handle unicode in column names and cell values"""
        schema = amcattest.create_test_schema(isarticleschema=True)
        s1 = 'S1 \xc4\u0193 \u02a2 \u038e\u040e'
        s2 = 'S2 \u053e\u06a8 \u090c  \u0b8f\u0c8a'
        f = CodingSchemaField.objects.create(codingschema=schema, fieldnr=1, label=s1,
                                             fieldtype_id=1, codebook=None)

        job = amcattest.create_test_job(unitschema=schema, articleschema=schema, narticles=5)

        articles = list(job.articleset.articles.all())
        amcattest.create_test_coding(codingjob=job, article=articles[0]).update_values({f: s2})

        # test csv
        s = self._get_results_script([job], {f: {}}, export_format='csv')

        data = base64.b64decode(s.run()['data']).decode('utf-8')
        table = [[cell for cell in row] for row in csv.reader(StringIO(data))]
        self.assertEqual(table, [[s1], [s2]])

        # test json
        s = self._get_results_script([job], {f: {}}, export_format='json')
        self.assertEqual(json.loads(s.run()), [[s2]])  # json export has no header (?)

    def test_unicode_excel(self):
        """Test whether the export can handle unicode in column names and cell values"""
        try:
            import openpyxl
        except ImportError:
            raise unittest.SkipTest("OpenPyxl not installed, skipping excel test")

        schema = amcattest.create_test_schema(isarticleschema=True)
        s1 = u'S1 \xc4\u0193 \u02a2 \u038e\u040e'
        s2 = u'S2 \u053e\u06a8 \u090c  \u0b8f\u0c8a'
        f = CodingSchemaField.objects.create(codingschema=schema, fieldnr=1, label=s1,
                                             fieldtype_id=1, codebook=None)

        job = amcattest.create_test_job(unitschema=schema, articleschema=schema, narticles=5)

        articles = list(job.articleset.articles.all())
        coding = amcattest.create_test_coding(codingjob=job, article=articles[0])
        coding.update_values({f: s2})


        # test excel, can't test content but we can test output and no error
        s = self._get_results_script([job], {f: {}}, export_format='xlsx')
        self.assertTrue(s.run())

    def test_nqueries_sentence_codings(self):
        aschema, acodebook, astrf, aintf, acodef, _, _ = amcattest.create_test_schema_with_fields(isarticleschema=True)
        sschema, scodebook, sstrf, sintf, scodef, _, _ = amcattest.create_test_schema_with_fields(isarticleschema=False)
        cjob = amcattest.create_test_job(10, articleschema=aschema, unitschema=sschema)

        for article in cjob.articleset.articles.all():
            coding = create_test_coding(codingjob=cjob, article=article)
            coding.update_values({astrf: "blas", aintf: 20})
            for sentence in get_or_create_sentences(article):
                coding = create_test_coding(codingjob=cjob, article=article, sentence=sentence)
                coding.update_values({sstrf: "bla", sintf: 10})

        fields = {sstrf: {}, sintf: {}, astrf: {}, aintf: {}}
        script = self._get_results_script([cjob], fields, export_level=CODING_LEVEL_BOTH)

        with self.checkMaxQueries(9):
            list(csv.reader(StringIO(script.run())))

    def test_include_uncoded_articles(self):
        aschema, acodebook, astrf, aintf, acodef, _, _ = amcattest.create_test_schema_with_fields(isarticleschema=True)
        sschema, scodebook, sstrf, sintf, scodef, _, _ = amcattest.create_test_schema_with_fields(isarticleschema=False)
        cjob = amcattest.create_test_job(2, articleschema=aschema, unitschema=sschema)
        a1, a2 = cjob.articleset.articles.all()
        coding = create_test_coding(codingjob=cjob, article=a1)
        coding.update_values({sstrf: "bla", sintf: 10})

        # Default settings should not export uncoded article (a2)
        fields = {sstrf: {}, sintf: {}, astrf: {}, aintf: {}}
        result = self._get_results([cjob], fields, export_level=CODING_LEVEL_BOTH)
        self.assertEqual(1, len(result))

        # Should export extra article if asked to
        fields = {sstrf: {}, sintf: {}, astrf: {}, aintf: {}}
        result = self._get_results([cjob], fields, include_uncoded_articles=True, export_level=CODING_LEVEL_BOTH)
        self.assertEqual(2, len(result))

    def test_include_uncoded_sentences(self):
        aschema, acodebook, astrf, aintf, acodef, _, _ = amcattest.create_test_schema_with_fields(isarticleschema=True)
        sschema, scodebook, sstrf, sintf, scodef, _, _ = amcattest.create_test_schema_with_fields(isarticleschema=False)
        a1 = amcattest.create_test_article(text="Zin 1. Zin 2.")
        a2 = amcattest.create_test_article(text="Zin 1. Zin 2.")
        aset = amcattest.create_test_set([a1, a2])
        cjob = amcattest.create_test_job(articleset=aset, articleschema=aschema, unitschema=sschema)

        sentence = list(get_or_create_sentences(a1))[1]
        coding = create_test_coding(codingjob=cjob, article=a1, sentence=sentence)
        coding.update_values({sstrf: "bla", sintf: 10})

        # We expect 1 sentence if we only export codings
        fields = {sstrf: {}, sintf: {}, astrf: {}, aintf: {}}
        result = self._get_results([cjob], fields, include_uncoded_sentences=False, export_level=CODING_LEVEL_BOTH)
        self.assertEqual(1, len(result))

        result = self._get_results([cjob], fields, include_uncoded_sentences=True, export_level=CODING_LEVEL_BOTH)
        self.assertEqual(3, len(result))

    def test_nqueries(self):
        codebook, codes = amcattest.create_test_codebook_with_codes()
        schema, codebook, strf, intf, codef, _, _ = amcattest.create_test_schema_with_fields(codebook=codebook)
        job = amcattest.create_test_job(unitschema=schema, articleschema=schema, narticles=7)
        articles = list(job.articleset.articles.all())

        log.info(codes)
        amcattest.create_test_coding(codingjob=job, article=articles[0]).update_values(
            {strf: "bla", intf: 1, codef: codes["A1b"].id})
        amcattest.create_test_coding(codingjob=job, article=articles[1]).update_values(
            {strf: "bla", intf: 1, codef: codes["A1b"].id})
        amcattest.create_test_coding(codingjob=job, article=articles[2]).update_values(
            {strf: "bla", intf: 1, codef: codes["A1b"].id})
        amcattest.create_test_coding(codingjob=job, article=articles[3]).update_values(
            {strf: "bla", intf: 1, codef: codes["A1b"].id})
        amcattest.create_test_coding(codingjob=job, article=articles[4]).update_values(
            {strf: "bla", intf: 1, codef: codes["A1b"].id})

        codingjobs = list(CodingJob.objects.filter(pk__in=[job.id]))
        c = list(codingjobs[0].codings)[0]

        script = self._get_results_script([job], {strf: {}, intf: {}})
        with self.checkMaxQueries(9):
            list(csv.reader(StringIO(script.run())))

        script = self._get_results_script([job], {strf: {}, intf: {}, codef: dict(ids=True)})
        with self.checkMaxQueries(9):
            list(csv.reader(StringIO(script.run())))

        script = self._get_results_script([job], {strf: {}, intf: {}, codef: dict(labels=True)})
        with self.checkMaxQueries(9):
            list(csv.reader(StringIO(script.run())))
