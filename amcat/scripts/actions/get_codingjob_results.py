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
from django.forms import ModelChoiceField, BooleanField
from django.utils.datastructures import MultiValueDict
from django.db.models import Q

from amcat.scripts.forms import ModelMultipleChoiceFieldWithIdLabel
from amcat.models import CodingJob, CodingSchemaField, CodingSchema, Project, Codebook, Language
from amcat.models import Article, Sentence
from amcat.scripts.script import Script
from amcat.tools.table import table3
from amcat.scripts.output.csv_output import table_to_csv
from amcat.tools.progress import NullMonitor


log = logging.getLogger(__name__)

import collections
import itertools
import json
import base64

FIELD_LABEL = "{label} {schemafield.label}"

AGGREGATABLE_FIELDS = {"medium"}

_DateFormatField = collections.namedtuple("_DateFormatField", ["id", "label", "strftime"])

DATE_FORMATS = (
    _DateFormatField("yearweekw", "yearweek (monday start of week)", "%Y%W"),
    _DateFormatField("yearweeku", "yearweek (sunday start of week)", "%Y%U"),
    _DateFormatField("yearmonth", "yearmonth", "%Y%m"),
)

CODING_LEVEL_ARTICLE, CODING_LEVEL_SENTENCE, CODING_LEVEL_BOTH = range(3)
CODING_LEVELS = [
    (CODING_LEVEL_ARTICLE, "Article Codings"),
    (CODING_LEVEL_SENTENCE, "Sentence Codings"),
    (CODING_LEVEL_BOTH, "Article and Sentence Codings"),
]

ExportFormat = collections.namedtuple('ExportFormat', ["label", "function", "mimetype"])

