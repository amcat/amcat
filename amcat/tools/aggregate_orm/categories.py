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
from __future__ import unicode_literals

from collections import OrderedDict, defaultdict
from operator import itemgetter

from django.db.models import Q

from amcat.models import Medium, ArticleSet, Code
from amcat.tools.aggregate_orm.sqlobj import SQLObject, JOINS

POSTGRES_DATE_TRUNC_VALUES = [
    "microseconds",
    "milliseconds",
    "second",
    "minute",
    "hour",
    "day",
    "week",
    "month",
    "quarter",
    "year",
    "decade",
    "century",
    "millennium"
]

DATE_TRUNC_SQL = 'date_trunc(\'{interval}\', T_articles.date)'

__all__ = (
    "IntervalCategory",
    "MediumCategory",
    "ArticleSetCategory",
    "TermCategory",
    "SchemafieldCategory"
)

class Category(SQLObject):
    def aggregate(self, categories, value, rows):
        """
        Categories may aggregate rows further as they see fit. This can for example
        be used to implement codebook code aggregations.
        """
        return rows

    def get_objects(self, ids):
        return None

    def get_object(self, objects, id):
        return id

    def get_group_by(self):
        return next(iter(self.get_selects()))

    def get_column_names(self):
        """Returns names of columns when serializing to a flat format (csv)."""
        raise NotImplementedError("get_column_names() should be implemented by subclasses.")

    def get_column_values(self, obj):
        """Returns values for each column yielded by get_column_names() for an instance."""
        raise NotImplementedError("get_column_values() should be implemented by subclasses.")


class ModelCategory(Category):
    model = None

    def get_objects(self, ids):
        return self.model.objects.in_bulk(ids)

    def get_object(self, objects, id):
        return objects[id]

    def get_column_names(self):
        model_name = self.model.__name__.lower()
        return model_name + "_id", model_name + "_label"

    def get_column_values(self, obj):
        return obj.id, getattr(obj, obj.__label__)


class IntervalCategory(Category):
    joins_needed = ("codings", "coded_articles", "articles")

    def __init__(self, interval, **kwargs):
        super(IntervalCategory, self).__init__(**kwargs)

        if interval not in POSTGRES_DATE_TRUNC_VALUES:
            err_msg = "{} not a valid interval. Choose on of: {}"
            raise ValueError(err_msg.format(interval, POSTGRES_DATE_TRUNC_VALUES))

        self.interval = interval

    def get_selects(self):
        return [DATE_TRUNC_SQL.format(interval=self.interval)]

    def __repr__(self):
        return "<Interval: %s>" % self.interval

    def get_column_names(self):
        yield "date"

    def get_column_values(self, obj):
        """@type obj: datetime.datetime"""
        yield obj.isoformat()

class DuplicateLabelError(ValueError):
    pass

class InvalidReferenceError(ValueError):
    pass

class MediumCategory(ModelCategory):
    model = Medium
    joins_needed = ("codings", "coded_articles", "articles")

    def __init__(self, prefix=None, codebook=None):
        """
        Mediums can be aggregated using a codebook of the form:

        A
        - B
        - C
        D

        Mediums with the label A, B, or C will all be grouped under 'A'. D will not be considered,
        which is the same as just leaving it out.

        @param codebook: codebook to use for grouping
        @type codebook: Codebook
        """
        super(MediumCategory, self).__init__(prefix=prefix)
        self.codebook = codebook
        self.aggregation_map = {}

        if self.codebook is not None:
            self.codebook.cache()

            # Sanity check 1: labels must be unique
            labels = [c.label for c in self.codebook.codes]
            if len(set(labels)) != len(labels):
                dcount= defaultdict(int)
                for label in labels:
                    dcount[label] += 1
                duplicates = {l for l in labels if dcount[l] > 1}
                raise DuplicateLabelError("Duplicate labels in codebook {}: {}".format(codebook, duplicates))

            # Sanity check 2: labels must refer to mediums
            qfilter = Q()
            for label in labels:
                qfilter |= Q(name__iexact=label)
            mediums = Medium.objects.filter(qfilter)
            if mediums.distinct("id").count() != len(labels):
                real_labels = set(mediums.values_list("name", flat=True))
                error_message = "Some labels in {} did not refer to mediums: {}"
                raise InvalidReferenceError(error_message.format(self.codebook, set(labels) - real_labels))

            # Determine code -> code mapping
            root_map = {}
            for root_node in self.codebook.get_tree():
                root_map[root_node.code_id] = root_node.code_id
                for descendant in root_node.get_descendants():
                    root_map[descendant.code_id] = root_node.code_id

            # Replace code ids by labels
            root_map = {self.codebook._codes[k]: self.codebook._codes[v] for k, v in root_map.items()}

            # Replace codes by labels
            root_map = {k.label: v.label for k, v in root_map.items()}

            # Replace labels by mediums
            medium_map = {m.name: m.id for m in mediums.only("id", "name")}
            medium_map = {medium_map[k]: medium_map[v] for k, v in root_map.items()}

            # Set as global :)
            self.aggregation_map = medium_map

    def _aggregate(self, categories, value, rows):
        num_categories = len(categories)
        self_index = categories.index(self)

        # Create a mapping from key -> rownrs which need to be aggregated
        to_aggregate = defaultdict(list)
        for n, row in enumerate(rows):
            medium_id = row[self_index]
            new_medium_id = self.aggregation_map.get(medium_id, medium_id)
            key = row[:self_index] + [new_medium_id] + row[self_index+1:num_categories]
            to_aggregate[tuple(key)].append(n)

        for key, rownrs in to_aggregate.items():
            values = [row[num_categories:] for row in [rows[rownr] for rownr in rownrs]]
            yield list(key) + value.aggregate(values)

    def aggregate(self, categories, value, rows):
        if self.codebook is None:
            return super(MediumCategory, self).aggregate(categories, value, rows)
        return self._aggregate(categories, value, rows)

    def get_selects(self):
        yield 'T_articles.medium_id'


