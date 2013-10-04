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


from itertools import ifilterfalse
import datetime
import re
import logging

from django import forms
from django.core.exceptions import ValidationError

from amcat.models import Project, ArticleSet, Medium, AmCAT
from amcat.models import Codebook, Language, Label, Article
from amcat.forms.forms import order_fields
from amcat.tools.toolkit import to_datetime, stripAccents
from amcat.tools import djangotoolkit 

log = logging.getLogger(__name__)

DATETYPES = {
    "all" : "All Dates",
    "on" : "On",
    "before" : "Before",
    "after" : "After",
    "between" : "Between",
}

REFERENCE_RE = re.compile(r"<(?P<reference>.*?)(?P<recursive>\+?)>")

__all__ = [
    "parse_query", "resolve_reference", "resolve_query",
    "resolve_queries", "SearchQuery", "SelectionForm",
    "TestSelectionForm", "ModelMultipleChoiceFieldWithIdLabel",
    "ModelChoiceFieldWithIdLabel"
]

DAY_DELTA = datetime.timedelta(hours=23, minutes=59, seconds=59, milliseconds=999)

class SearchQuery(object):
    """
    Represents a query object that contains both a (Solr) query and
    an optional label
    """
    def __init__(self, query, label=None):
        self.query = stripAccents(query)
        self.declared_label = stripAccents(label)
        self.label = self.declared_label or self.query

def _get_label_delimiter(query, label_delimiters):
    for label_delimiter in label_delimiters:
        if label_delimiter in query:
            return label_delimiter

def parse_query(query, label_delimiters=("#", "\t")):
    """
    Returns SearchQuery object, parsed from string `q`
    @raises: ValidationError if `q` is not valid query
    """
    query = query.strip()
    label_delimiter = _get_label_delimiter(query, label_delimiters)

    if label_delimiter is not None:
        lbl, q = re.split("{label_delimiter}+".format(**locals()), query, 1)
        #lbl, query = query.split(label_delimiter, 1)

        if not (0 < len(lbl) <= 20):
            raise ValidationError("Invalid label (after the {label_delimiter}). Query was: {query!r}"
                                  .format(**locals()), code="invalid")
        if not len(query):
            raise ValidationError("Invalid label (before the {label_delimiter}). Query was: {query!r}"
                                  .format(**locals()), code="invalid")
        return SearchQuery(q.strip(), label=lbl.strip())

    return SearchQuery(query)


def _resolve_recursive(codebook, tree_item, rlanguage):
    this = codebook.get_code(tree_item.code_id).get_label(rlanguage, fallback=False)

    if this is None:
        raise ValidationError("Code with id '{tree_item.code_id}' has no label in replacement-language.".format(**locals()), code="invalid")

    children = " OR ".join(_resolve_recursive(codebook, t, rlanguage) for t in tree_item.children)
    return ("{this} OR ({children})".format(**locals()) if children else this)


def resolve_reference(reference, recursive, queries, codebook=None, labels=None, rlanguage=None):
    # Case 1: reference is numeric, so it refers to a Code
    if reference.isnumeric():
        code = codebook.get_code(int(reference))
        if recursive:
            tree = codebook.get_tree(roots=[code])
            tree = _resolve_recursive(codebook, tree[0], rlanguage)
            return "({})".format(tree)
        return code.get_label(rlanguage, fallback=False)

    # Case 2: reference refers to labeled subquery
    if (reference, reference) in queries:
        # This refernce might contain references, resolve it first.
        return resolve_query(
            queries[(reference, reference)],
            queries, codebook, labels
        ).query

    # Case 3: reference refers to code in codebook, refered to by its label
    try:
        label = labels[reference].get_label(rlanguage, fallback=False)
    except Label.DoesNotExist:
        raise ValidationError("Code with label '{reference}' has no label in replacement-language.".format(**locals()), code="invalid")
    except KeyError:
        raise ValidationError("No code with label '{reference}' found in {codebook}".format(**locals()), code="invalid")
    except TypeError:
        raise ValidationError("<{reference}> does not refer to either a code or a query-label. Did you forget to set a codebook?".format(**locals()), code="invalid")

    if not recursive:
        return label

    return resolve_reference(
        unicode(labels[reference].id), recursive,
        queries, codebook, labels, rlanguage
    )

def resolve_query(query, queries, codebook=None, labels=None, rlanguage=None):
    """
    Take a query and parse and solve all references, marked as <reference>. Each
    query can contain three types of references:

      1) A reference to a previously defined subquery (<[a-zA-Z0-9]+>)
      2) A reference to a code in the given codebook
    
    """
    for mo in REFERENCE_RE.finditer(query.query):
        recursive = bool(mo.group("recursive"))
        reference = mo.group("reference")
        replacement = resolve_reference(
            reference, recursive, queries,
            codebook, labels, rlanguage
        )

        query.query = query.query.replace(mo.group(0), replacement, 1)

    return query


