#!/usr/bin/python
# ##########################################################################
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

from __future__ import unicode_literals, print_function, absolute_import
import datetime
import logging

from django import forms
from django.utils.datastructures import MultiValueDict
from django.db.models import Q

from amcat.scripts.forms import ModelMultipleChoiceFieldWithIdLabel
from amcat.models import CodingJob, CodingSchemaField, CodingSchema, Project
from amcat.models import Article, Sentence
from amcat.scripts.script import Script
from amcat.tools.table import table3
from amcat.scripts.output.xlsx import table_to_xlsx
from amcat.scripts.output.csv_output import table_to_csv
from amcat.tools.progress import NullMonitor

log = logging.getLogger(__name__)

import csv
import collections
import itertools
import json
import base64

from cStringIO import StringIO

FIELD_LABEL = "{label} {schemafield.label}"

CODING_LEVEL_ARTICLE, CODING_LEVEL_SENTENCE, CODING_LEVEL_BOTH = range(3)
CODING_LEVELS = [
    (CODING_LEVEL_ARTICLE, "Article Codings"),
    (CODING_LEVEL_SENTENCE, "Sentence Codings"),
    (CODING_LEVEL_BOTH, "Article and Sentence Codings"),
]

ExportFormat = collections.namedtuple('ExportFormat', ["label", "function", "mimetype"])