EXPORT_FORMATS = (
    ExportFormat(label="csv", function=table_to_csv, mimetype="text/csv"),
    ExportFormat(label="xlsx", function=lambda t: t.export(format='xlsx'), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
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
    include_uncoded_articles = forms.BooleanField(initial=False, required=False)
    include_uncoded_sentences = forms.BooleanField(initial=False, required=False)
    export_format = forms.ChoiceField(tuple((c.label, c.label) for c in EXPORT_FORMATS))
    date_format = forms.CharField(initial="%Y-%m-%d %H-%M-%S", required=False)

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
        self.fields.update(dict(self.get_aggregation_fields()))
        self.fields.update(dict(self.get_date_fields()))

    def get_date_fields(self):
        # Add date format fields
        for id, label, strftime in DATE_FORMATS:
            form_field = BooleanField(initial=False, label="Include {}".format(label), required=False)
            yield "meta_{}".format(id), form_field

    def get_aggregation_fields(self):
        prefix = "aggregation"
        for field_name in AGGREGATABLE_FIELDS:
            # Aggregate field
            label = "Aggregate {field_name}, codebook".format(field_name=field_name)
            cbs = self.project.get_codebooks().values_list("pk", flat=True)
            form_field = ModelChoiceField(queryset=Codebook.objects.filter(pk__in=cbs),
                                          label=label, required=False)
            yield "{prefix}_{field_name}".format(**locals()), form_field

            # Aggregate leave empty
            help_text = "If value is not found in codebook, leave field empty."
            label = "Aggregate {field_name}, include not found".format(field_name=field_name)
            form_field = BooleanField(initial=True, label=label, required=False, help_text=help_text)
            yield "{prefix}_{field_name}_default".format(**locals()), form_field

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
            yield "{prefix}_{id}".format(**locals()), field



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


def _get_rows(jobs, include_sentences=False, include_multiple=True, include_uncoded_articles=False, include_uncoded_sentences=False,
              progress_monitor=NullMonitor()):
    """
    @param jobs: output rows for these jobs. Make sure this is a QuerySet object with .prefetch_related("codings__values")
    @param include_sentences: include sentence level codings (if False, row.sentence and .sentence_coding are always None)
    @param include_multiple: include multiple codedarticles per article
    @param include_uncoded_articles: include articles without corresponding codings
    """
    art_filter = Q(coded_articles__codingjob__in=jobs)
    if include_uncoded_articles:
        art_filter |= Q(articlesets_set__codingjob_set__in=jobs)

    job_articles = {a.id: a for a in Article.objects.filter(art_filter)}
    job_sentences = {s.id: s for s in Sentence.objects.filter(article__id__in=job_articles.keys())}

    # Mapping of article -> sentences
    article_sentences = collections.defaultdict(set)
    for sentence_id, sentence in job_sentences.items():
        article_sentences[sentence.article_id].add(sentence_id)

    # Articles that have been seen in a codingjob already (so we can skip duplicate codings on the same article)
    seen_articles = set()

    for i, job in enumerate(jobs):
        # Get all codings in dicts for later lookup
        coded_articles = set()

        # {ca: coding}
        article_codings = {}

        # {ca: {sentence_id : [codings]}}
        sentence_codings = collections.defaultdict(lambda: collections.defaultdict(list))

        for ca in job.coded_articles.order_by('id').prefetch_related("codings__values"):
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

                if include_uncoded_sentences:
                    non_coded_sentences = article_sentences[ca.article_id] - set(sentence_ids)
                    for sentence in map(job_sentences.get, non_coded_sentences):
                        yield CodingRow(job, ca, a, sentence, article_coding, None)

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
        if obj is not None:
            return unicode(getattr(obj, self.field.attr))


class MappingMetaColumn(MetaColumn):
    """
    Mapping meta columns are meta columns, which subject their values to a mapping. Depending on
    the options given, a value might be left out if not found in the mapping or left alone.
    """
    def __init__(self, field, mapping, include_not_found=False):
        """
        @param field: metacolumn for superclass
        @type field: _MetaColum

        @param mapping: mapping values of superclass are subjected to
        @type mapping: dict

        @param include_not_found: if a value is not found in mapping, use value itself
        @type include_not_found: bool
        """
        self.mapping = mapping
        self.include_not_found = include_not_found
        super(MappingMetaColumn, self).__init__(field)

    def getCell(self, row):
        value = super(MappingMetaColumn, self).getCell(row)
        if value is None:
            return value
        return self.mapping.get(value, value if self.include_not_found else None)


class DateColumn(table3.ObjectColumn):
    def __init__(self, label, format):
        self.format = format
        super(DateColumn, self).__init__(label)

    def getCell(self, row):
        return row.article.date.strftime(self.format)


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

    def get_table(self, codingjobs, export_level, include_uncoded_sentences=False,
                  include_uncoded_articles=False, **kargs):
        codingjobs = CodingJob.objects.prefetch_related("coded_articles__codings__values").filter(pk__in=codingjobs)

        # Get all row of table
        self.progress_monitor.update(5, "Preparing Jobs")
        rows = list(_get_rows(
            codingjobs, include_sentences=(int(export_level) != CODING_LEVEL_ARTICLE),
            include_multiple=True, include_uncoded_articles=include_uncoded_articles,
            include_uncoded_sentences=include_uncoded_sentences,
            progress_monitor=self.progress_monitor
        ))

        table = table3.ObjectTable(rows=rows)
        self.progress_monitor.update(5, "Preparing columns")

        # Meta field columns
        for field in _METAFIELDS:
            if self.options.get("meta_{field.object}_{field.attr}".format(**locals())):
                if field.object == "subsentence":
                    table.addColumn(SubSentenceColumn(field))
                elif field.attr == "date":
                    table.addColumn(DateColumn(field.label, kargs["date_format"]))
                else:
                    table.addColumn(MetaColumn(field))

        # Date formatting (also belongs to meta)
        for id, label, strftime in DATE_FORMATS:
            if self.options.get("meta_{id}".format(id=id)):
                table.addColumn(DateColumn(label, strftime))

        for field_name in AGGREGATABLE_FIELDS:
            codebook = self.options.get("aggregation_{field_name}".format(field_name=field_name))
            not_found = self.options.get("aggregation_{field_name}_default".format(field_name=field_name))

            if not codebook:
                continue

            codebook.cache()
     
            table.addColumn(MappingMetaColumn(
                _MetaField("article", field_name, field_name + " aggregation"),
                codebook.get_aggregation_mapping(), not_found
            ))

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

            jobnames = [unicode(j).encode("ascii", "replace") for j in codingjobs]

            filename = "Codingjobs {jobs} {now}.{ext}".format(
                jobs=",".join(jobnames),
                now=datetime.datetime.now(), ext=format.label
            )

            result = {
                "type": "download",
                "encoding": "base64",
                "content_type": format.mimetype,
                "filename": filename,
                "data": base64.b64encode(result)
            }

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