class ArticleSetCategory(ModelCategory):
    model = ArticleSet
    joins_needed = ("codings", "coded_articles", "codingjobs")

    def get_selects(self):
        yield "T_codingjobs.articleset_id"


class TermCategory(Category):
    joins_needed = ("codings", "coded_articles", "articles")

    def __init__(self, terms=None, **kwargs):
        # Force random prefix
        super(TermCategory, self).__init__(prefix=None)
        self.terms = terms

    def _get_values(self):
        for term, article_ids in enumerate(self.terms.values()):
            for article_id in article_ids:
                yield article_id, term

    def get_setup_statements(self):
        # Create table
        sql = "CREATE TEMPORARY TABLE T_{prefix}_terms (article_id int, term int);"
        yield sql.format(prefix=self.prefix)

        values = tuple(self._get_values())
        if values:
            sql = "INSERT INTO T_{prefix}_terms (article_id, term) VALUES {values};"
            yield sql.format(prefix=self.prefix, values=str(values)[1:-1])

        # Create index
        sql = "CREATE INDEX T_{prefix}_article_id_index ON T_{prefix}_terms (article_id);"
        yield sql.format(prefix=self.prefix)

        # Analyse table
        yield "ANALYSE T_{prefix}_terms;".format(prefix=self.prefix)

    def get_teardown_statements(self):
        yield "DROP INDEX IF EXISTS T_{prefix}_article_id_index;".format(prefix=self.prefix)
        yield "DROP TABLE IF EXISTS T_{prefix}_terms;".format(prefix=self.prefix)

    def get_joins(self):
        yield JOINS.terms.format(prefix="").format(table="T_{prefix}_terms".format(prefix=self.prefix))

    def get_selects(self):
        yield 'T_T_{prefix}_terms.term'.format(prefix=self.prefix)

    def get_objects(self, ids):
        assert isinstance(self.terms, OrderedDict)
        return dict(enumerate(self.terms.keys()))

    def get_object(self, objects, id):
        return objects.get(id)

    def copy(self, terms):
        return self.__class__(terms)

    def get_column_names(self):
        yield "term"

    def get_column_values(self, obj):
        """@type obj: SearchQuery"""
        yield obj.label


class SchemafieldCategory(ModelCategory):
    model = Code

    def __init__(self, field, codebook=None, **kwargs):
        super(SchemafieldCategory, self).__init__(**kwargs)
        self.field = field
        self.codebook = codebook
        self.aggregation_map = {}

        if self.codebook is not None:
            self.codebook.cache()
            for root_node in self.codebook.get_tree():
                self.aggregation_map[root_node.code_id] = root_node.code_id
                for descendant in root_node.get_descendants():
                    self.aggregation_map[descendant.code_id] = root_node.code_id

    def _aggregate(self, categories, value, rows):
        num_categories = len(categories)
        self_index = categories.index(self)

        # First do a sanity check. If a coding specifies a code which is
        # NOT present in the given codebook, raise an error.
        coded_codes = set(map(itemgetter(self_index), rows))
        codebook_codes = set(self.codebook.get_code_ids())
        invalid_codes = coded_codes - codebook_codes

        if invalid_codes:
            error_message = "Codes with ids {} were used in {}, but are not present in {}."
            raise ValueError(error_message.format(invalid_codes, self.field, self.codebook))

        # Create a mapping from key -> rownrs which need to be aggregated
        to_aggregate = defaultdict(list)
        for n, row in enumerate(rows):
            key = row[:self_index] + [self.aggregation_map[row[self_index]]] + row[self_index+1:num_categories]
            to_aggregate[tuple(key)].append(n)

        for key, rownrs in to_aggregate.items():
            values = [row[num_categories:] for row in [rows[rownr] for rownr in rownrs]]
            yield list(key) + value.aggregate(values)

    def aggregate(self, categories, value, rows):
        if self.codebook is None:
            return super(SchemafieldCategory, self).aggregate(categories, value, rows)
        return self._aggregate(categories, value, rows)

    def get_selects(self):
        return ['codings_values.intval']

    def get_wheres(self):
        where_sql = 'codings_values.field_id = {field.id}'
        yield where_sql.format(field=self.field)

    def __repr__(self):
        return "<SchemafieldCategory: %s>" % self.field