EXPORT_FORMATS = (
    ExportFormat(label="csv", function=table_to_csv, mimetype="text/csv"),
    ExportFormat(label="xlsx", function=table_to_xlsx, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ExportFormat(label="json", function=lambda t: json.dumps(list(t.to_list())), mimetype=None),
)

_MetaField = collections.namedtuple("MetaField", ["object", "attr", "label"])

_METAFIELDS = [
    _MetaField("article", "id", "Article ID"),
    _MetaField("article", "headline", "Headline"),
    _MetaField("article", "byline", "Byline"),
    _MetaField("article", "medium", "Medium"),
    _MetaField("article", "medium_id", "Medium ID"),
    _MetaField("article", "date", "Date"),
    _MetaField("job", "id", "Codingjob ID"),
    _MetaField("job", "name", "Codingjob Name"),
    _MetaField("job", "coder", "Coder"),
    _MetaField("sentence", "id", "Sentence ID"),
    _MetaField("sentence", "parnr", "Paragraph"),
    _MetaField("sentence", "sentnr", "Sentence nr"),
    _MetaField("sentence", "sentence", "Sentence"),
    _MetaField("subsentence", "rangefrom", "Words from"),
    _MetaField("subsentence", "rangeto", "Words to"),
    _MetaField("subsentence", "subsentence", "Words coded"),
    _MetaField("coded_article", "comments", "Comments"),
    _MetaField("coded_article", "status", "Status"),
]


class CodingjobListForm(forms.Form):
    codingjobs = ModelMultipleChoiceFieldWithIdLabel(queryset=CodingJob.objects.all(), required=True)
    export_level = forms.ChoiceField(label="Level of codings to export", choices=CODING_LEVELS,
                                     initial=CODING_LEVEL_ARTICLE)

    def __init__(self, data=None, files=None, **kwargs):
        """
        Offers a form with a list of codingjobs. Raises a KeyError if keyword-
        argument project is not given.

        @param project: Restrict list of codingjobs to this project
        @type project: models.Project"""
        self.project = kwargs.pop("project", None)

        super(CodingjobListForm, self).__init__(data, files, **kwargs)
        if self.project:
            if isinstance(self.project, int):
                self.project = Project.objects.get(id=self.project)
            self.fields["codingjobs"].queryset = self.project.codingjob_set.all()
        self.data = self.data or MultiValueDict()


class CodingJobResultsForm(CodingjobListForm):
    """
    This is a dynamically rendered form, which consists of a static part (general
    options for exporting results) and a dynamic part. The dynamic part consists of
    field options being generated for each of the fields in the union of all fields
    in all codingjobs, depending on their type.
    """
    include_duplicates = forms.BooleanField(initial=False, required=False)
    export_format = forms.ChoiceField(tuple((c.label, c.label) for c in EXPORT_FORMATS))

    def __init__(self, data=None, files=None, **kwargs):
        """

        @param project: Restrict list of codingjobs to this project
        @type project: models.Project
        """
        codingjobs = kwargs.pop("codingjobs", None)
        export_level = kwargs.pop("export_level", None)
        super(CodingJobResultsForm, self).__init__(data, files, **kwargs)
        if codingjobs is None:  # is this necessary?
            data = self.data.getlist("codingjobs", codingjobs)
            codingjobs = self.fields["codingjobs"].clean(data)
        if export_level is None:
            export_level = int(self.fields["export_level"].clean(self.data['export_level']))

        # Hide fields from step (1)
        self.fields["codingjobs"].widget = forms.MultipleHiddenInput()
        self.fields["export_level"].widget = forms.HiddenInput()

        subsentences = CodingSchema.objects.filter(codingjobs_unit__in=codingjobs, subsentences=True).exists()


        # Add meta fields
        for field in _METAFIELDS:
            if field.object == "sentence" and export_level == CODING_LEVEL_ARTICLE: continue
            if field.object == "subsentence" and (export_level == CODING_LEVEL_ARTICLE or not subsentences): continue

            self.fields["meta_{field.object}_{field.attr}".format(**locals())] = forms.BooleanField(
                initial=True, required=False, label="Include {field.label}".format(**locals()))

        # Insert dynamic fields based on schemafields
        self.schemafields = _get_schemafields(codingjobs, export_level)
        self.fields.update(self.get_form_fields(self.schemafields))

    def get_form_fields(self, schemafields):
        """Returns a dict with all the fields needed to export this codingjob"""
        return dict(itertools.chain(*(self._get_form_fields(f) for f in schemafields)))

    def _get_form_fields(self, schemafield):
        """
        To prevent name collisions, this method also requires all schemafields, to check
        whether the current schemafield has a label which collides with a label of an
        other schemafield.
        """
        include_field = forms.BooleanField(
            label=FIELD_LABEL.format(label="Include", **locals()), initial=True, required=False,
        )

        # Show 'include this field' checkbox (for every field)
        prefix = _get_field_prefix(schemafield)
        yield ("{prefix}_included".format(**locals()), include_field)

        # Include field-specific form fields
        for id, field in schemafield.serialiser.get_export_fields():
            field.label = FIELD_LABEL.format(label="Export " + field.label, **locals())
            id = "{prefix}_{id}".format(**locals())
            yield id, field


def _get_field_prefix(schemafield):
    return "schemafield_{schemafield.codingschema_id}_{schemafield.fieldnr}".format(**locals())


def _get_schemafields(codingjobs, level):
    unitfilter = Q(codingschema__codingjobs_unit__in=codingjobs)
    articlefilter = Q(codingschema__codingjobs_article__in=codingjobs)

    # Get fields based on given codingjobs and unit_codings setting
    fields = CodingSchemaField.objects.all()
    if level == CODING_LEVEL_ARTICLE:
        fields = fields.filter(articlefilter)
    elif level == CODING_LEVEL_SENTENCE:
        fields = fields.filter(unitfilter)
    elif level == CODING_LEVEL_BOTH:
        fields = fields.filter(articlefilter | unitfilter)
    else:
        raise ValueError("Coding level {level!r} not recognized".format(**locals()))

    # Get fields based on given codingjobs and unit_codings setting
    return (fields.order_by("id").distinct()
            .select_related("codingschema", "fieldtype"))


CodingRow = collections.namedtuple('CodingRow',
                                   ['job', 'coded_article', 'article', 'sentence', 'article_coding', 'sentence_coding'])


def _get_rows(jobs, include_sentences=False, include_multiple=True, include_uncoded_articles=False,
              progress_monitor=NullMonitor()):
    """
    @param jobs: output rows for these jobs. Make sure this is a QuerySet object with .prefetch_related("codings__values")
    @param sentences: include sentence level codings (if False, row.sentence and .sentence_coding are always None)
    @param include_multiple: include multiple codedarticles per article
    @param include_uncoded_articles: include articles without corresponding codings
    """
    art_filter = Q(coded_articles__codingjob__in=jobs)
    if include_uncoded_articles:
        art_filter |= Q(articlesets_set__codingjob_set__in=jobs)

    job_articles = {a.id: a for a in Article.objects.filter(art_filter)}
    job_sentences = {s.id: s for s in Sentence.objects.filter(article__id__in=job_articles.keys())}

    # Articles that have been seen in a codingjob already (so we can skip duplicate codings on the same article)
    seen_articles = set()

    for i, job in enumerate(jobs):
        # Get all codings in dicts for later lookup
        coded_articles = set()
        article_codings = {}  # {ca : coding}
        sentence_codings = collections.defaultdict(
            lambda: collections.defaultdict(list))  # {ca : {sentence_id : [codings]}}

        for ca in job.coded_articles.order_by('id').prefetch_related("codings"):
            coded_articles.add(ca)
            for c in ca.codings.all():
                if c.sentence_id is None:
                    if ca not in article_codings:  # HACK, take first entry of duplicate article codings (#79)
                        article_codings[ca.id] = c
                else:
                    sentence_codings[ca.id][c.sentence_id].append(c)
        # output the rows for this job
        for ca in coded_articles:
            a = job_articles[ca.article_id]
            if a in seen_articles and not include_multiple:
                continue

            article_coding = article_codings.get(ca.id)
            sentence_ids = sentence_codings[ca.id]
            if include_sentences and sentence_ids:
                seen_articles.add(a)
                for sid in sentence_ids:
                    s = job_sentences[sid]
                    for sentence_coding in sentence_codings[ca.id][sid]:
                        yield CodingRow(job, ca, a, s, article_coding, sentence_coding)
            elif article_coding:
                seen_articles.add(a)
                yield CodingRow(job, ca, a, None, article_coding, None)

    if include_uncoded_articles:
        for article in set(job_articles.values()) - seen_articles:
            yield CodingRow(job, job.get_coded_article(article), article, None, None, None)


class CodingColumn(table3.ObjectColumn):
    def __init__(self, field, label, function):
        self.function = function
        self.field = field
        label = self.field.label + label
        self.cache = {}  # assume that the function is deterministic!
        super(CodingColumn, self).__init__(label)

    def getCell(self, row):
        coding = row.article_coding if self.field.codingschema.isarticleschema else row.sentence_coding
        if coding is None:
            return None
        value = coding.get_value(field=self.field)
        if value is not None:
            try:
                return self.cache[value]
            except KeyError:
                self.cache[value] = self.function(value)
                return self.cache[value]


class MetaColumn(table3.ObjectColumn):
    def __init__(self, field):
        self.field = field
        super(MetaColumn, self).__init__(self.field.label)

    def getCell(self, row):
        obj = getattr(row, self.field.object)
        if obj:
            return unicode(getattr(obj, self.field.attr))


class SubSentenceColumn(table3.ObjectColumn):
    def __init__(self, field):
        self.field = field
        super(SubSentenceColumn, self).__init__(self.field.label)

    def getCell(self, row):
        coding = row.sentence_coding
        if not coding: return None
        if self.field.attr == "rangefrom": return coding.start
        if self.field.attr == "rangeto": return coding.end
        if self.field.attr == "subsentence":
            # TODO: split the same way as annotator
            words = row.sentence.sentence.split()
            if coding.start and coding.end:
                words = words[coding.start:(coding.end + 1)]
            elif coding.start:
                words = words[coding.start:]
            elif coding.end:
                words = words[:(coding.end + 1)]
            return " ".join(words)


class GetCodingJobResults(Script):
    options_form = CodingJobResultsForm

    @classmethod
    def get_called_with(cls, **called_with):
        codingjobs = called_with['data']['codingjobs']
        if not isinstance(codingjobs, list):
            called_with['data']['codingjobs'] = [codingjobs]
        return dict(options=cls.options_form(**called_with))

    def get_table(self, codingjobs, export_level, **kargs):
        codingjobs = CodingJob.objects.prefetch_related("coded_articles__codings__values").filter(pk__in=codingjobs)

        # Get all row of table
        self.progress_monitor.update(5, "Preparing Jobs")
        rows = list(_get_rows(
            codingjobs, include_sentences=(int(export_level) != CODING_LEVEL_ARTICLE),
            include_multiple=True, include_uncoded_articles=False,
            progress_monitor=self.progress_monitor
        ))

        table = table3.ObjectTable(rows=rows)
        self.progress_monitor.update(5, "Preparing columns")

        # Meta field columns
        for field in _METAFIELDS:
            if self.options.get("meta_{field.object}_{field.attr}".format(**locals())):
                if field.object == "subsentence":
                    table.addColumn(SubSentenceColumn(field))
                else:
                    table.addColumn(MetaColumn(field))

        # Build columns based on form schemafields
        for schemafield in self.bound_form.schemafields:
            prefix = _get_field_prefix(schemafield)
            if self.options[prefix + "_included"]:
                options = {k[len(prefix) + 1:]: v for (k, v) in self.options.iteritems() if k.startswith(prefix)}

                for label, function in schemafield.serialiser.get_export_columns(**options):
                    table.addColumn(CodingColumn(schemafield, label, function))
        return table

    def _run(self, export_format, codingjobs, **kargs):
        self.progress_monitor.update(5, "Starting Export")
        table = self.get_table(codingjobs, **kargs)
        self.progress_monitor.update(5, "Preparing Results File")
        format = {f.label: f for f in EXPORT_FORMATS}[export_format]
        table = ProgressTable(table, len(codingjobs), self.progress_monitor)
        result = format.function(table)
        self.progress_monitor.update(15, "Encoding result")

        if format.mimetype:
            if len(codingjobs) > 3:
                codingjobs = codingjobs[:3] + ["etc"]
            filename = "Codingjobs {j} {now}.{ext}".format(j=",".join(str(j) for j in codingjobs),
                                                           now=datetime.datetime.now(), ext=format.label)
            result = {"type": "download",
                      "encoding": "base64",
                      "content_type": format.mimetype,
                      "filename": filename,
                      "data": base64.b64encode(result)}
        self.progress_monitor.update(5, "Results file ready")

        return result


from amcat.tools.table.table3 import WrappedTable


class ProgressTable(WrappedTable):
    def __init__(self, table, njobs, monitor):
        super(ProgressTable, self).__init__(table)
        self.njobs = njobs
        self.monitor = monitor
        self.seen_jobs = set()

    def getValue(self, row, col):
        jobid = row.job.id
        if jobid not in self.seen_jobs:
            self.seen_jobs.add(jobid)
            tick = int(60. / self.njobs)
            i = len(self.seen_jobs)
            self.monitor.update(tick, "Exporting job {i} / {self.njobs}: {row.job.name}"
                                .format(**locals()))
        return super(ProgressTable, self).getValue(row, col)


if __name__ == '__main__':
    from amcat.scripts.tools import cli

    result = cli.run_cli()

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
import unittest


class TestGetCodingJobResults(amcattest.AmCATTestCase):
    def _get_results_script(self, jobs, options, export_level=0, export_format='json'):
        """
        @param options: {field :{options}} -> include that field with those options
        """
        from django.utils.datastructures import MultiValueDict
        from amcat.forms import validate

        jobs = list(jobs)

        data = dict(codingjobs=[job.id for job in jobs],
                    export_format=[export_format],
                    export_level=[str(export_level)],
        )
        for field, opts in options.items():
            prefix = _get_field_prefix(field)
            data["{prefix}_included".format(**locals())] = [True]
            for k, v in opts.items():
                data["{prefix}_{k}".format(**locals())] = [v]

        f = CodingJobResultsForm(data=MultiValueDict(data), project=jobs[0].project)
        validate(f)
        return GetCodingJobResults(f)

    def _get_results(self, *args, **kargs):
        script = self._get_results_script(*args, **kargs)
        result = script.run()
        return [tuple(x) for x in json.loads(result)]

    def test_get_rows(self):
        schema, codebook, strf, intf, codef = amcattest.create_test_schema_with_fields()
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
        schema, codebook, strf, intf, codef = amcattest.create_test_schema_with_fields(codebook=codebook,
                                                                                       isarticleschema=True)
        sschema, codebook, sstrf, sintf, scodef = amcattest.create_test_schema_with_fields(codebook=codebook)
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
        s1 = u'S1 \xc4\u0193 \u02a2 \u038e\u040e'
        s2 = u'S2 \u053e\u06a8 \u090c  \u0b8f\u0c8a'
        f = CodingSchemaField.objects.create(codingschema=schema, fieldnr=1, label=s1,
                                             fieldtype_id=1, codebook=None)

        job = amcattest.create_test_job(unitschema=schema, articleschema=schema, narticles=5)

        articles = list(job.articleset.articles.all())
        amcattest.create_test_coding(codingjob=job, article=articles[0]).update_values({f: s2})

        # test csv
        s = self._get_results_script([job], {f: {}}, export_format='csv')
        import base64

        data = base64.b64decode(s.run()['data'])
        table = [[cell.decode('utf-8') for cell in row] for row in csv.reader(StringIO(data))]
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

    def test_nqueries(self):
        from amcat.tools import amcatlogging

        amcatlogging.setup()

        codebook, codes = amcattest.create_test_codebook_with_codes()
        schema, codebook, strf, intf, codef = amcattest.create_test_schema_with_fields(codebook=codebook)
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
        amcatlogging.debug_module('django.db.backends')

        script = self._get_results_script([job], {strf: {}, intf: {}})
        with self.checkMaxQueries(8):
            list(csv.reader(StringIO(script.run())))

        script = self._get_results_script([job], {strf: {}, intf: {}, codef: dict(ids=True)})
        with self.checkMaxQueries(8):
            list(csv.reader(StringIO(script.run())))

        script = self._get_results_script([job], {strf: {}, intf: {}, codef: dict(labels=True)})
        with self.checkMaxQueries(8):
            list(csv.reader(StringIO(script.run())))