def resolve_queries(queries, codebook=None, label_language=None, replacement_language=None):
    _queries = { (q.label, q.declared_label) : q for q in queries }

    if len(queries) != len(_queries):
        labels = [q.label for q in queries]
        offender = next(l for l in labels if labels.count(l) > 1)
        raise ValidationError("Label '{offender}' defined more than once".format(**locals()))

    labels = None
    if codebook is not None:
        labels = { c.get_label(label_language, fallback=False) : c for c in codebook.get_codes() }

    for query in _queries.values():   
        yield resolve_query(query, _queries, codebook, labels, replacement_language)

class ModelMultipleChoiceFieldWithIdLabel(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return "%s - %s" % (obj.id, obj.name)
        
class ModelChoiceFieldWithIdLabel(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "%s - %s" % (obj.id, obj)
        

def _add_to_dict(dict, key, value):
    if hasattr(dict, "getlist") and isinstance(value, (list, tuple)):
        return dict.setlist(key, value)
    dict[key] = value
            
@order_fields()
class SelectionForm(forms.Form):
    include_all = forms.BooleanField(label="Include articles not matched by any keyword", required=False, initial=False)
    articlesets = ModelMultipleChoiceFieldWithIdLabel(queryset=ArticleSet.objects.none(), required=False, initial=())
    mediums = ModelMultipleChoiceFieldWithIdLabel(queryset=Medium.objects.all(), required=False, initial=())
    article_ids = forms.CharField(widget=forms.Textarea, required=False)
    start_date = forms.DateField(input_formats=('%d-%m-%Y',), required=False)
    end_date = forms.DateField(input_formats=('%d-%m-%Y',), required=False)
    datetype = forms.ChoiceField(choices=DATETYPES.items(), initial='all', required=True)
    on_date = forms.DateField(input_formats=('%d-%m-%Y',), required=False)
    
    codebook_replacement_language = ModelChoiceFieldWithIdLabel(queryset=Language.objects.all(), required=False, label="Language which is used to replace keywords")
    codebook_label_language = ModelChoiceFieldWithIdLabel(queryset=Language.objects.all(), required=False, label="Language for keywords")
    codebook = ModelChoiceFieldWithIdLabel(queryset=Codebook.objects.all(), required=False, label="Use Codebook")

    query = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, project=None, data=None, *args, **kwargs):
        super(SelectionForm, self).__init__(data, *args, **kwargs)

        if data and "projects" in data and project is None:
            log.warning("Passing 'projects' in `data` deprecated. Use project parameter on __init__ instead.")
            project = Project.objects.get(id=data.pop("projects")[0])
        elif project is None:
            raise ValueError("Project cannot be None")

        self._queries = None
        self.project = project

        codebooks = Codebook.objects.filter(project_id=project.id)
        self.fields['mediums'].queryset = self._get_mediums()
        self.fields['codebook'].queryset = codebooks
        self.fields['articlesets'].queryset = project.all_articlesets().order_by('-pk')

        distinct_arg = ["id"] if djangotoolkit.db_supports_distinct_on() else []
        
        self.fields['codebook_label_language'].queryset = self.fields['codebook_replacement_language'].queryset = (
            Language.objects.filter(labels__code__codebook_codes__codebook__in=codebooks).distinct(*distinct_arg)
        )

        if data is not None:
            self.data = self.get_data()

    def get_data(self):
        """Include initials in form-data."""
        data = self.data.copy()

        for field_name, value in self.initial.iteritems():
            if field_name not in data:
                _add_to_dict(data, field_name, value)

        for field_name, field in self.fields.iteritems():
            if field_name not in data:
                _add_to_dict(data, field_name, field.initial)
        return data

    def _get_mediums(self):
        if AmCAT.mediums_cache_enabled():
            return self.project.get_mediums()
        return Medium.objects.all()

    def _get_queries(self, unresolved_queries):
        if self._queries is not None: self._queries

        codebook = self.cleaned_data["codebook"]
        label_language = self.cleaned_data["codebook_label_language"]
        replacement_language = self.cleaned_data["codebook_replacement_language"]

        if codebook and label_language and replacement_language:
            codebook.cache_labels(label_language, replacement_language)

        return list(resolve_queries(
            unresolved_queries, codebook,
            label_language, replacement_language
        ))

    @property
    def queries(self):
        """
        Generator which yield SearchQuery objects.
        @raises: ValidationError if form not valid
        """
        return iter(self._queries)

    @property
    def solr_query(self):
        return self.cleaned_data["query"]

    @property
    def use_solr(self):
        """
        Should query use solr database?
        @raises: ValidationError if form not valid
        """
        self.full_clean()
        query = self.cleaned_data.get("query")
        return bool(query) and query != "()"

    def clean_codebook_label_language(self):
        return self.cleaned_data.get("codebook_label_language")

    def clean_codebook_replacement_language(self):
        return self.cleaned_data.get("codebook_replacement_language")

    def clean_codebook(self):
        codebook = self.cleaned_data["codebook"]
        label_language = self.cleaned_data["codebook_label_language"]
        replacement_language = self.cleaned_data["codebook_replacement_language"]

        if codebook and not (label_language and replacement_language):
            raise ValidationError(
                "Along with a codebook, you must also select languages.",
                code="missing"
            )

        return codebook

    def clean_query(self):
        query = self.cleaned_data["query"].strip()
        include_all = self.cleaned_data["include_all"]
        if include_all: query += "\nAll#*:*"

        queries = [parse_query(q) for q in query.split("\n") if q.strip()]
        self._queries = self._get_queries(queries)

        return "\n".join(q.query for q in self.queries)

    def clean_datetype(self):
        datetype = self.cleaned_data["datetype"]
        start_date = self.cleaned_data["start_date"]
        end_date = self.cleaned_data["end_date"]

        if datetype == "between" and not (start_date and end_date):
            raise ValidationError("Both a start and an end date need to be defined when datetype is 'between'", code="missing")
        elif datetype == "before" and not end_date:
            raise ValidationError("End date should be defined when 'datetype' is 'before'", code="missing")
        elif datetype == "after" and not start_date:
            raise ValidationError("Start date should be defined when 'datetype' is 'after'", code="missing")

        if start_date and end_date and not (start_date < end_date):
            raise ValidationError("End date should be greater than start date")

        return datetype

    def clean_start_date(self):
        if self.cleaned_data["start_date"]:
            return to_datetime(self.cleaned_data["start_date"])

    def clean_end_date(self):
        if self.cleaned_data["end_date"]:
            return to_datetime(self.cleaned_data["end_date"]) + DAY_DELTA

    def clean_on_date(self):
        on_date = self.cleaned_data["on_date"]
        if on_date: on_date = to_datetime(on_date)

        if "datetype" not in self.cleaned_data:
            # Don't bother checking, datetype raised ValidationError
            return on_date
        
        datetype = self.cleaned_data["datetype"]

        if datetype == "on" and not on_date:
            raise ValidationError("'On date' should be defined when dateype is 'on'", code="missing")
            
        if datetype == "on":
            self.cleaned_data["datetype"] = "between"
            self.cleaned_data["start_date"] = on_date
            self.cleaned_data["end_date"] = on_date + DAY_DELTA

        return None

    def clean_articlesets(self):
        if not self.cleaned_data["articlesets"]:
            return self.project.all_articlesets()
        return self.cleaned_data["articlesets"]

    def clean_mediums(self):
        if not self.cleaned_data["mediums"]:
            return self._get_mediums()
        return self.cleaned_data["mediums"]


    def clean_article_ids(self):
        article_ids = self.cleaned_data["article_ids"].split("\n")
        article_ids = filter(bool, map(unicode.strip, article_ids))

        # Parse all article ids as integer
        try:
            article_ids = map(int, article_ids)
        except ValueError:
            offender = repr(next(ifilterfalse(unicode.isnumeric, article_ids)))
            raise ValidationError("{offender} is not an integer".format(**locals()))

        # Check if they can be chosen
        articlesets = self.cleaned_data["articlesets"]
        all_articles = Article.objects.filter(articlesets_set__in=articlesets).distinct("id")
        chosen_articles = Article.objects.filter(id__in=article_ids).distinct("id")
        intersection = all_articles & chosen_articles

        if chosen_articles.count() != intersection.count():
            # Find offenders (skipping non-existing, which we can only find when
            # fetching all possible articles)
            offenders = chosen_articles.exclude(all_articles).values_list("id", flat=True)
            raise ValidationError(
                ("Articles {offenders} not in chosen articlesets or some non-existent"
                    .format(**locals())), code="invalid")

        return article_ids

    def clean(self):
        cleaned_data = { k:v for k,v in self.cleaned_data.iteritems() if v is not None }

        try:
            cleaned_data["queries"] = list(self.queries)
        except TypeError:
            log.debug("Parsing query failed. Query was: {!r}".format(self.data['query']))

        cleaned_data['projects'] = [self.project.id]

        return cleaned_data


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestSelectionForm(amcattest.PolicyTestCase):
    PYLINT_IGNORE_EXTRA = "W0212",

    def get_form(self, **kwargs):
        codebook = None

        if "project" in kwargs:
            project = kwargs.pop("project")
        else:
            codebook = amcattest.create_test_codebook_with_codes()[0]
            project = codebook.project

        return project, codebook, SelectionForm(project, data=kwargs)

    def test_defaults(self):
        from django.core.cache import cache
        cache.clear()

        set1 = amcattest.create_test_set(1)

        p, c, form = self.get_form()
        self.assertEqual({set1.articles.all()[0].medium}, set(form.fields['mediums'].queryset))
        AmCAT.enable_mediums_cache()
        p, c, form = self.get_form()
        self.assertEqual(set(), set(form.fields['mediums'].queryset))


    def test_get_label_delimiter(self):
        self.assertEquals(_get_label_delimiter("abc", "a"), "a")
        self.assertEquals(_get_label_delimiter("abc", "ab"), "a")
        self.assertEquals(_get_label_delimiter("abc", "ba"), "b")
        self.assertEquals(_get_label_delimiter("abc", "d"), None)

    def test_field_ordering(self):
        """Test if fields are defined in correct order (imported for
        *_clean methods on form."""
        orders = (
            ("start_date", "end_date", "datetype", "on_date"),
            ("include_all", "articlesets", "mediums", "query"),
            ("codebook_replacement_language", "codebook_label_language", "codebook"),
            ("articlesets", "article_ids")
        )

        for order in orders:
            fields = [SelectionForm.base_fields[f].creation_counter for f in order]
            self.assertEquals(sorted(fields), fields)

    def test_clean_include_all(self):
        p, c, form = self.get_form(include_all=False)
        self.assertTrue(form.is_valid())
        self.assertEquals(len(list(form.queries)), 0)

        p, c, form = self.get_form(include_all=True)
        self.assertTrue(form.is_valid())
        self.assertEquals(len(list(form.queries)), 1)
        self.assertEquals(next(form.queries).label, "All")
        self.assertEquals(next(form.queries).declared_label, "All")
        self.assertEquals(next(form.queries).query, "*:*")

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
        self.assertTrue(form.is_valid())
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

    def test_use_solr(self):
        p, c, form = self.get_form(query="  Bla   #  Balkenende")
        self.assertTrue(form.use_solr)

        p, c, form = self.get_form(query="")
        self.assertFalse(form.use_solr)

        p, c, form = self.get_form(query="()")
        self.assertFalse(form.use_solr)

        p, c, form = self.get_form(query=" () ")
        self.assertFalse(form.use_solr)

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
        self.assertTrue("Replacement" in form.solr_query)

        # Shouldn't crash at multiple (same) referals
        p, _, form = _form(query="<Referral>_<Referral>")
        self.assertTrue(form.is_valid())
        self.assertTrue("Replacement_Replacement" in form.solr_query)

        _form = functools.partial(
            _form, codebook_label_language=lan0.id,
            codebook_replacement_language=lan0.id
        )

        root = next(c for c in c.get_codes() if c.get_label(lan0.id) == "A")


        # Should be able to handle recursion when defined on label
        p, _, form = _form(query="<{}+>".format(root.get_label(lan0.id)))
        self.assertTrue(form.is_valid())
        self.assertEquals(3, form.solr_query.count("(")) # Three levels of nesting
        for label in ["A", "A2", "A1", "A1b", "A1a"]:
            self.assertTrue(label in form.solr_query)

        # Should be able to handle recursion when defined on id
        p, _, form = _form(query="<{}+>".format(root.id))
        self.assertTrue(form.is_valid())
        self.assertEquals(3, form.solr_query.count("(")) # Three levels of nesting
        for label in ["A", "A2", "A1", "A1b", "A1a"]:
            self.assertTrue(label in form.solr_query)

        # Should raise error when not all nodes have a label in lan0
        a1b = next(c for c in c.get_codes() if c.get_label(lan0.id) == "A1b")
        a1b.labels.all().delete()
        p, _, form = _form(query="<{}+>".format(root.id))
        self.assertFalse(form.is_valid())

        # Test refering to previously defined label
        p, _, form = _form(query="lbl#foo\n<lbl>".format(root.id))
        self.assertTrue(form.is_valid())
        self.assertEquals("foo\nfoo", form.solr_query)

        # test initial tabs and accents

        p, c, form = self.get_form(query=u"\t\t\tBl\u00e2\tBalk\u00ebnende")
        self.assertTrue(form.is_valid())
        self.assertEquals(len(list(form.queries)), 1)
        self.assertEquals(next(form.queries).declared_label, "Bla")
        self.assertEquals(next(form.queries).query, "Balkenende")
